"""Progress bar unit tests."""

from cursor_clean.progress import ProgressBar


def test_progress_bar_fraction() -> None:
    bar = ProgressBar(total=10, label="t", width=20)
    bar.update(5, force=True)
    assert bar.current == 5
    bar.finish()
    assert bar._finished
