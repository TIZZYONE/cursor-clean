"""Command-line interface for cursor-clean."""

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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cursor-clean",
        description=(
            "Scan and clean Cursor Roaming data (Windows): "
            "old chats + unused cursor-agent versions. "
            "Never deletes state.vscdb.backup. Zero deps, no local DB."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--lang",
        choices=["zh", "en"],
        default=None,
        help="UI language: zh / en. Or set CURSOR_CLEAN_LANG. Default: ask once.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--keep-days",
            type=int,
            default=90,
            help="Keep chats within this many days (default: 90).",
        )
        p.add_argument(
            "--data-dir",
            type=Path,
            default=None,
            help="Override Cursor Roaming root (default: %%APPDATA%%\\Cursor).",
        )
        p.add_argument(
            "--deep",
            action="store_true",
            help="Estimate reclaimable chat blob size (slower).",
        )
        p.add_argument(
            "--include-cache",
            action="store_true",
            help="Also consider CachedData and logs (off by default).",
        )

    p_scan = sub.add_parser("scan", help="Scan only (no changes).")
    add_common(p_scan)

    p_clean = sub.add_parser("clean", help="Scan, confirm, then clean.")
    add_common(p_clean)
    p_clean.add_argument("-y", "--yes", action="store_true", help="Skip confirmation.")
    p_clean.add_argument("--skip-chats", action="store_true", help="Do not delete old chats.")
    p_clean.add_argument("--skip-agents", action="store_true", help="Do not delete old agents.")
    p_clean.add_argument(
        "--skip-vacuum",
        action="store_true",
        help="Skip VACUUM (file may not shrink until later).",
    )
    p_clean.add_argument(
        "--force",
        action="store_true",
        help="Allow while Cursor appears running (not recommended).",
    )

    p_vac = sub.add_parser("vacuum", help="Only VACUUM state.vscdb. Quit Cursor first.")
    p_vac.add_argument("--data-dir", type=Path, default=None)
    p_vac.add_argument("--force", action="store_true")

    p_agents = sub.add_parser("clean-agents", help="Only delete old agent versions.")
    p_agents.add_argument("--data-dir", type=Path, default=None)
    p_agents.add_argument("-y", "--yes", action="store_true")
    return parser


def _print_report(report: ScanReport) -> None:
    print(t("data_root", path=report.paths["root"]))
    print(t("state_db", size=format_bytes(report.state_db_bytes)))
    print(t("state_backup", size=format_bytes(report.state_db_backup_bytes)))
    print()

    if report.chat is not None:
        cutoff = datetime.fromtimestamp(report.chat.cutoff_ms / 1000, tz=timezone.utc)
        print(t("chats_title"))
        print(t("keep_days", days=report.chat.keep_days))
        print(t("cutoff", cutoff=cutoff.strftime("%Y-%m-%d %H:%M")))
        print(t("total", n=report.chat.total_composers))
        print(t("older", n=report.chat.old_composers))
        if report.chat.estimated_bytes is not None:
            print(t("est_blobs", size=format_bytes(report.chat.estimated_bytes)))
        else:
            print(t("est_blobs_hint"))
        print()
    else:
        print(t("chats_unavailable"))
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

    if report.cached_data_bytes or report.logs_bytes:
        print(t("cache_title"))
        print(f"  CachedData: {format_bytes(report.cached_data_bytes)}")
        print(f"  logs:       {format_bytes(report.logs_bytes)}")
        print()

    for w in report.warnings:
        print(t("warning", msg=w))


def _ensure_cursor_quit(*, force: bool) -> int | None:
    n = cursor_process_count()
    if n > 0:
        print(t("cursor_count", n=n), file=sys.stderr)
    if n > 0 and not force:
        print(t("cursor_running"), file=sys.stderr)
        print(t("tip_quit_first"), file=sys.stderr)
        return 2
    if n > 0 and force:
        print(t("cursor_running_warn"), file=sys.stderr)
    return None


def cmd_scan(args: argparse.Namespace) -> int:
    report = scan(
        data_dir=args.data_dir,
        keep_days=args.keep_days,
        deep=args.deep,
        include_cache=args.include_cache,
    )
    _print_report(report)
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    blocked = _ensure_cursor_quit(force=args.force)
    if blocked is not None:
        return blocked

    report = scan(
        data_dir=args.data_dir,
        keep_days=args.keep_days,
        deep=args.deep,
        include_cache=args.include_cache,
    )
    _print_report(report)

    will_chats = (not args.skip_chats) and report.chat and report.chat.old_composers > 0
    will_agents = (not args.skip_agents) and report.agent_reclaimable_bytes > 0
    will_cache = bool(args.include_cache) and (
        report.cached_data_bytes > 0 or report.logs_bytes > 0
    )
    will_vacuum = not args.skip_vacuum

    if not (will_chats or will_agents or will_cache or will_vacuum):
        print(t("nothing"))
        return 0

    print(t("planned"))
    if will_agents:
        print(
            t(
                "plan_agents",
                n=sum(1 for v in report.agent_versions if not v.keep),
                size=format_bytes(report.agent_reclaimable_bytes),
            )
        )
    if will_chats:
        print(t("plan_chats", n=report.chat.old_composers))
    if will_vacuum:
        print(t("plan_vacuum"))
    if will_cache:
        print(
            t(
                "plan_cache",
                size=format_bytes(report.cached_data_bytes + report.logs_bytes),
            )
        )
    print(t("plan_backup"))

    if not args.yes:
        answer = input(t("proceed")).strip().lower()
        if answer not in {"y", "yes"}:
            print(t("aborted"))
            return 1

    print()
    result = clean(
        report,
        clean_chats=not args.skip_chats,
        clean_agents=not args.skip_agents,
        include_cache=args.include_cache,
        do_vacuum=not args.skip_vacuum,
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
    if result.cache_bytes_freed:
        print(t("cache_freed", size=format_bytes(result.cache_bytes_freed)))
    for err in result.errors:
        print(t("error", msg=err), file=sys.stderr)
    return 1 if result.errors else 0


def cmd_vacuum(args: argparse.Namespace) -> int:
    blocked = _ensure_cursor_quit(force=args.force)
    if blocked is not None:
        return blocked
    paths = resolve_paths(args.data_dir)
    db = paths["state_db"]
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
    paths = resolve_paths(args.data_dir)
    versions = scan_agent_versions(paths["agent_versions"])
    to_delete = [v for v in versions if not v.keep]
    if not to_delete:
        print(t("no_agents"))
        return 0
    total = sum(v.size_bytes for v in to_delete)
    print(t("will_agents", n=len(to_delete), size=format_bytes(total)))
    if not args.yes:
        answer = input(t("proceed")).strip().lower()
        if answer not in {"y", "yes"}:
            print(t("aborted"))
            return 1
    deleted, freed = clean_agent_versions(versions)
    print(t("agents_done", n=len(deleted), size=format_bytes(freed)))
    return 0


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)

    interactive_lang = not getattr(args, "yes", False)
    lang = resolve_lang(cli_lang=args.lang, interactive=interactive_lang)
    set_lang(lang)

    if getattr(args, "keep_days", 90) < 1:
        parser.error("--keep-days must be >= 1")

    if args.command == "scan":
        return cmd_scan(args)
    if args.command == "clean":
        return cmd_clean(args)
    if args.command == "vacuum":
        return cmd_vacuum(args)
    if args.command == "clean-agents":
        return cmd_clean_agents(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
