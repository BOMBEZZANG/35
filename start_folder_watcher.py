"""
Start the folder watcher service to auto-import NotebookLM MP3 files.

This script monitors ~/Downloads for new MP3 files and automatically
imports them to assets/audio/summary/lectureN.mp3
"""

import logging
from pathlib import Path

from src.exam_pipeline.audio import watch_downloads

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def on_import_callback(mp3_path: Path, index: int):
    """
    Callback function called after successful import.

    Args:
        mp3_path: Path to the imported MP3 file
        index: Lecture index number
    """
    logger.info("=" * 70)
    logger.info(f"🎉 NEW LECTURE IMPORTED!")
    logger.info("=" * 70)
    logger.info(f"  Source: {mp3_path.name}")
    logger.info(f"  Imported as: lecture{index}.mp3")
    logger.info(f"  Location: assets/audio/summary/lecture{index}.mp3")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Verify the audio file quality")
    logger.info("  2. Build Flutter app with new lecture")
    logger.info("  3. Deploy to App Store")
    logger.info("")


def main():
    """Start the folder watcher service."""
    # Configure paths
    assets_dir = Path("assets")  # Will be created if doesn't exist
    downloads_dir = Path.home() / "Downloads"

    print("=" * 70)
    print("NotebookLM Podcast Auto-Import Service")
    print("=" * 70)
    print()
    print(f"Monitoring: {downloads_dir}")
    print(f"Importing to: {assets_dir}/audio/summary/")
    print()
    print("How it works:")
    print("  1. Download podcast MP3 from NotebookLM to ~/Downloads")
    print("  2. This service detects the new file automatically")
    print("  3. MP3 is imported as lectureN.mp3 (auto-incrementing)")
    print("  4. Ready for app build!")
    print()
    print("Press Ctrl+C to stop watching")
    print("=" * 70)
    print()

    # Ensure assets directory exists
    assets_dir.mkdir(exist_ok=True)

    # Start watching
    try:
        watch_downloads(
            assets_dir=assets_dir,
            watch_dir=downloads_dir,
            category_name="프로그래밍기능사",
            callback=on_import_callback,
        )
    except KeyboardInterrupt:
        print("\n")
        print("=" * 70)
        print("✓ Folder watcher stopped")
        print("=" * 70)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise


if __name__ == "__main__":
    main()
