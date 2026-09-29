"""CLI for cursor-clean."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from cursor_clean import __version__
from cursor_clean.cleaner import clean, clean_agent_versions, vacuum_state_db
from cursor_clean.console import configure_stdio
from cursor_clean.format_utils import format_bytes
from cursor_clean.i18n import resolve_lang, set_lang, t
from cursor_clean.paths import resolve_paths
from cursor_clean.process import cursor_process_count
from cursor_clean.scanner import ScanReport, scan, scan_agent_versions

DEFAULT_KEEP_DAYS = 45


def _build_parser() -> argparse.ArgumentParser:
    # Shared flags live on each subcommand so `cursor-clean clean --lang zh` works.
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--lang", choices=["zh", "en"], default=None, help="UI language")
    shared.add_argument(
        "--keep-days",
        type=int,
        default=DEFAULT_KEEP_DAYS,
        help=f"Keep chats newer than N days (default {DEFAULT_KEEP_DAYS})",
    )
    shared.add_argument("--data-dir", type=Path, default=None, help="Cursor Roaming root")
    shared.add_argument("--deep", action="store_true", help="Estimate chat blob bytes")
    shared.add_argument("--include-cache", action="store_true", help="Clear CachedData/logs too")

    parser = argparse.ArgumentParser(
        prog="cursor-clean",
        description="Clean Cursor Roaming data (old chats + unused agent versions).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("scan", parents=[shared], help="Preview reclaimable items")

    p_clean = sub.add_parser("clean", parents=[shared], help="Clean agents + chats + vacuum")
    p_clean.add_argument("-y", "--yes", action="store_true", help="No confirmation")
    p_clean.add_argument("--skip-chats", action="store_true")
    p_clean.add_argument("--skip-agents", action="store_true")
    p_clean.add_argument("--skip-vacuum", action="store_true")
    p_clean.add_argument("--force", action="store_true", help="VACUUM even if Cursor running")

    p_vac = sub.add_parser("vacuum", parents=[shared], help="Shrink state.vscdb (quit Cursor)")
    p_vac.add_argument("--force", action="store_true")

    p_ag = sub.add_parser("clean-agents", parents=[shared], help="Only delete old agent versions")
    p_ag.add_argument("-y", "--yes", action="store_true")
    return parser


def _print_report(report: ScanReport) -> None:
    print(t("data_root", path=report.paths["root"]))
    print(t("state_db", size=format_bytes(report.state_db_bytes)))
    print(t("state_backup", size=format_bytes(report.state_db_backup_bytes)))
    print()
    if report.chat is None:
        print(t("chats_unavailable"))
    else:
        cutoff = datetime.fromtimestamp(report.chat.cutoff_ms / 1000, tz=timezone.utc)
        print(t("chats_title"))
        print(t("keep_days", days=report.chat.keep_days))
        print(t("cutoff", cutoff=cutoff.strftime("%Y-%m-%d %H:%M")))
        print(t("total", n=report.chat.total_composers))
        print(t("older", n=report.chat.old_composers))
        if report.chat.estimated_bytes is None:
            print(t("est_blobs_hint"))
        else:
            print(t("est_blobs", size=format_bytes(report.chat.estimated_bytes)))
    print()
    print(t("agents_title"))
    if not report.agent_versions:
        print(t("agents_none"))
    else:
        for v in report.agent_versions:
            mark = t("keep") if v.keep else t("delete")
            print(f"  [{mark}] {v.name:40} {format_bytes(v.size_bytes)}")
        print(t("reclaimable", size=format_bytes(report.agent_reclaimable_bytes)))
    print()
    for w in report.warnings:
        print(t("warning", msg=w))


def _require_cursor_quit(*, force: bool) -> int | None:
    n = cursor_process_count()
    if n <= 0:
        return None
    print(t("cursor_count", n=n), file=sys.stderr)
    if force:
        print(t("cursor_running_warn"), file=sys.stderr)
        return None
    print(t("cursor_running"), file=sys.stderr)
    return 2


def cmd_scan(args: argparse.Namespace) -> int:
    _print_report(
        scan(
            data_dir=args.data_dir,
            keep_days=args.keep_days,
            deep=args.deep,
            include_cache=args.include_cache,
        )
    )
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    cursor_n = cursor_process_count()
    want_vacuum = not args.skip_vacuum
    if want_vacuum and cursor_n > 0 and not args.force:
        print(t("cursor_count", n=cursor_n), file=sys.stderr)
        print(t("vacuum_auto_skip"), file=sys.stderr)
        want_vacuum = False
    elif want_vacuum and cursor_n > 0:
        print(t("cursor_running_warn"), file=sys.stderr)

    report = scan(
        data_dir=args.data_dir,
        keep_days=args.keep_days,
        deep=args.deep,
        include_cache=args.include_cache,
    )
    _print_report(report)

    will_chats = (not args.skip_chats) and report.chat and report.chat.old_composers > 0
    will_agents = (not args.skip_agents) and any(not v.keep for v in report.agent_versions)
    will_cache = bool(args.include_cache) and (report.cached_data_bytes or report.logs_bytes)
    if not (will_chats or will_agents or will_cache or want_vacuum):
        print(t("nothing"))
        return 0

    print(t("planned"))
    if will_agents:
        n = sum(1 for v in report.agent_versions if not v.keep)
        print(t("plan_agents", n=n, size=format_bytes(report.agent_reclaimable_bytes)))
    if will_chats:
        print(t("plan_chats", n=report.chat.old_composers))
    if want_vacuum:
        print(t("plan_vacuum"))
    elif not args.skip_vacuum and cursor_n > 0:
        print(t("plan_vacuum_later"))
    print(t("plan_backup"))

    if not args.yes and input(t("proceed")).strip().lower() not in {"y", "yes"}:
        print(t("aborted"))
        return 1

    print()
    result = clean(
        report,
        clean_chats=not args.skip_chats,
        clean_agents=not args.skip_agents,
        include_cache=args.include_cache,
        do_vacuum=want_vacuum,
    )
    print()
    print(t("done"))
    if result.agent_deleted:
        print(
            t(
                "agents_removed",
                n=len(result.agent_deleted),
                size=format_bytes(result.agent_bytes_freed),
            )
        )
    if not args.skip_chats:
        print(
            t(
                "chats_removed",
                n=result.chat_deleted_composers,
                kv=result.chat_deleted_kv_rows,
            )
        )
    print(
        t(
            "state_result",
            before=format_bytes(result.state_db_before),
            after=format_bytes(result.state_db_after),
            freed=format_bytes(result.state_db_bytes_freed),
            vacuum=t("vacuum_ok") if result.vacuum_done else "",
        )
    )
    if result.vacuum_skipped or (not want_vacuum and not args.skip_vacuum):
        print(t("hint_run_vacuum"))
    for err in result.errors:
        print(t("error", msg=err), file=sys.stderr)
    return 1 if result.errors else 0


def cmd_vacuum(args: argparse.Namespace) -> int:
    if _require_cursor_quit(force=args.force) is not None:
        return 2
    db = resolve_paths(args.data_dir)["state_db"]
    if not db.is_file():
        print(t("db_missing", path=db), file=sys.stderr)
        return 1
    try:
        vacuum_state_db(db)
    except sqlite3.Error as exc:
        print(t("vacuum_failed", err=exc), file=sys.stderr)
        print(t("vacuum_retry"), file=sys.stderr)
        return 1
    return 0


def cmd_clean_agents(args: argparse.Namespace) -> int:
    versions = scan_agent_versions(resolve_paths(args.data_dir)["agent_versions"])
    to_delete = [v for v in versions if not v.keep]
    if not to_delete:
        print(t("no_agents"))
        return 0
    print(
        t(
            "will_agents",
            n=len(to_delete),
            size=format_bytes(sum(v.size_bytes for v in to_delete)),
        )
    )
    if not args.yes and input(t("proceed")).strip().lower() not in {"y", "yes"}:
        print(t("aborted"))
        return 1
    deleted, freed = clean_agent_versions(versions)
    print(t("agents_done", n=len(deleted), size=format_bytes(freed)))
    return 0


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)
    set_lang(resolve_lang(cli_lang=args.lang, interactive=not getattr(args, "yes", False)))
    if args.keep_days < 1:
        parser.error("--keep-days must be >= 1")
    return {
        "scan": cmd_scan,
        "clean": cmd_clean,
        "vacuum": cmd_vacuum,
        "clean-agents": cmd_clean_agents,
    }[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
