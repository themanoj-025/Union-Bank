"""Tests for UNION-BANK- password hashing (bcrypt)."""

import bcrypt
import pytest

from unionbank.utils.hashing import hash_password, verify_password


class TestHashPassword:
    """Tests for password hashing."""

    def test_returns_string(self) -> None:
        result = hash_password("TestPass123")
        assert isinstance(result, str)

    def test_hash_differs_from_plaintext(self) -> None:
        result = hash_password("TestPass123")
        assert result != "TestPass123"

    def test_different_hashes_each_time(self) -> None:
        h1 = hash_password("TestPass123")
        h2 = hash_password("TestPass123")
        assert h1 != h2  # Salt makes each hash unique

    def test_hash_is_bcrypt_format(self) -> None:
        result = hash_password("TestPass123")
        # bcrypt hashes start with $2b$
        assert result.startswith("$2b$")


class TestVerifyPassword:
    """Tests for password verification."""

    def test_correct_password(self) -> None:
        hashed = hash_password("MyStr0ngPass")
        assert verify_password("MyStr0ngPass", hashed) is True

    def test_wrong_password(self) -> None:
        hashed = hash_password("MyStr0ngPass")
        assert verify_password("WrongPass123", hashed) is False

    def test_empty_password(self) -> None:
        hashed = hash_password("")
        assert verify_password("", hashed) is True

    def test_invalid_hash(self) -> None:
        assert verify_password("test", "not-a-hash") is False

    def test_none_hash(self) -> None:
        assert verify_password("test", None) is False

    def test_round_trip_various(self) -> None:
        passwords = ["abc", "Password1!", "x" * 72, "unicode-test-日本語"]
        for pwd in passwords:
            h = hash_password(pwd)
            assert verify_password(pwd, h) is True
