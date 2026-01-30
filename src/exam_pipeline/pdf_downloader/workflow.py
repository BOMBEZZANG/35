"""Automated workflow for downloading exam PDFs based on CSV catalog."""

import logging
from pathlib import Path
from typing import Callable, Optional, Tuple

from .csv_manager import ExamCatalog, ExamRecord
from .downloader import PDFDownloader

logger = logging.getLogger(__name__)


class DownloadWorkflow:
    """
    Manages automated PDF download workflow.

    Workflow:
    1. Read CSV catalog
    2. Filter unpublished exams
    3. Select exam with highest views
    4. Download up to 15 PDFs from that exam's board
    5. Mark exam as published in CSV
    """

    def __init__(
        self,
        csv_path: Path,
        download_dir: Path,
        max_pdfs_per_exam: int = 15,
    ):
        """
        Initialize download workflow.

        Args:
            csv_path: Path to comcbt_data_published.csv
            download_dir: Directory to save PDFs
            max_pdfs_per_exam: Maximum PDFs to download per exam (default: 15)
        """
        self.catalog = ExamCatalog(csv_path)
        self.downloader = PDFDownloader(
            download_dir, max_pdfs_per_category=max_pdfs_per_exam
        )
        self.max_pdfs_per_exam = max_pdfs_per_exam

    def run_next_download(
        self, log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, Optional[ExamRecord], int]:
        """
        Download PDFs for the next unpublished exam.

        Selects exam with highest view count, downloads PDFs, and marks as published.

        Args:
            log_callback: Optional callback for progress logging

        Returns:
            Tuple of (success, exam_record, files_downloaded)
        """
        # Step 1: Get catalog statistics
        stats = self.catalog.get_statistics()
        logger.info(
            f"Catalog: {stats['unpublished']} unpublished / "
            f"{stats['total_exams']} total exams"
        )

        if log_callback:
            log_callback(
                f"\n📊 Catalog: {stats['unpublished']} unpublished exams remaining\n"
            )

        # Step 2: Select top unpublished exam
        exam = self.catalog.get_top_unpublished_exam()

        if not exam:
            logger.info("No unpublished exams found")
            if log_callback:
                log_callback("✓ All exams have been published!")
            return False, None, 0

        # Step 3: Display selected exam
        logger.info(f"Selected: {exam.title} ({exam.view_count:,} views)")
        if log_callback:
            log_callback("=" * 70)
            log_callback(f"🎯 Selected Exam (Rank #1 by views)")
            log_callback("=" * 70)
            log_callback(f"Title:  {exam.title}")
            log_callback(f"Views:  {exam.view_count:,}")
            log_callback(f"URL:    {exam.url}")
            log_callback(f"Target: Download up to {self.max_pdfs_per_exam} PDFs")
            log_callback("=" * 70 + "\n")

        # Step 4: Download PDFs
        try:
            self.downloader._init_driver()
            folder, count = self.downloader.download_from_board(
                exam.url, exam.title, log_callback
            )

            if count > 0:
                logger.info(f"Successfully downloaded {count} files")

                # Step 5: Mark as published
                self.catalog.mark_as_published(exam)

                if log_callback:
                    log_callback(f"\n✓ Marked as published in CSV")
                    log_callback(f"✓ Download complete: {count} files\n")

                return True, exam, count

            else:
                logger.warning(f"No files downloaded for: {exam.title}")
                if log_callback:
                    log_callback(f"\n⚠ No PDF files found for this exam")
                    log_callback(f"Skipping CSV update (will retry next time)\n")

                return False, exam, 0

        except Exception as e:
            logger.error(f"Download failed: {e}")
            if log_callback:
                log_callback(f"\n✗ Error: {e}\n")
            return False, exam, 0

        finally:
            self.downloader._close_driver()

    def run_batch_downloads(
        self,
        batch_size: int = 5,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[int, int]:
        """
        Download PDFs for multiple exams in batch.

        Args:
            batch_size: Number of exams to process
            log_callback: Optional callback for progress logging

        Returns:
            Tuple of (exams_completed, total_files_downloaded)
        """
        if log_callback:
            log_callback(f"\n🚀 Starting batch download ({batch_size} exams)\n")

        exams_completed = 0
        total_files = 0

        for i in range(1, batch_size + 1):
            if log_callback:
                log_callback(f"\n{'#' * 70}")
                log_callback(f"# EXAM {i}/{batch_size}")
                log_callback(f"{'#' * 70}\n")

            success, exam, count = self.run_next_download(log_callback)

            if success:
                exams_completed += 1
                total_files += count
            elif not exam:
                # No more unpublished exams
                if log_callback:
                    log_callback(f"\n✓ All exams completed!\n")
                break

        # Final summary
        if log_callback:
            log_callback(f"\n{'=' * 70}")
            log_callback(f"📊 BATCH COMPLETE")
            log_callback(f"{'=' * 70}")
            log_callback(f"Exams processed:  {exams_completed}/{batch_size}")
            log_callback(f"Total PDFs:       {total_files}")
            log_callback(f"{'=' * 70}\n")

        logger.info(
            f"Batch complete: {exams_completed} exams, {total_files} files"
        )

        return exams_completed, total_files


def run_auto_download(
    csv_path: Path,
    download_dir: Path,
    max_pdfs_per_exam: int = 15,
    log_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, int]:
    """
    Run automatic download for next unpublished exam.

    Args:
        csv_path: Path to CSV catalog
        download_dir: Directory to save PDFs
        max_pdfs_per_exam: Maximum PDFs per exam (default: 15)
        log_callback: Optional callback for logging

    Returns:
        Tuple of (success, files_downloaded)
    """
    workflow = DownloadWorkflow(csv_path, download_dir, max_pdfs_per_exam)
    success, exam, count = workflow.run_next_download(log_callback)
    return success, count
