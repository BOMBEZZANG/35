"""CSV manager for tracking exam download status."""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExamRecord:
    """Represents a single exam record from CSV."""

    title: str
    view_count: int
    url: str
    published: bool
    row_index: int  # Track position in CSV for updates

    @property
    def is_published(self) -> bool:
        """Check if exam is already published."""
        return self.published

    def __repr__(self) -> str:
        status = "✓ Published" if self.published else "○ Unpublished"
        return f"ExamRecord({self.title[:30]}..., views={self.view_count:,}, {status})"


class ExamCatalog:
    """
    Manages exam catalog CSV file.

    Handles:
    - Reading exam records
    - Filtering unpublished exams
    - Selecting by view count
    - Updating published status
    """

    def __init__(self, csv_path: Path):
        """
        Initialize exam catalog.

        Args:
            csv_path: Path to comcbt_data_published.csv
        """
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        self.records: List[ExamRecord] = []
        self._load_records()

    def _load_records(self) -> None:
        """Load all records from CSV."""
        logger.info(f"Loading exam catalog from: {self.csv_path}")

        self.records = []

        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_index, row in enumerate(reader, start=1):
                try:
                    # Parse view_count (handle empty strings)
                    view_count_str = row.get("view_count", "0").strip()
                    view_count = int(view_count_str) if view_count_str else 0

                    # Parse published status (Y = published, empty = unpublished)
                    published_str = row.get("Published", "").strip().upper()
                    published = published_str == "Y"

                    record = ExamRecord(
                        title=row.get("title", "").strip(),
                        view_count=view_count,
                        url=row.get("url", "").strip(),
                        published=published,
                        row_index=row_index,
                    )

                    self.records.append(record)

                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping invalid row {row_index}: {e}")
                    continue

        logger.info(f"Loaded {len(self.records)} exam records")

    def get_unpublished_exams(self) -> List[ExamRecord]:
        """
        Get all unpublished exams.

        Returns:
            List of ExamRecord objects where published=False
        """
        unpublished = [r for r in self.records if not r.is_published]
        logger.info(
            f"Found {len(unpublished)} unpublished exams "
            f"(out of {len(self.records)} total)"
        )
        return unpublished

    def get_top_unpublished_exam(self) -> Optional[ExamRecord]:
        """
        Get unpublished exam with highest view count.

        Returns:
            ExamRecord with highest views, or None if all published
        """
        unpublished = self.get_unpublished_exams()

        if not unpublished:
            logger.warning("No unpublished exams found")
            return None

        # Sort by view_count descending
        top_exam = max(unpublished, key=lambda r: r.view_count)

        logger.info(
            f"Selected top exam: {top_exam.title} "
            f"({top_exam.view_count:,} views)"
        )

        return top_exam

    def mark_as_published(self, exam_record: ExamRecord) -> None:
        """
        Mark an exam as published in CSV.

        Args:
            exam_record: ExamRecord to mark as published
        """
        logger.info(f"Marking as published: {exam_record.title}")

        # Read all rows
        rows = []
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

            for row_index, row in enumerate(reader, start=1):
                # Update the matching row
                if row_index == exam_record.row_index:
                    row["Published"] = "Y"
                    logger.info(f"Updated row {row_index}: Published=Y")

                rows.append(row)

        # Write back to CSV
        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"CSV updated: {self.csv_path}")

        # Update in-memory record
        exam_record.published = True

    def get_statistics(self) -> dict:
        """
        Get catalog statistics.

        Returns:
            Dictionary with stats
        """
        total = len(self.records)
        published = sum(1 for r in self.records if r.is_published)
        unpublished = total - published

        return {
            "total_exams": total,
            "published": published,
            "unpublished": unpublished,
            "completion_rate": (published / total * 100) if total > 0 else 0,
        }

    def print_statistics(self) -> None:
        """Print catalog statistics."""
        stats = self.get_statistics()

        print("\n" + "=" * 50)
        print("📊 Exam Catalog Statistics")
        print("=" * 50)
        print(f"Total exams:     {stats['total_exams']:,}")
        print(f"Published:       {stats['published']:,}")
        print(f"Unpublished:     {stats['unpublished']:,}")
        print(f"Completion:      {stats['completion_rate']:.1f}%")
        print("=" * 50 + "\n")

    def list_top_unpublished(self, limit: int = 10) -> None:
        """
        Print top unpublished exams by view count.

        Args:
            limit: Number of exams to show
        """
        unpublished = self.get_unpublished_exams()

        if not unpublished:
            print("✓ All exams have been published!")
            return

        # Sort by view count descending
        sorted_exams = sorted(unpublished, key=lambda r: r.view_count, reverse=True)
        top_exams = sorted_exams[:limit]

        print(f"\n🔝 Top {len(top_exams)} Unpublished Exams (by views):")
        print("-" * 80)

        for i, exam in enumerate(top_exams, start=1):
            print(f"{i:2d}. {exam.view_count:>8,} views | {exam.title[:50]}")

        print("-" * 80 + "\n")
