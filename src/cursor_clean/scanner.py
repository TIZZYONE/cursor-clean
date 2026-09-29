"""Scan Cursor Roaming data for reclaimable space."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from cursor_clean.paths import resolve_paths


@dataclass
class AgentVersionInfo:
    name: str
    path: Path
    size_bytes: int
    keep: bool


@dataclass
class ChatCleanupPlan:
    keep_days: int
    cutoff_ms: int
    total_composers: int
    old_composers: int
    old_composer_ids: list[str] = field(default_factory=list)
    estimated_bytes: int | None = None  # filled when deep=True


@dataclass
class ScanReport:
    paths: dict[str, Path]
    state_db_bytes: int
    state_db_backup_bytes: int
    chat: ChatCleanupPlan | None
    agent_versions: list[AgentVersionInfo]
    cached_data_bytes: int
    logs_bytes: int
    warnings: list[str] = field(default_factory=list)

    @property
    def agent_reclaimable_bytes(self) -> int:
        return sum(v.size_bytes for v in self.agent_versions if not v.keep)

    @property
    def chat_reclaimable_bytes(self) -> int | None:
        if self.chat is None:
            return None
        return self.chat.estimated_bytes


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            continue
    return total


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size if path.is_file() else 0
    except OSError:
        return 0


def _open_ro(db_path: Path) -> sqlite3.Connection:
    uri = db_path.resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=30)
    con.execute("PRAGMA query_only=ON")
    return con


def _composer_cutoff_ms(keep_days: int) -> int:
    return int((time.time() - keep_days * 86400) * 1000)


def scan_old_composers(
    db_path: Path,
    keep_days: int = 45,
    *,
    deep: bool = False,
) -> ChatCleanupPlan:
    """Find composers older than keep_days.

    Age uses COALESCE(NULLIF(lastUpdatedAt,0), createdAt).
    deep=True estimates reclaimable blob bytes (slower on large DBs).
    """
    cutoff = _composer_cutoff_ms(keep_days)
    con = _open_ro(db_path)
    try:
        total = con.execute("SELECT COUNT(*) FROM composerHeaders").fetchone()[0]
        rows = con.execute(
            """
            SELECT composerId
            FROM composerHeaders
            WHERE COALESCE(NULLIF(lastUpdatedAt, 0), createdAt) < ?
            ORDER BY COALESCE(NULLIF(lastUpdatedAt, 0), createdAt) ASC
            """,
            (cutoff,),
        ).fetchall()
        old_ids = [r[0] for r in rows if r[0]]
        estimated: int | None = None
        if deep and old_ids:
            estimated = _estimate_composer_blob_bytes(con, old_ids)
        return ChatCleanupPlan(
            keep_days=keep_days,
            cutoff_ms=cutoff,
            total_composers=int(total),
            old_composers=len(old_ids),
            old_composer_ids=old_ids,
            estimated_bytes=estimated,
        )
    finally:
        con.close()


def _estimate_composer_blob_bytes(con: sqlite3.Connection, old_ids: list[str]) -> int:
    """Sum LENGTH(value) for keys belonging to old composers.

    Uses chunked IN (...) so it works on read-only connections (no TEMP table).
    """
    total = 0
    # Keep SQL parameter lists manageable.
    chunk_size = 400
    prefixes = (
        ("composerData:", 14),
        ("bubbleId:", 10),
        ("checkpointId:", 14),
        ("messageRequestContext:", 23),
    )
    for i in range(0, len(old_ids), chunk_size):
        chunk = old_ids[i : i + chunk_size]
        placeholders = ",".join("?" * len(chunk))
        parts = []
        params: list[str] = []
        for prefix, start in prefixes:
            parts.append(
                f"(key LIKE ? AND substr(key, {start}, 36) IN ({placeholders}))"
            )
            params.append(f"{prefix}%")
            params.extend(chunk)
        sql = f"SELECT COALESCE(SUM(LENGTH(value)), 0) FROM cursorDiskKV WHERE {' OR '.join(parts)}"
        row = con.execute(sql, params).fetchone()
        total += int(row[0] if row else 0)
    return total


def scan_agent_versions(versions_dir: Path) -> list[AgentVersionInfo]:
    """List agent CLI versions; keep the newest non-tmp folder."""
    if not versions_dir.is_dir():
        return []

    entries: list[AgentVersionInfo] = []
    for child in versions_dir.iterdir():
        if not child.is_dir():
            continue
        entries.append(
            AgentVersionInfo(
                name=child.name,
                path=child,
                size_bytes=_dir_size(child),
                keep=False,
            )
        )

    real = [e for e in entries if not e.name.startswith(".tmp")]
    if real:
        # Version folder names are date-prefixed (YYYY.MM.DD-...), lexicographic max ~= newest.
        newest = max(real, key=lambda e: e.name)
        for e in entries:
            e.keep = e.name == newest.name
    return sorted(entries, key=lambda e: (e.keep, e.name), reverse=True)


def scan(
    *,
    data_dir: Path | None = None,
    keep_days: int = 90,
    deep: bool = False,
    include_cache: bool = False,
) -> ScanReport:
    """Scan Cursor data and build a cleanup report."""
    paths = resolve_paths(data_dir)
    warnings: list[str] = []

    state_db = paths["state_db"]
    chat: ChatCleanupPlan | None = None
    if state_db.is_file():
        try:
            chat = scan_old_composers(state_db, keep_days=keep_days, deep=deep)
        except sqlite3.Error as exc:
            warnings.append(f"Failed to read state.vscdb: {exc}")
    else:
        warnings.append(f"state.vscdb not found: {state_db}")

    agents = scan_agent_versions(paths["agent_versions"])
    cached = _dir_size(paths["cached_data"]) if include_cache else 0
    logs = _dir_size(paths["logs"]) if include_cache else 0

    return ScanReport(
        paths=paths,
        state_db_bytes=_file_size(state_db),
        state_db_backup_bytes=_file_size(paths["state_db_backup"]),
        chat=chat,
        agent_versions=agents,
        cached_data_bytes=cached,
        logs_bytes=logs,
        warnings=warnings,
    )
