"""Progress bar unit tests."""

from cursor_clean.progress import ProgressBar


def test_determinate_percent() -> None:
    bar = ProgressBar(total=10, label="t")
    bar.update(5, force=True)
    assert abs(bar._percent(final=False) - 50.0) < 0.01
    bar.finish()
    assert bar._finished


def test_timed_percent_caps_at_99() -> None:
    bar = ProgressBar(estimate_seconds=1000, label="v")
    bar._start = bar._start - 500  # pretend 500s elapsed
    pct = bar._percent(final=False)
    assert 49.0 <= pct <= 51.0
    bar._start = bar._start - 5000
    assert bar._percent(final=False) == 99.0
    assert bar._percent(final=True) == 100.0
