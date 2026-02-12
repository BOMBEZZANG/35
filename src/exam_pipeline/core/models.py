"""Core data models for exam questions and related entities."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Union


@dataclass
class Question:
    """
    Represents an exam question with all its components.

    Supports both 4-option and 5-option question formats.
    """

    question_id: int
    question_number: str
    big_question: str  # Main question text
    options: List[Union[str, bytes]]  # Length 4 or 5, can be text or BLOB
    correct_option: int  # 1-based index (1-5)
    category: str
    option_count: int  # 4 or 5

    # Optional fields
    question_image: Optional[bytes] = None  # Question BLOB
    big_question_special_image: Optional[bytes] = None  # Big question special BLOB
    exam_session: Optional[str] = None
    answer_description: Optional[str] = None
    audio_path: Optional[str] = None
    date_information: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate question data after initialization."""
        if self.option_count not in [4, 5]:
            raise ValueError(f"option_count must be 4 or 5, got {self.option_count}")

        if len(self.options) != self.option_count:
            raise ValueError(
                f"options length ({len(self.options)}) must match "
                f"option_count ({self.option_count})"
            )

        if not (1 <= self.correct_option <= self.option_count):
            raise ValueError(
                f"correct_option ({self.correct_option}) must be between "
                f"1 and {self.option_count}"
            )

    @property
    def has_images(self) -> bool:
        """Check if question contains any image BLOBs."""
        return any(isinstance(opt, bytes) for opt in self.options) or bool(
            self.question_image or self.big_question_special_image
        )

    @property
    def is_text_only(self) -> bool:
        """Check if question is text-only (no images)."""
        return not self.has_images

    def to_dict(self) -> dict:
        """Convert question to dictionary representation."""
        return {
            "question_id": self.question_id,
            "question_number": self.question_number,
            "big_question": self.big_question,
            "question_image": self.question_image,
            "big_question_special_image": self.big_question_special_image,
            "options": self.options,
            "correct_option": self.correct_option,
            "option_count": self.option_count,
            "category": self.category,
            "exam_session": self.exam_session,
            "answer_description": self.answer_description,
            "audio_path": self.audio_path,
            "date_information": self.date_information,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class QuestionMarker:
    """
    Marks the start position of a question in a PDF.

    Used by PDF extraction algorithm to identify question boundaries.
    """

    page_num: int
    question_num: int
    bbox: tuple  # (x0, y0, x1, y1)
    block_index: int

    def __lt__(self, other: "QuestionMarker") -> bool:
        """Compare markers for sorting (by page, then block index)."""
        if self.page_num != other.page_num:
            return self.page_num < other.page_num
        return self.block_index < other.block_index


@dataclass
class QuestionRange:
    """
    Defines the extraction range for a question in a PDF.

    Contains start/end markers and page boundaries.
    """

    start_marker: QuestionMarker
    end_marker: Optional[QuestionMarker]
    start_page: int
    end_page: int

    @property
    def question_number(self) -> int:
        """Get question number from start marker."""
        return self.start_marker.question_num

    @property
    def spans_multiple_pages(self) -> bool:
        """Check if question spans multiple PDF pages."""
        return self.start_page != self.end_page


@dataclass
class OXQuiz:
    """
    Represents an O/X (True/False) quiz question.
    """

    question_id: int
    big_question: str  # Quiz statement
    correct_option: int  # 1 for O (True), 2 for X (False)
    category: str
    answer_description: str

    # Fixed options
    option1: str = "O"
    option2: str = "X"

    def is_true(self) -> bool:
        """Check if correct answer is True (O)."""
        return self.correct_option == 1

    def is_false(self) -> bool:
        """Check if correct answer is False (X)."""
        return self.correct_option == 2

    def to_dict(self) -> dict:
        """Convert quiz to dictionary representation."""
        return {
            "question_id": self.question_id,
            "big_question": self.big_question,
            "option1": self.option1,
            "option2": self.option2,
            "correct_option": self.correct_option,
            "category": self.category,
            "answer_description": self.answer_description,
        }


@dataclass
class StudyNote:
    """
    Represents a study note for a category.
    """

    category: str
    content: str
    related_questions: List[dict] = field(default_factory=list)

    def add_related_question(self, date: str, question_id: int) -> None:
        """Add a related question reference."""
        self.related_questions.append({"date": date, "question_id": question_id})

    def to_dict(self) -> dict:
        """Convert study note to dictionary representation."""
        return {
            "category": self.category,
            "content": self.content,
            "related_questions": self.related_questions,
        }


@dataclass
class LectureScript:
    """
    Represents a lecture script for audio generation.
    """

    category: str
    index: int  # Lecture number (1, 2, 3...)
    content: str
    audio_path: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert lecture script to dictionary representation."""
        return {
            "category": self.category,
            "index": self.index,
            "content": self.content,
            "audio_path": self.audio_path,
        }


@dataclass
class AppMetadata:
    """
    Metadata for Flutter app generation.
    """

    bundle_id: str
    app_name: str
    version: str = "1.0.0"
    build_number: int = 1
    description: str = ""
    keywords: List[str] = field(default_factory=list)
    privacy_url: Optional[str] = None
    support_url: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert metadata to dictionary representation."""
        return {
            "bundle_id": self.bundle_id,
            "app_name": self.app_name,
            "version": self.version,
            "build_number": self.build_number,
            "description": self.description,
            "keywords": self.keywords,
            "privacy_url": self.privacy_url,
            "support_url": self.support_url,
        }
