"""Execute cleanup actions against Cursor Roaming data."""

from __future__ import annotations

import shutil
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from cursor_clean.i18n import t
from cursor_clean.progress import ProgressBar, attach_sqlite_progress
from cursor_clean.scanner import AgentVersionInfo, ChatCleanupPlan, ScanReport, _dir_size, _file_size

ProgressFn = Callable[[str], None]


def _default_progress(msg: str) -> None:
    print(msg, flush=True)


def _fmt_gb(num: int | float) -> str:
    return f"{float(num) / (1024**3):.2f}G"


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


def _db_size_label(db_path: Path, prefix: str) -> str:
    main = _file_size(db_path)
    wal = _file_size(Path(str(db_path) + "-wal"))
    return f"{prefix} db={_fmt_gb(main)} wal={_fmt_gb(wal)}"


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
    progress(t("progress_size_note"))
    t0 = time.time()
    con = _open_rw(db_path)
    bar = ProgressBar(indeterminate=True, label=_db_size_label(db_path, t("bar_delete_chats")))
    bar.start_heartbeat(0.5)
    try:
        con.execute("CREATE TEMP TABLE old_c (id TEXT PRIMARY KEY)")
        con.executemany(
            "INSERT OR IGNORE INTO old_c(id) VALUES (?)",
            [(i,) for i in plan.old_composer_ids],
        )
        attach_sqlite_progress(con, bar, every=2000)

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
        bar.update(force=True, label=_db_size_label(db_path, t("bar_delete_chats")))

        before_h = con.total_changes
        con.execute("DELETE FROM composerHeaders WHERE composerId IN (SELECT id FROM old_c)")
        headers_deleted = con.total_changes - before_h
        con.commit()
        con.set_progress_handler(None, 0)
        bar.finish()
        progress(
            t(
                "progress_del_chats_done",
                n=headers_deleted,
                kv=kv_deleted,
                sec=time.time() - t0,
            )
        )
        return headers_deleted, kv_deleted
    except Exception:
        try:
            con.set_progress_handler(None, 0)
        except Exception:
            pass
        bar.finish(ok=False)
        raise
    finally:
        con.close()


def vacuum_state_db(
    db_path: Path,
    *,
    progress: ProgressFn = _default_progress,
) -> None:
    """VACUUM state.vscdb. Needs Cursor fully quit (exclusive lock)."""
    before = _file_size(db_path)
    wal_before = _file_size(Path(str(db_path) + "-wal"))
    progress(t("progress_vacuum", gb=before / (1024**3)))
    progress(t("progress_vacuum_explain"))
    if wal_before > 100 * 1024 * 1024:
        progress(t("progress_wal_warn", gb=wal_before / (1024**3)))

    t0 = time.time()
    bar = ProgressBar(
        indeterminate=True,
        label=_db_size_label(db_path, t("bar_vacuum")),
    )
    bar.start_heartbeat(0.5)

    # Short busy timeout: fail fast if Cursor still holds the lock.
    con = sqlite3.connect(str(db_path), timeout=15)
    try:
        con.execute("PRAGMA busy_timeout=15000")
        attach_sqlite_progress(con, bar, every=1000)

        def _refresh_label() -> None:
            bar.update(force=True, label=_db_size_label(db_path, t("bar_vacuum")))

        # Checkpoint first — can already reclaim a huge -wal while Cursor is quit.
        progress(t("progress_checkpoint"))
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        _refresh_label()

        con.execute("VACUUM")
        con.set_progress_handler(None, 0)
        bar.finish()
    except Exception:
        try:
            con.set_progress_handler(None, 0)
        except Exception:
            pass
        bar.finish(ok=False)
        raise
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
    bar = ProgressBar(total=len(to_delete), label=t("bar_delete_agents"))
    deleted: list[str] = []
    freed = 0
    errors: list[str] = []
    try:
        for i, item in enumerate(to_delete, start=1):
            size = item.size_bytes
            bar.update(
                i - 1,
                force=True,
                label=f"{t('bar_delete_agents')} {item.name}",
            )
            try:
                if not item.path.exists():
                    # Already gone — count as done, no bytes.
                    deleted.append(item.name)
                else:
                    shutil.rmtree(item.path)
                    if item.path.exists():
                        errors.append(f"{item.name}: still exists after delete")
                    else:
                        deleted.append(item.name)
                        freed += size
            except OSError as exc:
                errors.append(f"{item.name}: {exc}")
            bar.update(i, force=True)
        bar.finish(ok=not errors)
    except Exception:
        bar.finish(ok=False)
        raise

    progress(t("progress_agents_freed", gb=freed / (1024**3)))
    if errors:
        for err in errors:
            progress(t("warning", msg=err))
        raise OSError(t("agent_partial_fail", n=len(errors)))
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
