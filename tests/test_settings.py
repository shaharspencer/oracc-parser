"""Tests for settings module and .env loading."""

import os

import pytest

from oracc_parser.settings import get_settings, data_dir, log_level


class TestSettings:
    """Settings should load with sensible defaults."""

    def test_default_log_level(self):
        assert log_level() == "INFO"

    def test_data_dir_is_path(self):
        d = data_dir()
        assert hasattr(d, "exists")  # It's a Path

    def test_settings_returns_dict(self):
        s = get_settings()
        assert isinstance(s, dict)
        assert "zenodo_record_url" in s
        assert "data_dir" in s
        assert "translations_dir" in s

    def test_env_override(self, monkeypatch):
        """Environment variables should override defaults."""
        # Clear the lru_cache first
        get_settings.cache_clear()
        monkeypatch.setenv("ORACC_LOG_LEVEL", "DEBUG")
        s = get_settings()
        assert s["log_level"] == "DEBUG"
        # Clean up
        get_settings.cache_clear()
