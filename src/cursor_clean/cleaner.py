"""Cleanup actions for Cursor Roaming data."""

from __future__ import annotations

import os
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
CHAT_BATCH = 40  # composers per SQL batch (speed vs progress granularity)


def _log(msg: str) -> None:
    print(msg, flush=True)


def _gb(n: float) -> str:
    return f"{n / (1024**3):.2f}G"


@dataclass
class CleanResult:
    chat_deleted_composers: int = 0
    chat_deleted_kv_rows: int = 0
    vacuum_done: bool = False
    vacuum_skipped: bool = False
    state_db_before: int = 0
    state_db_after: int = 0
    agent_deleted: list[str] = field(default_factory=list)
    agent_bytes_freed: int = 0
    cache_bytes_freed: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def state_db_bytes_freed(self) -> int:
        return max(0, self.state_db_before - self.state_db_after)


def _open_rw(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path), timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    return con


def _size_label(db_path: Path, prefix: str) -> str:
    return (
        f"{prefix} db={_gb(_file_size(db_path))} "
        f"wal={_gb(_file_size(Path(str(db_path) + '-wal')))}"
    )


def _rmtree(path: Path) -> str | None:
    """Delete directory. Return None on success / already gone, else error text."""
    if not path.exists():
        return None

    def _onerror(func, p, _info) -> None:  # noqa: ANN001
        if not os.path.exists(p):
            return
        raise

    try:
        # Windows long-path prefix helps deep agent trees.
        target = path
        if os.name == "nt":
            resolved = str(path.resolve())
            if not resolved.startswith("\\\\?\\"):
                target = Path("\\\\?\\" + resolved)
        shutil.rmtree(target, onerror=_onerror)
    except FileNotFoundError:
        return None
    except OSError as exc:
        if not path.exists():
            return None
        return str(exc)
    return None if not path.exists() else "still exists"


def delete_old_chats(
    db_path: Path,
    plan: ChatCleanupPlan,
    *,
    progress: ProgressFn = _log,
    batch_size: int = CHAT_BATCH,
) -> tuple[int, int]:
    """Batch-delete old composers. Progress = completed / total (resumable)."""
    ids = plan.old_composer_ids
    if not ids:
        return 0, 0

    total = len(ids)
    progress(t("phase_chats", n=total))
    progress(t("progress_size_note"))
    t0 = time.time()
    con = _open_rw(db_path)
    bar = ProgressBar(total=total, label=t("bar_delete_chats"))
    done = 0
    kv_total = 0
    try:
        con.execute("CREATE TEMP TABLE batch_c (id TEXT PRIMARY KEY)")
        for start in range(0, total, batch_size):
            batch = ids[start : start + batch_size]
            con.execute("DELETE FROM batch_c")
            con.executemany("INSERT INTO batch_c(id) VALUES (?)", [(c,) for c in batch])
            before = con.total_changes
            con.execute(
                """
                DELETE FROM cursorDiskKV WHERE
                  (key LIKE 'composerData:%' AND substr(key,14,36) IN (SELECT id FROM batch_c))
                  OR (key LIKE 'bubbleId:%' AND substr(key,10,36) IN (SELECT id FROM batch_c))
                  OR (key LIKE 'checkpointId:%' AND substr(key,14,36) IN (SELECT id FROM batch_c))
                  OR (key LIKE 'messageRequestContext:%' AND substr(key,23,36) IN (SELECT id FROM batch_c))
                """
            )
            kv_total += con.total_changes - before
            con.execute(
                "DELETE FROM composerHeaders WHERE composerId IN (SELECT id FROM batch_c)"
            )
            con.commit()
            done = min(total, start + len(batch))
            bar.update(done, force=True, label=f"{t('bar_delete_chats')} {done}/{total}")
        bar.finish()
        progress(
            t("progress_del_chats_done", n=done, kv=kv_total, sec=time.time() - t0)
        )
        return done, kv_total
    except Exception:
        try:
            con.rollback()
        except Exception:
            pass
        bar.finish(ok=False)
        raise
    finally:
        con.close()


