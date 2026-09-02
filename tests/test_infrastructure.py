"""Tests for infrastructure modules — container, cache, metrics, tracing."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestContainer:
    """Test DI container module."""

    def test_container_importable(self) -> None:
        import unionbank.infrastructure.container as mod
        assert hasattr(mod, "__file__")

    def test_get_container_function(self) -> None:
        from unionbank.infrastructure.container import get_container
        import inspect
        sig = inspect.signature(get_container)
        assert sig.return_annotation is not inspect.Parameter.empty


class TestCache:
    """Test infrastructure cache module."""

    def test_cache_importable(self) -> None:
        import unionbank.infrastructure.cache as mod
        assert hasattr(mod, "__file__")


class TestMetrics:
    """Test infrastructure metrics module."""

    def test_metrics_importable(self) -> None:
        import unionbank.infrastructure.metrics as mod
        assert hasattr(mod, "__file__")


class TestTracing:
    """Test tracing module."""

    def test_tracing_importable(self) -> None:
        import unionbank.tracing as mod
        assert hasattr(mod, "__file__")


class TestLogging:
    """Test logging utilities."""

    def test_logger_importable(self) -> None:
        import unionbank.utils.logger as mod
        assert hasattr(mod, "__file__")

    def test_structured_logging_importable(self) -> None:
        import src.logging_utils.structured_logging as mod
        assert hasattr(mod, "__file__")


class TestDatabase:
    """Test database module."""

    def test_database_importable(self) -> None:
        import unionbank.infrastructure.database as mod
        assert hasattr(mod, "__file__")


class TestPersistence:
    """Test persistence module."""

    def test_persistence_importable(self) -> None:
        import unionbank.infrastructure.persistence as mod
        assert hasattr(mod, "__file__")


class TestMappers:
    """Test mappers module."""

    def test_mappers_importable(self) -> None:
        import unionbank.infrastructure.mappers as mod
        assert hasattr(mod, "__file__")


class TestBackwardCompat:
    """Test backward compatibility module."""

    def test_backward_compat_importable(self) -> None:
        import unionbank.infrastructure.backward_compat as mod
        assert hasattr(mod, "__file__")
