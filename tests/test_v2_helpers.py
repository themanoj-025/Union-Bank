"""Tests for entrypoints.api.v2.helpers — response builders and exception handlers."""

from __future__ import annotations

import pytest

from unionbank.entrypoints.api.models import ApiResponse

pytestmark = pytest.mark.slow


class TestOk:
    """_ok builds success responses."""

    def test_ok_with_data(self) -> None:
        from unionbank.entrypoints.api.v2.helpers import _ok
        resp = _ok({"key": "value"})
        assert resp.success is True
        assert resp.data == {"key": "value"}

    def test_ok_with_string_data(self) -> None:
        from unionbank.entrypoints.api.v2.helpers import _ok
        resp = _ok("hello")
        assert resp.success is True
        assert resp.data == "hello"

    def test_ok_with_meta(self) -> None:
        from unionbank.entrypoints.api.v2.helpers import _ok
        resp = _ok("data", meta={"page": 1})
        assert resp.success is True
        assert resp.meta == {"page": 1}

    def test_ok_without_meta(self) -> None:
        from unionbank.entrypoints.api.v2.helpers import _ok
        resp = _ok("data")
        assert resp.success is True
        assert resp.meta is None


class TestErr:
    """_err raises HTTPException with envelope body."""

    def test_err_raises_http_exception(self) -> None:
        from fastapi import HTTPException
        from unionbank.entrypoints.api.v2.helpers import _err
        with pytest.raises(HTTPException) as exc_info:
            _err("Something went wrong", 400)
        assert exc_info.value.status_code == 400

    def test_err_default_status(self) -> None:
        from fastapi import HTTPException
        from unionbank.entrypoints.api.v2.helpers import _err
        with pytest.raises(HTTPException) as exc_info:
            _err("Error")
        assert exc_info.value.status_code == 400

    def test_err_with_error_code(self) -> None:
        from fastapi import HTTPException
        from unionbank.entrypoints.api.v2.helpers import _err
        with pytest.raises(HTTPException) as exc_info:
            _err("Invalid", 422, "VALIDATION_ERROR")
        assert exc_info.value.status_code == 422
        detail = exc_info.value.detail
        assert detail["success"] is False
        assert detail["meta"]["error_code"] == "VALIDATION_ERROR"


class TestFmtCurrency:
    """_fmt_currency formats monetary values."""

    def test_fmt_currency(self) -> None:
        from unionbank.entrypoints.api.v2.helpers import _fmt_currency
        result = _fmt_currency(100000.0)
        assert "100,000" in result or "100000" in result

    def test_fmt_currency_zero(self) -> None:
        from unionbank.entrypoints.api.v2.helpers import _fmt_currency
        result = _fmt_currency(0.0)
        assert "0" in result


class TestV2ExceptionHandler:
    """v2_http_exception_handler returns ApiResponse envelope."""

    @pytest.mark.asyncio
    async def test_handler_returns_json_response(self) -> None:
        from fastapi import HTTPException
        from unionbank.entrypoints.api.v2.helpers import v2_http_exception_handler
        from starlette.requests import Request

        exc = HTTPException(status_code=404, detail="Not found")
        scope = {"type": "http", "method": "GET", "path": "/", "query_string": b""}
        request = Request(scope)
        response = await v2_http_exception_handler(request, exc)
        assert response.status_code == 404


class TestV2GenericExceptionHandler:
    """v2_generic_exception_handler catches unhandled exceptions."""

    @pytest.mark.asyncio
    async def test_handler_returns_500(self) -> None:
        from starlette.requests import Request
        from unionbank.entrypoints.api.v2.helpers import v2_generic_exception_handler

        exc = ValueError("boom")
        scope = {"type": "http", "method": "GET", "path": "/", "query_string": b""}
        request = Request(scope)
        response = await v2_generic_exception_handler(request, exc)
        assert response.status_code == 500
