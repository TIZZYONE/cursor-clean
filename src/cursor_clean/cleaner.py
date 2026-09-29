"""Execute cleanup actions against Cursor Roaming data."""

from __future__ import annotations

import shutil
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from cursor_clean.i18n import t
from cursor_clean.scanner import AgentVersionInfo, ChatCleanupPlan, ScanReport, _dir_size, _file_size

ProgressFn = Callable[[str], None]


def _default_progress(msg: str) -> None:
    print(msg, flush=True)


@dataclass
class CleanResult:
    chat_deleted_composers: int = 0
    chat_deleted_kv_rows: int = 0
    vacuum_done: bool = False
    state_db_before: int = 0
    state_db_after: int = 0
    agent_deleted: list[str] = field(default_factory=list)
    agent_bytes_freed: int = 0
    cache_bytes_freed: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def state_db_bytes_freed(self) -> int:
        return max(0, self.state_db_before - self.state_db_after)


def _open_rw(db_path: Path, *, timeout: float = 30) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path), timeout=timeout)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    return con


def delete_old_chats(
    db_path: Path,
    plan: ChatCleanupPlan,
    *,
    progress: ProgressFn = _default_progress,
) -> tuple[int, int]:
    """Delete old composers and related KV rows. Does not VACUUM."""
    if not plan.old_composer_ids:
        return 0, 0

    progress(t("progress_del_chats", n=len(plan.old_composer_ids)))
    t0 = time.time()
    con = _open_rw(db_path)
    try:
        con.execute("CREATE TEMP TABLE old_c (id TEXT PRIMARY KEY)")
        con.executemany(
            "INSERT OR IGNORE INTO old_c(id) VALUES (?)",
            [(i,) for i in plan.old_composer_ids],
        )

        before_kv = con.total_changes
        con.execute(
            """
            DELETE FROM cursorDiskKV
            WHERE
              (key LIKE 'composerData:%'
               AND substr(key, 14, 36) IN (SELECT id FROM old_c))
              OR
              (key LIKE 'bubbleId:%'
               AND substr(key, 10, 36) IN (SELECT id FROM old_c))
              OR
              (key LIKE 'checkpointId:%'
               AND substr(key, 14, 36) IN (SELECT id FROM old_c))
              OR
              (key LIKE 'messageRequestContext:%'
               AND substr(key, 23, 36) IN (SELECT id FROM old_c))
            """
        )
        kv_deleted = con.total_changes - before_kv

        before_h = con.total_changes
        con.execute("DELETE FROM composerHeaders WHERE composerId IN (SELECT id FROM old_c)")
        headers_deleted = con.total_changes - before_h
        con.commit()
        progress(
            t(
                "progress_del_chats_done",
                n=headers_deleted,
                kv=kv_deleted,
                sec=time.time() - t0,
            )
        )
        return headers_deleted, kv_deleted
    finally:
        con.close()


def vacuum_state_db(
    db_path: Path,
    *,
    progress: ProgressFn = _default_progress,
) -> None:
    """VACUUM state.vscdb. Needs Cursor fully quit (exclusive lock)."""
    before = _file_size(db_path)
    progress(t("progress_vacuum", gb=before / (1024**3)))
    t0 = time.time()
    con = sqlite3.connect(str(db_path), timeout=10)
    try:
        con.execute("PRAGMA busy_timeout=10000")
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        con.execute("VACUUM")
    finally:
        con.close()
    after = _file_size(db_path)
    progress(
        t(
            "progress_vacuum_done",
            sec=time.time() - t0,
            before=before / (1024**3),
            after=after / (1024**3),
        )
    )


def clean_agent_versions(
    versions: list[AgentVersionInfo],
    *,
    progress: ProgressFn = _default_progress,
) -> tuple[list[str], int]:
    """Delete agent version folders marked keep=False."""
    to_delete = [v for v in versions if not v.keep]
    if not to_delete:
        return [], 0

    progress(t("progress_del_agents", n=len(to_delete)))
    deleted: list[str] = []
    freed = 0
    for item in to_delete:
        size = item.size_bytes
        progress(t("progress_del_agent_one", name=item.name, mb=size / (1024**2)))
        shutil.rmtree(item.path, ignore_errors=False)
        deleted.append(item.name)
        freed += size
    progress(t("progress_agents_freed", gb=freed / (1024**3)))
    return deleted, freed


def clean_optional_dirs(paths: dict[str, Path], *, include_cache: bool) -> int:
    """Optionally remove CachedData / logs contents. Backup is never touched."""
    if not include_cache:
        return 0
    freed = 0
    for key in ("cached_data", "logs"):
        path = paths[key]
        if not path.exists():
            continue
        size = _dir_size(path)
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=False)
            path.mkdir(parents=True, exist_ok=True)
        freed += size
    return freed


def clean(
    report: ScanReport,
    *,
    clean_chats: bool = True,
    clean_agents: bool = True,
    include_cache: bool = False,
    do_vacuum: bool = True,
    progress: ProgressFn | None = None,
) -> CleanResult:
    """Apply cleanup. Order: agents -> cache -> delete chats -> VACUUM."""
    log = progress or _default_progress
    result = CleanResult(state_db_before=_file_size(report.paths["state_db"]))

    if clean_agents:
        try:
            deleted, freed = clean_agent_versions(report.agent_versions, progress=log)
            result.agent_deleted = deleted
            result.agent_bytes_freed = freed
        except OSError as exc:
            result.errors.append(t("agent_failed", err=exc))

    if include_cache:
        try:
            log(t("progress_cache"))
            result.cache_bytes_freed = clean_optional_dirs(
                report.paths, include_cache=True
            )
            log(t("progress_cache_done", mb=result.cache_bytes_freed / (1024**2)))
        except OSError as exc:
            result.errors.append(t("cache_failed", err=exc))

    if clean_chats and report.chat and report.chat.old_composer_ids:
        try:
            headers, kv = delete_old_chats(
                report.paths["state_db"], report.chat, progress=log
            )
            result.chat_deleted_composers = headers
            result.chat_deleted_kv_rows = kv
        except (sqlite3.Error, OSError) as exc:
            result.errors.append(t("chat_failed", err=exc))

    if do_vacuum and report.paths["state_db"].is_file():
        try:
            vacuum_state_db(report.paths["state_db"], progress=log)
            result.vacuum_done = True
        except sqlite3.OperationalError as exc:
            msg = str(exc).lower()
            hint = t("vacuum_locked_hint") if ("locked" in msg or "busy" in msg) else ""
            result.errors.append(t("vacuum_failed_err", err=exc, hint=hint))
        except (sqlite3.Error, OSError) as exc:
            result.errors.append(t("vacuum_failed_err", err=exc, hint=""))

    result.state_db_after = _file_size(report.paths["state_db"])
    return result
