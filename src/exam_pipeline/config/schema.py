"""Configuration schema with Pydantic validation."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class ImageAssignmentConfig(BaseModel):
    """Image assignment algorithm configuration."""

    tolerance_y: int = Field(default=5, ge=0)
    max_offset: int = Field(default=150, ge=0)
    column_detection_enabled: bool = True


class PDFConfig(BaseModel):
    """PDF extraction configuration."""

    option_count: int = Field(default=4, ge=4, le=5)
    image_assignment: ImageAssignmentConfig = ImageAssignmentConfig()

    @field_validator("option_count")
    @classmethod
    def validate_option_count(cls, v: int) -> int:
        """Validate option count is 4 or 5."""
        if v not in [4, 5]:
            raise ValueError("option_count must be 4 or 5")
        return v


class RetryConfig(BaseModel):
    """Retry logic configuration."""

    max_attempts: int = Field(default=3, ge=1, le=10)
    delay: float = Field(default=2.0, ge=0.1)


class AIConfig(BaseModel):
    """AI processing configuration."""

    model: str = "o3-2025-04-16"
    chunk_size: int = Field(default=10, ge=1, le=100)
    max_concurrent: int = Field(default=5, ge=1, le=20)
    retry: RetryConfig = RetryConfig()
    timeout: float = Field(default=180.0, ge=10.0)


class CompressionConfig(BaseModel):
    """Audio compression configuration."""

    bitrate: str = "32k"
    sample_rate: int = 16000


class QuestionTTSConfig(BaseModel):
    """Question text-to-speech configuration."""

    provider: Literal["google"] = "google"
    voice: str = "ko-KR-Standard-D"
    speaking_rate: float = Field(default=0.9, ge=0.5, le=2.0)
    pitch: float = Field(default=-4.0, ge=-20.0, le=20.0)
    compression: CompressionConfig = CompressionConfig()


class LectureConfig(BaseModel):
    """Lecture audio configuration."""

    import_mode: bool = True
    output_dir: str = "assets/audio/summary"


class AudioConfig(BaseModel):
    """Audio generation configuration."""

    question_tts: QuestionTTSConfig = QuestionTTSConfig()
    lecture: LectureConfig = LectureConfig()


class LogoConfig(BaseModel):
    """Logo generation configuration."""

    size: int = Field(default=1024, ge=512, le=2048)
    background_colors: str = "auto"
    pattern_count: int = 25


class ScreenshotConfig(BaseModel):
    """Screenshot generation configuration."""

    devices: List[str] = [
        "iPhone 15 Pro Max",
        "iPad Pro (12.9-inch) (6th generation)",
    ]
    count: int = Field(default=15, ge=1, le=30)


class IOSConfig(BaseModel):
    """iOS-specific configuration."""

    deployment_target: str = "15.0"
    admob_app_id: str = "ca-app-pub-2598779635969436~4262650072"


class AppConfig(BaseModel):
    """App building configuration."""

    flutter_version: str = "3.x"
    logo: LogoConfig = LogoConfig()
    screenshot: ScreenshotConfig = ScreenshotConfig()
    ios: IOSConfig = IOSConfig()


class FastlaneConfig(BaseModel):
    """Fastlane configuration."""

    scheme: str = "Runner"
    workspace: str = "Runner.xcworkspace"
    export_method: Literal["app-store", "ad-hoc", "development"] = "app-store"


class AppStoreConfig(BaseModel):
    """App Store Connect configuration."""

    team_id: str = "CPHBF5XF4B"
    apple_id: str = "bombezzang2607@gmail.com"
    primary_category: str = "EDUCATION"
    secondary_category: str = "PRODUCTIVITY"
    copyright: str = "© 2025 Jongmin Kim"


class DeployConfig(BaseModel):
    """Deployment configuration."""

    fastlane: FastlaneConfig = FastlaneConfig()
    app_store: AppStoreConfig = AppStoreConfig()


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class Config(BaseModel):
    """Main configuration model."""

    pdf: PDFConfig = PDFConfig()
    ai: AIConfig = AIConfig()
    audio: AudioConfig = AudioConfig()
    app: AppConfig = AppConfig()
    deploy: DeployConfig = DeployConfig()
    logging: LoggingConfig = LoggingConfig()
