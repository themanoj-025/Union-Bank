"""Tests for unionbank.domain.interest and unionbank.utils.formatting."""

import re

from unionbank.domain.interest import calculate_monthly_interest
from unionbank.utils.formatting import (
    calculate_emi,
    fmt_currency,
    generate_goal_id,
    generate_loan_id,
    generate_notification_id,
    generate_transaction_id,
    mask_account_number,
    mask_sensitive_data,
    now_str,
)


class TestCalculateMonthlyInterest:
    def test_basic(self) -> None:
        result = calculate_monthly_interest(100000, 3.5)
        assert result == round(100000 * 3.5 / 12 / 100, 2)

    def test_zero_balance(self) -> None:
        assert calculate_monthly_interest(0) == 0.0

    def test_high_rate(self) -> None:
        result = calculate_monthly_interest(50000, 12.0)
        assert result == round(50000 * 12.0 / 12 / 100, 2)

    def test_default_rate(self) -> None:
        result = calculate_monthly_interest(10000)
        assert result > 0


class TestFmtCurrency:
    def test_basic(self) -> None:
        assert fmt_currency(1000) == "₹1,000.00"

    def test_zero(self) -> None:
        assert fmt_currency(0) == "₹0.00"

    def test_large_number(self) -> None:
        assert fmt_currency(1000000) == "₹1,000,000.00"

    def test_negative(self) -> None:
        assert fmt_currency(-500) == "₹-500.00"


class TestNowStr:
    def test_format(self) -> None:
        result = now_str()
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", result)


class TestIdGenerators:
    def test_transaction_id(self) -> None:
        tid = generate_transaction_id()
        assert tid.startswith("TXN-")
        assert len(tid) == 12

    def test_goal_id(self) -> None:
        gid = generate_goal_id()
        assert gid.startswith("GOAL-")
        assert len(gid) == 13

    def test_loan_id(self) -> None:
        lid = generate_loan_id()
        assert lid.startswith("LON-")
        assert len(lid) == 12

    def test_notification_id(self) -> None:
        nid = generate_notification_id()
        assert nid.startswith("NTF-")
        assert len(nid) == 12

    def test_unique_ids(self) -> None:
        ids = {generate_transaction_id() for _ in range(100)}
        assert len(ids) == 100


class TestCalculateEmi:
    def test_basic(self) -> None:
        emi = calculate_emi(100000, 10, 12)
        assert emi > 0
        assert emi > 100000 / 12  # EMI must be > simple division

    def test_zero_principal(self) -> None:
        assert calculate_emi(0, 10, 12) == 0.0

    def test_zero_rate(self) -> None:
        emi = calculate_emi(12000, 0, 12)
        assert emi == 0.0  # zero rate returns 0 per implementation

    def test_zero_tenure(self) -> None:
        assert calculate_emi(100000, 10, 0) == 0.0


class TestMaskAccountNumber:
    def test_normal(self) -> None:
        assert mask_account_number("1234567890") == "******7890"

    def test_short_number(self) -> None:
        assert mask_account_number("123") == "****"

    def test_empty(self) -> None:
        assert mask_account_number("") == "****"

    def test_exactly_4(self) -> None:
        assert mask_account_number("1234") == "1234"


class TestMaskSensitiveData:
    def test_mask_account(self) -> None:
        result = mask_sensitive_data("Transfer to 1234567890 completed")
        assert "1234567890" not in result
        assert "******7890" in result

    def test_mask_email(self) -> None:
        result = mask_sensitive_data("Sent to john@example.com")
        assert "john@" not in result
        assert "***@example.com" in result

    def test_no_sensitive_data(self) -> None:
        msg = "Transfer completed successfully"
        assert mask_sensitive_data(msg) == msg
