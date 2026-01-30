"""Test folder watcher with a simulated MP3 download."""

import logging
import shutil
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_folder_watcher():
    """Test the folder watcher service."""

    print("=" * 70)
    print("Testing Folder Watcher Service")
    print("=" * 70)
    print()

    # Setup test directories
    test_downloads = Path("test_downloads")
    test_assets = Path("test_assets_watcher")

    test_downloads.mkdir(exist_ok=True)
    test_assets.mkdir(exist_ok=True)

    print(f"Test Downloads: {test_downloads}")
    print(f"Test Assets: {test_assets}/audio/summary/")
    print()

    # Check if dummy MP3 exists
    dummy_mp3 = Path("dummy_lecture.mp3")

    if not dummy_mp3.exists():
        print("Creating dummy MP3 file...")
        # Create a dummy MP3 (just for testing)
        import edge_tts
        import asyncio

        async def create_dummy():
            text = "여러분, 안녕하세요! 이것은 테스트 강의입니다."
            communicate = edge_tts.Communicate(
                text=text,
                voice='ko-KR-SunHiNeural'
            )
            await communicate.save(str(dummy_mp3))

        asyncio.run(create_dummy())
        print(f"✓ Created: {dummy_mp3}")

    print()
    print("=" * 70)
    print("Starting Folder Watcher...")
    print("=" * 70)
    print()
    print("The watcher will:")
    print("  1. Monitor test_downloads/ for new MP3 files")
    print("  2. Auto-import them to test_assets_watcher/audio/summary/")
    print("  3. Name them as lecture1.mp3, lecture2.mp3, etc.")
    print()
    print("In 5 seconds, I'll copy dummy_lecture.mp3 to test_downloads/")
    print("and you should see it auto-import!")
    print()
    print("Press Ctrl+C to stop the watcher after the test")
    print("=" * 70)
    print()

    # Start watcher in background
    from src.exam_pipeline.audio import FolderWatcher

    def on_import(mp3_path, index):
        print()
        print("=" * 70)
        print(f"✓ AUTO-IMPORT SUCCESSFUL!")
        print("=" * 70)
        print(f"  Detected: {mp3_path.name}")
        print(f"  Imported as: lecture{index}.mp3")
        print()

        # Verify the file exists
        imported_file = test_assets / "audio" / "summary" / f"lecture{index}.mp3"
        if imported_file.exists():
            size_kb = imported_file.stat().st_size / 1024
            print(f"  ✓ Verified: {imported_file} ({size_kb:.1f} KB)")

        print("=" * 70)
        print()
        print("Test complete! Press Ctrl+C to exit.")

    watcher = FolderWatcher(
        assets_dir=test_assets,
        watch_dir=test_downloads,
        callback=on_import
    )

    watcher.start()

    # Wait a bit, then simulate a download
    print("Waiting 3 seconds before simulating download...")
    time.sleep(3)

    print()
    print("Simulating MP3 download...")
    test_mp3 = test_downloads / "test_lecture.mp3"
    shutil.copy(dummy_mp3, test_mp3)
    print(f"✓ Copied {dummy_mp3.name} → {test_mp3}")
    print()
    print("Watcher should detect and import this file now...")
    print()

    try:
        # Keep watching
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
        print()
        print("=" * 70)
        print("✓ Test Complete")
        print("=" * 70)

        # Show imported files
        summary_dir = test_assets / "audio" / "summary"
        if summary_dir.exists():
            lectures = list(summary_dir.glob("lecture*.mp3"))
            if lectures:
                print()
                print("Imported lectures:")
                for lecture in sorted(lectures):
                    size_kb = lecture.stat().st_size / 1024
                    print(f"  ✓ {lecture.name} ({size_kb:.1f} KB)")
            else:
                print()
                print("No lectures imported")

        print()


if __name__ == "__main__":
    test_folder_watcher()
