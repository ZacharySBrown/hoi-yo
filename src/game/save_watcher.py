"""Watches for new HOI4 autosave files and yields them as they appear."""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import time
from pathlib import Path
from typing import AsyncGenerator

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

AUTOSAVE_PATTERN = "autosave*.hoi4"
DEBOUNCE_SECONDS = 2.0


class _SaveHandler(FileSystemEventHandler):
    """Internal handler that pushes matching file events into an asyncio queue."""

    def __init__(self, queue: asyncio.Queue[Path], loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        self._queue = queue
        self._loop = loop
        self._last_event_time: float = 0.0

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def _handle(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return

        path = Path(event.src_path)
        if not fnmatch.fnmatch(path.name, AUTOSAVE_PATTERN):
            return

        now = time.monotonic()
        if now - self._last_event_time < DEBOUNCE_SECONDS:
            logger.debug("Debouncing save event for %s (%.1fs since last)", path.name, now - self._last_event_time)
            return

        self._last_event_time = now
        logger.info("New autosave detected: %s", path.name)
        self._loop.call_soon_threadsafe(self._queue.put_nowait, path)


class SaveWatcher:
    """Watches a directory for HOI4 autosave files.

    Usage::

        watcher = SaveWatcher(save_dir)
        async for save_path in watcher.watch():
            process_save(save_path)
    """

    def __init__(self, save_dir: Path) -> None:
        self.save_dir = save_dir
        self._observer: Observer | None = None

    async def watch(self) -> AsyncGenerator[Path, None]:
        """Async generator that yields paths to new autosave files as they appear.

        Watches ``self.save_dir`` for files matching ``autosave*.hoi4``.
        Events within 2 seconds of each other are debounced (HOI4 writes
        saves incrementally).
        """
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Path] = asyncio.Queue()

        handler = _SaveHandler(queue, loop)
        observer = Observer()
        self._observer = observer

        save_dir = self.save_dir
        if not save_dir.exists():
            logger.warning("Save directory does not exist yet: %s -- will create it", save_dir)
            save_dir.mkdir(parents=True, exist_ok=True)

        observer.schedule(handler, str(save_dir), recursive=False)
        observer.start()
        logger.info("Watching for autosaves in %s", save_dir)

        try:
            while True:
                path = await queue.get()
                yield path
        finally:
            observer.stop()
            observer.join()
            self._observer = None

    def stop(self) -> None:
        """Stop the watcher if it is running."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
