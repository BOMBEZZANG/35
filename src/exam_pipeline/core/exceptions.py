"""Custom exceptions for the exam pipeline."""


class ExamPipelineError(Exception):
    """Base exception for all exam pipeline errors."""

    pass


class ConfigurationError(ExamPipelineError):
    """Configuration-related errors."""

    pass


class PDFExtractionError(ExamPipelineError):
    """PDF parsing and extraction errors."""

    pass


class ImageAssignmentError(PDFExtractionError):
    """6-stage image assignment algorithm errors."""

    pass


class QuestionDetectionError(PDFExtractionError):
    """Question boundary detection errors."""

    pass


class DatabaseError(ExamPipelineError):
    """Database operation errors."""

    pass


class AIGenerationError(ExamPipelineError):
    """AI content generation errors."""

    pass


class OCRError(AIGenerationError):
    """OCR processing errors."""

    pass


class AudioGenerationError(ExamPipelineError):
    """Audio generation and processing errors."""

    pass


class TTSError(AudioGenerationError):
    """Text-to-speech errors."""

    pass


class AudioCompressionError(AudioGenerationError):
    """Audio compression (FFmpeg) errors."""

    pass


class AppBuildError(ExamPipelineError):
    """Flutter app building errors."""

    pass


class LogoGenerationError(AppBuildError):
    """Logo generation errors."""

    pass


class ScreenshotError(AppBuildError):
    """Screenshot generation errors."""

    pass


class DeploymentError(ExamPipelineError):
    """App Store deployment errors."""

    pass


class FastlaneError(DeploymentError):
    """Fastlane automation errors."""

    pass


class AppStoreError(DeploymentError):
    """App Store Connect API errors."""

    pass
