"""Tests for configuration module."""

import pytest
import tempfile
import toml
from pathlib import Path
from scribe.config import Config


class TestConfig:
    """Test configuration management."""

    def test_default_config(self):
        """Test that default configuration is loaded correctly."""
        config = Config()
        assert config["model"]["size"] == "tiny.en"
        assert config["audio"]["sample_rate"] == 16000
        assert config["output"]["mode"] == "type"

    def test_load_custom_config(self, tmp_path):
        """Test loading custom configuration from file."""
        # Create custom config
        custom_config = {
            "model": {"size": "base.en", "device": "cpu"},
            "audio": {"sample_rate": 16000},
        }

        config_file = tmp_path / "config.toml"
        with open(config_file, "w") as f:
            toml.dump(custom_config, f)

        # Load config
        config = Config(config_path=str(config_file))
        assert config["model"]["size"] == "base.en"
        # Default values should still be present
        assert config["audio"]["sample_rate"] == 16000

    def test_deep_merge(self):
        """Test deep merging of configurations."""
        config = Config()
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        override = {"a": {"b": 10}, "e": 4}

        result = config._deep_merge(base, override)

        assert result["a"]["b"] == 10  # Overridden
        assert result["a"]["c"] == 2  # Preserved
        assert result["d"] == 3  # Preserved
        assert result["e"] == 4  # Added

    def test_get_config_value(self):
        """Test getting configuration values."""
        config = Config()
        assert config.get("model", "size") == "tiny.en"
        assert config.get("nonexistent", "key", "default") == "default"

    def test_save_config(self, tmp_path):
        """Test saving configuration to file."""
        config_file = tmp_path / "config.toml"
        config = Config(config_path=str(config_file))

        # Modify config
        config.config["model"]["size"] = "base.en"

        # Save
        config.save()

        # Load again and verify
        config2 = Config(config_path=str(config_file))
        assert config2["model"]["size"] == "base.en"

    def test_config_path_detection(self, monkeypatch, tmp_path):
        """Test configuration path detection."""
        # Set XDG_CONFIG_HOME
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

        config = Config()
        expected_path = tmp_path / "scribe" / "config.toml"
        assert config.config_path == expected_path
