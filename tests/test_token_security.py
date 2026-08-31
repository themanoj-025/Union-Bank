"""Tests for UNION-BANK- token security utilities."""

import hashlib

import pytest

from unionbank.utils.token_security import hash_token_id


class TestHashTokenId:
    """Tests for refresh token ID hashing."""

    def test_returns_hex_string(self) -> None:
        result = hash_token_id("abc123")
        assert isinstance(result, str)
        assert all(c in "0123456789abcdef" for c in result)

    def test_sha256_length(self) -> None:
        result = hash_token_id("test")
        assert len(result) == 64  # SHA-256 hex digest is 64 chars

    def test_deterministic(self) -> None:
        r1 = hash_token_id("same-input")
        r2 = hash_token_id("same-input")
        assert r1 == r2

    def test_different_inputs(self) -> None:
        r1 = hash_token_id("token-a")
        r2 = hash_token_id("token-b")
        assert r1 != r2

    def test_matches_manual_sha256(self) -> None:
        token = "my-refresh-token-id"
        expected = hashlib.sha256(token.encode("utf-8")).hexdigest()
        assert hash_token_id(token) == expected

    def test_empty_string(self) -> None:
        result = hash_token_id("")
        assert len(result) == 64

    def test_unicode_token(self) -> None:
        result = hash_token_id("tokén-üñíçödé")
        assert len(result) == 64
