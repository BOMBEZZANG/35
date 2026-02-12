"""Configuration manager for loading and validating configuration."""

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

from .schema import Config


class ConfigManager:
    """Manages application configuration from YAML and environment variables."""

    _instance: Optional[Config] = None

    @classmethod
    def load(cls, config_path: Optional[Path] = None, env_path: Optional[Path] = None) -> Config:
        """
        Load configuration from YAML file and environment variables.

        Args:
            config_path: Path to config.yaml. Defaults to config/config.yaml
            env_path: Path to .env file. Defaults to config/.env

        Returns:
            Config: Validated configuration object

        Raises:
            FileNotFoundError: If config.yaml not found
            ValidationError: If configuration is invalid
        """
        if cls._instance is not None:
            return cls._instance

        # Load environment variables
        if env_path is None:
            env_path = cls._get_default_path("config/.env")

        if env_path.exists():
            load_dotenv(env_path)
        else:
            # Try to load from default locations
            load_dotenv()  # Load from .env in current directory

        # Load YAML configuration
        if config_path is None:
            config_path = cls._get_default_path("config/config.yaml")

        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                f"Copy config/config.yaml.example to config/config.yaml"
            )

        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Validate and create config object
        cls._instance = Config(**config_data)

        return cls._instance

    @classmethod
    def reload(cls) -> Config:
        """Reload configuration from disk."""
        cls._instance = None
        return cls.load()

    @classmethod
    def _get_default_path(cls, relative_path: str) -> Path:
        """
        Get default path relative to project root.

        Args:
            relative_path: Path relative to project root

        Returns:
            Path: Absolute path to file
        """
        # Try to find project root (directory containing pyproject.toml)
        current = Path.cwd()

        while current != current.parent:
            if (current / "pyproject.toml").exists():
                return current / relative_path
            current = current.parent

        # Fallback to current directory
        return Path.cwd() / relative_path

    @staticmethod
    def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable with optional default.

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            str: Environment variable value or default
        """
        return os.getenv(key, default)

    @staticmethod
    def get_openai_api_key() -> str:
        """
        Get OpenAI API key from environment.

        Returns:
            str: OpenAI API key

        Raises:
            ValueError: If API key not found
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables. "
                "Add it to config/.env or set as environment variable."
            )
        return api_key

    @staticmethod
    def get_google_credentials_path() -> Path:
        """
        Get Google Cloud credentials path from environment.

        Returns:
            Path: Path to Google Cloud credentials JSON

        Raises:
            ValueError: If credentials path not found or file doesn't exist
        """
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not cred_path:
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS not found in environment variables. "
                "Add it to config/.env or set as environment variable."
            )

        path = Path(cred_path)
        if not path.exists():
            raise ValueError(f"Google Cloud credentials file not found: {path}")

        return path

    @staticmethod
    def get_gcs_bucket_name() -> str:
        """
        Get Google Cloud Storage bucket name from environment.

        Returns:
            str: GCS bucket name

        Raises:
            ValueError: If bucket name not found
        """
        bucket = os.getenv("GCS_BUCKET_NAME")
        if not bucket:
            raise ValueError(
                "GCS_BUCKET_NAME not found in environment variables. "
                "Add it to config/.env or set as environment variable."
            )
        return bucket
