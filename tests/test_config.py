"""Tests for UNION-BANK- configuration module."""

import os

import pytest

from unionbank.config import Config, _require_env, _optional_env

pytestmark = pytest.mark.unit



class TestRequireEnv:
    """Tests for _require_env helper."""

    def test_returns_value(self, monkeypatch: object) -> None:
        monkeypatch.setenv("TEST_ENV_VAR", "hello")  # type: ignore
        assert _require_env("TEST_ENV_VAR") == "hello"

    def test_returns_default(self) -> None:
        assert _require_env("NONEXISTENT_VAR_XYZ", "fallback") == "fallback"

    def test_raises_on_missing(self) -> None:
        with pytest.raises(RuntimeError, match="Missing required"):
            _require_env("NONEXISTENT_VAR_XYZ")


class TestOptionalEnv:
    """Tests for _optional_env helper."""

    def test_returns_value(self, monkeypatch: object) -> None:
        monkeypatch.setenv("TEST_OPT_VAR", "world")  # type: ignore
        assert _optional_env("TEST_OPT_VAR") == "world"

    def test_returns_default(self) -> None:
        assert _optional_env("NONEXISTENT_OPT", "fallback") == "fallback"

    def test_returns_none(self) -> None:
        assert _optional_env("NONEXISTENT_OPT") is None


class TestConfig:
    """Tests for Config dataclass."""

    def test_config_is_frozen(self) -> None:
        config = Config()
        with pytest.raises(AttributeError):
            config.JWT_SECRET = "new-secret"  # type: ignore

    def test_has_required_fields(self) -> None:
        config = Config()
        assert hasattr(config, "JWT_SECRET")
        assert hasattr(config, "FLASK_SECRET_KEY")
        assert hasattr(config, "TRANSACTION_CATEGORIES")
