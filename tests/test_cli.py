"""CLI parsing tests."""

from cursor_clean.cli import DEFAULT_KEEP_DAYS, _build_parser


def test_lang_after_subcommand() -> None:
    args = _build_parser().parse_args(["clean", "--lang", "zh", "-y"])
    assert args.command == "clean"
    assert args.lang == "zh"
    assert args.yes is True


def test_keep_days_and_default() -> None:
    args = _build_parser().parse_args(["scan"])
    assert args.keep_days == DEFAULT_KEEP_DAYS == 45
    args2 = _build_parser().parse_args(["clean", "--keep-days", "30", "-y"])
    assert args2.keep_days == 30


def test_keep_backup_and_skip_orphans() -> None:
    args = _build_parser().parse_args(["clean", "--keep-backup", "--skip-orphans", "-y"])
    assert args.keep_backup is True
    assert args.skip_orphans is True
    args2 = _build_parser().parse_args(["clean", "-y"])
    assert args2.keep_backup is False
    assert args2.skip_orphans is False
