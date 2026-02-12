"""Test script for CSV-driven PDF downloader."""

from pathlib import Path
from src.exam_pipeline.pdf_downloader import ExamCatalog, run_auto_download

# Paths
CSV_PATH = Path("src/exam_pipeline/comcbt_data_published.csv")
DOWNLOAD_DIR = Path.home() / "Desktop" / "Apps" / "qcjongmin" / "appauto" / "raw_DB" / "rawdbs"


def test_catalog():
    """Test catalog reading and statistics."""
    print("\n" + "=" * 70)
    print("Testing Exam Catalog")
    print("=" * 70)

    catalog = ExamCatalog(CSV_PATH)

    # Show statistics
    catalog.print_statistics()

    # List top 10 unpublished exams
    catalog.list_top_unpublished(limit=10)


def test_download():
    """Test automatic download workflow."""
    print("\n" + "=" * 70)
    print("Testing Automatic Download")
    print("=" * 70 + "\n")

    # Run automatic download for top exam
    success, count = run_auto_download(
        csv_path=CSV_PATH,
        download_dir=DOWNLOAD_DIR,
        max_pdfs_per_exam=15,
        log_callback=print,  # Print progress to console
    )

    if success:
        print(f"\n✓ Success! Downloaded {count} files")
    else:
        print("\n✗ Download failed or no exams available")


if __name__ == "__main__":
    # Test 1: Show catalog info
    test_catalog()

    # Test 2: Download with ad modal handling
    test_download()
