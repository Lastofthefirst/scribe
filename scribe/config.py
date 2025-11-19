"""Configuration management for Scribe."""

import os
import toml
from pathlib import Path
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


class Config:
    """Manages Scribe configuration."""

    DEFAULT_CONFIG = {
        "model": {
            "size": "tiny.en",
            "device": "cpu",
            "compute_type": "int8",
        },
        "audio": {
            "sample_rate": 16000,
            "channels": 1,
            "vad_aggressiveness": 3,
            "silence_duration": 1.5,
            "min_audio_duration": 0.5,
        },
        "output": {
            "mode": "type",
            "typing_delay": 0.0,
            "auto_enter": False,
        },
        "notifications": {
            "show_notification": True,
            "play_bell": True,
            "bell_sound": "system",
            "notification_timeout": 3000,
        },
        "advanced": {
            "keep_model_loaded": False,
            "daemon_mode": False,
            "log_level": "INFO",
        },
    }

    def __init__(self, config_path: str = None):
        """Initialize configuration.

        Args:
            config_path: Path to config file. If None, uses default locations.
        """
        self.config_path = self._get_config_path(config_path)
        self.config = self._load_config()
        self._setup_logging()

    def _get_config_path(self, config_path: str = None) -> Path:
        """Get configuration file path.

        Args:
            config_path: Optional custom config path.

        Returns:
            Path to configuration file.
        """
        if config_path:
            return Path(config_path)

        # Try XDG_CONFIG_HOME first
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            config_dir = Path(xdg_config) / "scribe"
        else:
            config_dir = Path.home() / ".config" / "scribe"

        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.toml"

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults.

        Returns:
            Configuration dictionary.
        """
        if self.config_path.exists():
            try:
                user_config = toml.load(self.config_path)
                # Merge with defaults (user config overrides defaults)
                config = self._deep_merge(self.DEFAULT_CONFIG.copy(), user_config)
                logger.info(f"Loaded configuration from {self.config_path}")
                return config
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_path}: {e}")
                logger.info("Using default configuration")
                return self.DEFAULT_CONFIG.copy()
        else:
            logger.info(f"No config file found at {self.config_path}, using defaults")
            return self.DEFAULT_CONFIG.copy()

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries.

        Args:
            base: Base dictionary.
            override: Dictionary with overriding values.

        Returns:
            Merged dictionary.
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _setup_logging(self):
        """Setup logging based on configuration."""
        log_level = self.config["advanced"]["log_level"]
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            section: Configuration section.
            key: Configuration key.
            default: Default value if not found.

        Returns:
            Configuration value.
        """
        return self.config.get(section, {}).get(key, default)

    def save(self, config: Dict[str, Any] = None):
        """Save configuration to file.

        Args:
            config: Configuration to save. If None, saves current config.
        """
        if config:
            self.config = config

        try:
            with open(self.config_path, "w") as f:
                toml.dump(self.config, f)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

    def create_example_config(self):
        """Create example configuration file."""
        example_path = self.config_path.parent / "config.example.toml"
        try:
            with open(example_path, "w") as f:
                toml.dump(self.DEFAULT_CONFIG, f)
            logger.info(f"Example configuration created at {example_path}")
        except Exception as e:
            logger.error(f"Failed to create example config: {e}")

    def __getitem__(self, key: str) -> Any:
        """Get configuration section.

        Args:
            key: Section name.

        Returns:
            Configuration section.
        """
        return self.config[key]

    def __repr__(self) -> str:
        """String representation of configuration."""
        return f"Config(path={self.config_path})"