def vacuum_state_db(db_path: Path, *, progress: ProgressFn = _log) -> None:
    before = _file_size(db_path)
    wal = _file_size(Path(str(db_path) + "-wal"))
    progress(t("phase_vacuum", gb=before / (1024**3)))
    progress(t("progress_vacuum_explain"))
    if wal > 100 * 1024 * 1024:
        progress(t("progress_wal_warn", gb=wal / (1024**3)))

    t0 = time.time()
    bar = ProgressBar(indeterminate=True, label=_size_label(db_path, t("bar_vacuum")))
    bar.start_heartbeat(0.5)
    con = sqlite3.connect(str(db_path), timeout=15)
    try:
        con.execute("PRAGMA busy_timeout=15000")
        attach_sqlite_progress(con, bar, every=1000)
        progress(t("progress_checkpoint"))
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        bar.update(force=True, label=_size_label(db_path, t("bar_vacuum")))
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
    progress: ProgressFn = _log,
) -> tuple[list[str], int]:
    """Delete old agent folders. Already-missing dirs count as done (safe to re-run)."""
    to_delete = [v for v in versions if not v.keep]
    if not to_delete:
        return [], 0

    progress(t("phase_agents", n=len(to_delete)))
    deleted: list[str] = []
    freed = 0
    locked = 0
    total = len(to_delete)
    bar = ProgressBar(total=total, label=t("bar_delete_agents"))
    for i, item in enumerate(to_delete, start=1):
        existed = item.path.exists()
        err = _rmtree(item.path)
        if err is None:
            deleted.append(item.name)
            if existed:
                freed += item.size_bytes
            _log(f"  OK  [{i}/{total}] {item.name}  ({item.size_bytes / (1024**2):.0f} MB)")
        else:
            locked += 1
            _log(f"  SKIP[{i}/{total}] {item.name}  ({err})")
        bar.update(i, force=True, label=f"{t('bar_delete_agents')} {i}/{total}")
    bar.finish(ok=locked == 0)
    progress(t("progress_agents_freed", gb=freed / (1024**3)))
    if locked:
        progress(t("agent_skipped", n=locked))
    return deleted, freed


def clean_optional_dirs(paths: dict[str, Path], *, include_cache: bool) -> int:
    if not include_cache:
        return 0
    freed = 0
    for key in ("cached_data", "logs"):
        path = paths[key]
        if not path.exists():
            continue
        size = _dir_size(path)
        if path.is_dir():
            shutil.rmtree(path)
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
    log = progress or _log
    result = CleanResult(state_db_before=_file_size(report.paths["state_db"]))
    log(t("resume_safe"))

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
            result.cache_bytes_freed = clean_optional_dirs(report.paths, include_cache=True)
            log(t("progress_cache_done", mb=result.cache_bytes_freed / (1024**2)))
        except OSError as exc:
            result.errors.append(t("cache_failed", err=exc))

    if clean_chats and report.chat and report.chat.old_composer_ids:
        try:
            n, kv = delete_old_chats(report.paths["state_db"], report.chat, progress=log)
            result.chat_deleted_composers = n
            result.chat_deleted_kv_rows = kv
        except (sqlite3.Error, OSError) as exc:
            result.errors.append(t("chat_failed", err=exc))

    if do_vacuum and report.paths["state_db"].is_file():
        try:
            vacuum_state_db(report.paths["state_db"], progress=log)
            result.vacuum_done = True
        except sqlite3.OperationalError as exc:
            hint = t("vacuum_locked_hint") if "locked" in str(exc).lower() or "busy" in str(exc).lower() else ""
            result.errors.append(t("vacuum_failed_err", err=exc, hint=hint))
        except (sqlite3.Error, OSError) as exc:
            result.errors.append(t("vacuum_failed_err", err=exc, hint=""))
    elif not do_vacuum:
        result.vacuum_skipped = True

    result.state_db_after = _file_size(report.paths["state_db"])
    return result
