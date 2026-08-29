"""
Tests for UNION-BANK- interest calculation module.

Tests pure domain functions for interest computation.
"""


from unionbank.domain.interest import calculate_monthly_interest


class TestCalculateMonthlyInterest:
    """Test monthly interest calculation."""

    def test_basic_interest(self) -> None:
        result = calculate_monthly_interest(100000.0)
        # 100000 * 3.5 / 12 / 100 = 291.67
        assert result == 291.67

    def test_zero_balance(self) -> None:
        result = calculate_monthly_interest(0.0)
        assert result == 0.0

    def test_custom_rate(self) -> None:
        result = calculate_monthly_interest(100000.0, annual_rate_pct=6.0)
        # 100000 * 6.0 / 12 / 100 = 500.0
        assert result == 500.0

    def test_high_balance(self) -> None:
        result = calculate_monthly_interest(10000000.0)
        # 10M * 3.5 / 12 / 100 = 29166.67
        assert result == 29166.67

    def test_negative_balance(self) -> None:
        result = calculate_monthly_interest(-50000.0)
        assert result < 0

    def test_small_balance(self) -> None:
        result = calculate_monthly_interest(100.0)
        assert result == 0.29

    def test_zero_rate(self) -> None:
        result = calculate_monthly_interest(100000.0, annual_rate_pct=0.0)
        assert result == 0.0

    def test_high_rate(self) -> None:
        result = calculate_monthly_interest(100000.0, annual_rate_pct=12.0)
        # 100000 * 12 / 12 / 100 = 1000.0
        assert result == 1000.0
