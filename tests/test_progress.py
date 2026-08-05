"""Tests for miru/ui/progress.py — progress reporter and helpers."""

from unittest.mock import MagicMock, patch

import pytest

from miru.ui.progress import (
    ProgressReporter,
    async_spinner,
    create_progress,
    create_spinner,
    track_progress,
)


class TestProgressReporter:
    def test_start_creates_progress(self) -> None:
        with patch("miru.ui.progress.Progress") as MockProgress:
            reporter = ProgressReporter("Task")
            reporter.start(total=10)
            MockProgress.return_value.start.assert_called_once()
            reporter.stop()

    def test_update_without_start_is_noop(self) -> None:
        reporter = ProgressReporter()
        reporter.update(advance=1)  # no raise

    def test_stop_without_start_is_noop(self) -> None:
        reporter = ProgressReporter()
        reporter.stop()  # no raise

    def test_track_context_manager(self) -> None:
        with patch("miru.ui.progress.Progress") as MockProgress:
            reporter = ProgressReporter()
            with reporter.track(total=5) as progress:
                assert progress is reporter
            MockProgress.return_value.start.assert_called_once()
            MockProgress.return_value.stop.assert_called_once()

    def test_start_spinner_no_bar(self) -> None:
        with patch("miru.ui.progress.Progress") as MockProgress:
            reporter = ProgressReporter("Spin")
            reporter.start(total=None)
            MockProgress.return_value.add_task.assert_called_once_with("Spin", total=None)
            reporter.stop()


class TestHelpers:
    def test_create_progress(self) -> None:
        with patch("miru.ui.progress.Progress") as MockProgress:
            progress = create_progress("desc")
            assert progress is MockProgress.return_value

    def test_create_spinner_returns_none(self) -> None:
        assert create_spinner("msg") is None

    def test_track_progress_context(self) -> None:
        with patch("miru.ui.progress.Progress") as MockProgress:
            with track_progress("T", total=3) as reporter:
                assert isinstance(reporter, ProgressReporter)
            MockProgress.return_value.start.assert_called_once()
            MockProgress.return_value.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_spinner_cancelled(self) -> None:
        import asyncio

        task = asyncio.create_task(async_spinner("working"))
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
