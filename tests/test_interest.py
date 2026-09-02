"""Tests for domain.interest — pure interest calculation function."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow


class TestCalculateMonthlyInterest:
    """calculate_monthly_interest computes balance * rate / 12 / 100."""

    def test_default_rate(self) -> None:
        from unionbank.domain.interest import calculate_monthly_interest
        # 100000 * 3.5 / 12 / 100 = 291.666... → 291.67
        result = calculate_monthly_interest(100000)
        assert result == 291.67

    def test_zero_balance(self) -> None:
        from unionbank.domain.interest import calculate_monthly_interest
        assert calculate_monthly_interest(0) == 0.0

    def test_zero_rate(self) -> None:
        from unionbank.domain.interest import calculate_monthly_interest
        assert calculate_monthly_interest(100000, 0) == 0.0

    def test_high_rate(self) -> None:
        from unionbank.domain.interest import calculate_monthly_interest
        # 50000 * 12 / 12 / 100 = 500
        result = calculate_monthly_interest(50000, 12.0)
        assert result == 500.0

    def test_fractional_balance(self) -> None:
        from unionbank.domain.interest import calculate_monthly_interest
        result = calculate_monthly_interest(12345.67, 3.5)
        assert result == round(12345.67 * 3.5 / 12 / 100, 2)

    def test_return_type_is_float(self) -> None:
        from unionbank.domain.interest import calculate_monthly_interest
        assert isinstance(calculate_monthly_interest(100000), float)

    def test_large_balance(self) -> None:
        from unionbank.domain.interest import calculate_monthly_interest
        result = calculate_monthly_interest(10_000_000, 3.5)
        assert result > 0
