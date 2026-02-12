"""
Lecture audio importer for NotebookLM MP3 files.

Imports user-generated NotebookLM lecture audio files into the project structure.
"""

import logging
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class LectureImporter:
    """
    Imports NotebookLM-generated lecture audio files.

    Validates MP3 format and copies to correct asset directory structure.
    """

    def __init__(self, assets_dir: Path):
        """
        Initialize lecture importer.

        Args:
            assets_dir: Path to assets directory (e.g., project/assets)
        """
        self.assets_dir = Path(assets_dir)
        self.audio_summary_dir = self.assets_dir / "audio" / "summary"

        # Ensure directory exists
        self.audio_summary_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"LectureImporter initialized: {self.audio_summary_dir}")

    def _validate_mp3(self, file_path: Path) -> bool:
        """
        Validate MP3 file.

        Args:
            file_path: Path to MP3 file

        Returns:
            True if valid MP3
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False

        if not file_path.is_file():
            logger.error(f"Not a file: {file_path}")
            return False

        if file_path.suffix.lower() != ".mp3":
            logger.error(f"Not an MP3 file: {file_path}")
            return False

        # Check file size (must be > 1KB)
        if file_path.stat().st_size < 1024:
            logger.error(f"File too small (likely corrupted): {file_path}")
            return False

        # Check MP3 header (starts with ID3 or 0xFF)
        with open(file_path, "rb") as f:
            header = f.read(3)
            if not (header.startswith(b"ID3") or header[0] == 0xFF):
                logger.error(f"Invalid MP3 header: {file_path}")
                return False

        return True

    def import_lecture(
        self,
        source_file: Path,
        index: int,
        category: Optional[str] = None,
    ) -> bool:
        """
        Import a NotebookLM lecture MP3 file.

        Args:
            source_file: Path to source MP3 file
            index: Lecture index (1-based, e.g., 1 for lecture1.mp3)
            category: Optional category name for logging

        Returns:
            True if successful, False otherwise
        """
        source_file = Path(source_file)

        # Validate MP3
        if not self._validate_mp3(source_file):
            return False

        # Determine target filename
        target_filename = f"lecture{index}.mp3"
        target_path = self.audio_summary_dir / target_filename

        # Check if target already exists
        if target_path.exists():
            logger.warning(f"Target file already exists: {target_path}")
            logger.info("Overwriting existing file...")

        try:
            # Copy file
            shutil.copy2(source_file, target_path)

            file_size_mb = target_path.stat().st_size / (1024 * 1024)

            logger.info(
                f"✓ Imported lecture audio: {target_filename} "
                f"({file_size_mb:.2f} MB)"
            )

            if category:
                logger.info(f"  Category: {category}")

            return True

        except Exception as e:
            logger.error(f"Failed to import lecture audio: {e}")
            return False

    def import_multiple(
        self,
        source_files: list[tuple[Path, int, Optional[str]]],
    ) -> dict:
        """
        Import multiple lecture files.

        Args:
            source_files: List of (source_path, index, category) tuples

        Returns:
            Statistics dictionary
        """
        logger.info(f"Importing {len(source_files)} lecture files...")

        success_count = 0
        failed_count = 0

        for source_file, index, category in source_files:
            if self.import_lecture(source_file, index, category):
                success_count += 1
            else:
                failed_count += 1

        logger.info(
            f"Import completed: {success_count} succeeded, {failed_count} failed"
        )

        return {
            "total": len(source_files),
            "success": success_count,
            "failed": failed_count,
        }

    def list_imported_lectures(self) -> list[dict]:
        """
        List all imported lecture files.

        Returns:
            List of lecture info dictionaries
        """
        lectures = []

        if not self.audio_summary_dir.exists():
            return lectures

        for file_path in sorted(self.audio_summary_dir.glob("lecture*.mp3")):
            file_size_mb = file_path.stat().st_size / (1024 * 1024)

            lectures.append({
                "filename": file_path.name,
                "path": file_path,
                "size_mb": round(file_size_mb, 2),
            })

        return lectures


def import_lecture_audio(
    source_file: Path,
    assets_dir: Path,
    index: int,
    category: Optional[str] = None,
) -> bool:
    """
    Convenience function to import a lecture audio file.

    Args:
        source_file: Path to source MP3 file
        assets_dir: Path to assets directory
        index: Lecture index (1-based)
        category: Optional category name for logging

    Returns:
        True if successful, False otherwise
    """
    importer = LectureImporter(assets_dir)
    return importer.import_lecture(source_file, index, category)
