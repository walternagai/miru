"""Progress reporting utilities.

Provides progress bars, spinners, and tracking for long operations.
"""

import asyncio
import sys
from contextlib import contextmanager
from typing import Any, Iterator

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.text import Text

console = Console()


class ProgressReporter:
    """Unified progress reporting for various operations.
    
    Supports:
    - Spinner for indeterminate progress
    - Progress bar for determinate progress
    - Multi-task progress
    """
    
    def __init__(
        self,
        description: str = "Processing",
        transient: bool = False,
        show_elapsed: bool = True,
    ):
        self.description = description
        self.transient = transient
        self.show_elapsed = show_elapsed
        self._progress: Progress | None = None
        self._task_id: Any = None
    
    def start(self, total: int | None = None) -> None:
        """Start progress reporting.
        
        Args:
            total: Total steps (None for spinner)
        """
        columns = [
            SpinnerColumn(),
            TextColumn(f"[progress.description]{{task.description}}"),
        ]
        
        if total:
            columns.extend([
                BarColumn(),
                TaskProgressColumn(),
            ])
        
        if self.show_elapsed:
            columns.append(TimeElapsedColumn())
        
        self._progress = Progress(*columns, console=console, transient=self.transient)
        self._progress.start()
        self._task_id = self._progress.add_task(self.description, total=total)
    
    def update(self, advance: int = 1, description: str | None = None) -> None:
        """Update progress.
        
        Args:
            advance: Number of steps to advance
            description: New description (optional)
        """
        if self._progress and self._task_id is not None:
            kwargs = {"advance": advance}
            if description:
                kwargs["description"] = description
            self._progress.update(self._task_id, **kwargs)
    
    def stop(self) -> None:
        """Stop progress reporting."""
        if self._progress:
            self._progress.stop()
            self._progress = None
    
    @contextmanager
    def track(self, total: int | None = None) -> Iterator["ProgressReporter"]:
        """Context manager for progress tracking.
        
        Args:
            total: Total steps
            
        Yields:
            ProgressReporter instance
            
        Example:
            >>> with ProgressReporter("Processing").track(100) as progress:
            ...     for i in range(100):
            ...         # do work
            ...         progress.update()
        """
        try:
            self.start(total)
            yield self
        finally:
            self.stop()


def create_progress(description: str = "Processing") -> Progress:
    """Create a Rich progress bar.
    
    Args:
        description: Progress description
        
    Returns:
        Progress instance
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )


def create_spinner(message: str) -> "asyncio.Task[None] | None":
    """Create an async spinner for indeterminate progress.
    
    Args:
        message: Spinner message
        
    Returns:
        Asyncio task (if in async context) or None
        
    Example:
        >>> async with create_spinner("Processing..."):
        ...     await long_operation()
    """
    return None


@contextmanager
def track_progress(
    description: str = "Processing",
    total: int | None = None,
    transient: bool = False,
) -> Iterator[ProgressReporter]:
    """Context manager for tracking progress.
    
    Args:
        description: Progress description
        total: Total steps (None for spinner)
        transient: Remove progress when done
        
    Yields:
        ProgressReporter instance
        
    Example:
        >>> with track_progress("Comparing models", total=3) as progress:
        ...     for model in models:
        ...         result = run_model(model)
        ...         progress.update()
    """
    reporter = ProgressReporter(description, transient=transient)
    try:
        reporter.start(total)
        yield reporter
    finally:
        reporter.stop()


async def async_spinner(message: str = "Processing") -> None:
    """Async spinner for long operations.
    
    Args:
        message: Spinner message
        
    Note:
        This is meant to be run as a background task.
        
    Example:
        >>> task = asyncio.create_task(async_spinner("Processing"))
        >>> try:
        ...     await long_operation()
        ... finally:
        ...     task.cancel()
    """
    chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    idx = 0
    while True:
        sys.stdout.write(f"\r{chars[idx % len(chars)]} {message}...")
        sys.stdout.flush()
        await asyncio.sleep(0.1)
        idx += 1