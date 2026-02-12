"""
Folder watcher service for auto-importing NotebookLM podcast MP3 files.

Monitors ~/Downloads for new MP3 files and automatically imports them
to the project's assets/audio/summary/ directory.
"""

import logging
import re
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from watchdog.observers import Observer

from .lecture_importer import LectureImporter

logger = logging.getLogger(__name__)


class NotebookLMMP3Handler(FileSystemEventHandler):
    """
    File system event handler for NotebookLM MP3 files.

    Detects new MP3 files in Downloads folder and imports them automatically.
    """

    def __init__(
        self,
        assets_dir: Path,
        category_name: str = "프로그래밍기능사",
        callback: Optional[Callable[[Path, int], None]] = None,
    ):
        """
        Initialize MP3 handler.

        Args:
            assets_dir: Path to project assets directory
            category_name: Category name for logging (default: 프로그래밍기능사)
            callback: Optional callback function(mp3_path, index) after import
        """
        self.importer = LectureImporter(assets_dir)
        self.category_name = category_name
        self.callback = callback
        self.processed_files = set()

        # Auto-increment lecture index
        self._next_index = self._get_next_lecture_index()

        logger.info(
            f"NotebookLM MP3 Handler initialized: next index = {self._next_index}"
        )

    def _get_next_lecture_index(self) -> int:
        """
        Get the next available lecture index based on existing files.

        Returns:
            Next lecture index (1-based)
        """
        existing_lectures = self.importer.list_imported_lectures()

        if not existing_lectures:
            return 1

        # Extract indices from filenames (lecture1.mp3 -> 1)
        indices = []
        for lecture in existing_lectures:
            match = re.search(r'lecture(\d+)\.mp3', lecture["filename"])
            if match:
                indices.append(int(match.group(1)))

        if indices:
            return max(indices) + 1
        return 1

    def _is_valid_mp3(self, file_path: Path) -> bool:
        """
        Check if file is a valid MP3 (basic validation).

        Args:
            file_path: Path to file

        Returns:
            True if valid MP3
        """
        if not file_path.exists():
            return False

        if file_path.suffix.lower() != ".mp3":
            return False

        # Check minimum file size (at least 10KB - relaxed for testing)
        if file_path.stat().st_size < 10 * 1024:
            logger.debug(f"File too small: {file_path.name}")
            return False

        return True

    def _wait_for_file_complete(self, file_path: Path, timeout: int = 30) -> bool:
        """
        Wait for file download to complete.

        Args:
            file_path: Path to file
            timeout: Maximum wait time in seconds

        Returns:
            True if file is complete, False if timeout
        """
        last_size = 0
        stable_count = 0
        start_time = time.time()

        while time.time() - start_time < timeout:
            if not file_path.exists():
                time.sleep(0.5)
                continue

            current_size = file_path.stat().st_size

            if current_size == last_size and current_size > 0:
                stable_count += 1
                if stable_count >= 3:  # Stable for 1.5 seconds
                    logger.debug(f"File download complete: {file_path.name}")
                    return True
            else:
                stable_count = 0

            last_size = current_size
            time.sleep(0.5)

        logger.warning(f"Timeout waiting for file: {file_path.name}")
        return False

    def on_created(self, event):
        """
        Handle file creation event.

        Args:
            event: File system event
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process MP3 files
        if file_path.suffix.lower() != ".mp3":
            return

        # Avoid duplicate processing
        if str(file_path) in self.processed_files:
            return

        logger.info(f"New MP3 detected: {file_path.name}")

        # Wait for download to complete
        if not self._wait_for_file_complete(file_path):
            logger.error(f"Failed to confirm download completion: {file_path.name}")
            return

        # Validate MP3
        if not self._is_valid_mp3(file_path):
            logger.warning(f"Invalid MP3 file (skipped): {file_path.name}")
            return

        # Import the file
        try:
            success = self.importer.import_lecture(
                source_file=file_path,
                index=self._next_index,
                category=self.category_name,
            )

            if success:
                self.processed_files.add(str(file_path))

                logger.info(
                    f"✓ Auto-imported: {file_path.name} → lecture{self._next_index}.mp3"
                )

                # Call callback if provided
                if self.callback:
                    try:
                        self.callback(file_path, self._next_index)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")

                # Increment index for next file
                self._next_index += 1

                # Optional: Delete original file after successful import
                # file_path.unlink()
                # logger.info(f"Deleted original: {file_path.name}")

            else:
                logger.error(f"Failed to import: {file_path.name}")

        except Exception as e:
            logger.error(f"Error importing {file_path.name}: {e}")


class FolderWatcher:
    """
    Folder watcher service for monitoring Downloads directory.

    Features:
    - Monitors ~/Downloads for new MP3 files
    - Auto-imports NotebookLM podcasts
    - Optional callback on successful import
    """

    def __init__(
        self,
        assets_dir: Path,
        watch_dir: Optional[Path] = None,
        category_name: str = "프로그래밍기능사",
        callback: Optional[Callable[[Path, int], None]] = None,
    ):
        """
        Initialize folder watcher.

        Args:
            assets_dir: Path to project assets directory
            watch_dir: Directory to monitor (default: ~/Downloads)
            category_name: Category name for logging
            callback: Optional callback(mp3_path, index) after import
        """
        self.assets_dir = Path(assets_dir)
        self.watch_dir = Path(watch_dir or Path.home() / "Downloads")
        self.category_name = category_name
        self.callback = callback

        # Ensure watch directory exists
        if not self.watch_dir.exists():
            raise ValueError(f"Watch directory not found: {self.watch_dir}")

        # Create event handler
        self.event_handler = NotebookLMMP3Handler(
            assets_dir=self.assets_dir,
            category_name=self.category_name,
            callback=self.callback,
        )

        # Create observer
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            str(self.watch_dir),
            recursive=False,
        )

        logger.info(f"FolderWatcher initialized: watching {self.watch_dir}")

    def start(self):
        """Start watching the folder."""
        logger.info(f"Starting folder watcher on: {self.watch_dir}")
        self.observer.start()
        logger.info("✓ Folder watcher started (press Ctrl+C to stop)")

    def stop(self):
        """Stop watching the folder."""
        logger.info("Stopping folder watcher...")
        self.observer.stop()
        self.observer.join()
        logger.info("✓ Folder watcher stopped")

    def run(self):
        """
        Run the folder watcher (blocking).

        Watches until interrupted by Ctrl+C.
        """
        self.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()


def watch_downloads(
    assets_dir: Path,
    watch_dir: Optional[Path] = None,
    category_name: str = "프로그래밍기능사",
    callback: Optional[Callable[[Path, int], None]] = None,
):
    """
    Convenience function to start folder watcher.

    Args:
        assets_dir: Path to project assets directory
        watch_dir: Directory to monitor (default: ~/Downloads)
        category_name: Category name for logging
        callback: Optional callback(mp3_path, index) after import

    Example:
        >>> def on_import(mp3_path, index):
        ...     print(f"Imported: {mp3_path.name} as lecture{index}.mp3")
        ...
        >>> watch_downloads(
        ...     assets_dir=Path("project/assets"),
        ...     callback=on_import
        ... )
    """
    watcher = FolderWatcher(
        assets_dir=assets_dir,
        watch_dir=watch_dir,
        category_name=category_name,
        callback=callback,
    )

    watcher.run()
