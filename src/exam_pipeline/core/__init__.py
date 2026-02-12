"""Core data models, database, and exceptions."""

from .database import OXQuizDatabase, QuestionDatabase
from .exceptions import (
    AIGenerationError,
    AppBuildError,
    AudioGenerationError,
    ConfigurationError,
    DatabaseError,
    DeploymentError,
    ExamPipelineError,
    FastlaneError,
    ImageAssignmentError,
    LogoGenerationError,
    OCRError,
    PDFExtractionError,
    QuestionDetectionError,
    ScreenshotError,
    TTSError,
)
from .models import (
    AppMetadata,
    LectureScript,
    OXQuiz,
    Question,
    QuestionMarker,
    QuestionRange,
    StudyNote,
)

__all__ = [
    # Database
    "QuestionDatabase",
    "OXQuizDatabase",
    # Models
    "Question",
    "QuestionMarker",
    "QuestionRange",
    "OXQuiz",
    "StudyNote",
    "LectureScript",
    "AppMetadata",
    # Exceptions
    "ExamPipelineError",
    "ConfigurationError",
    "PDFExtractionError",
    "ImageAssignmentError",
    "QuestionDetectionError",
    "DatabaseError",
    "AIGenerationError",
    "OCRError",
    "AudioGenerationError",
    "TTSError",
    "AppBuildError",
    "LogoGenerationError",
    "ScreenshotError",
    "DeploymentError",
    "FastlaneError",
]
