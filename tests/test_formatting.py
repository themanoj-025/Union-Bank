"""
Tests for UNION-BANK- formatting and ID generation module.

Tests currency formatting, timestamp helpers, and ID generators.
"""



from unionbank.utils.formatting import (
    fmt_currency,
    generate_account_number,
    generate_goal_id,
    generate_loan_id,
    generate_notification_id,
    generate_transaction_id,
    now_str,
)


class TestFmtCurrency:
    """Test Indian Rupee formatting."""

    def test_basic_amount(self) -> None:
        assert fmt_currency(1234.56) == "₹1,234.56"

    def test_zero(self) -> None:
        assert fmt_currency(0.0) == "₹0.00"

    def test_large_amount(self) -> None:
        result = fmt_currency(1000000.0)
        assert "₹" in result
        assert result[1:] == "1,000,000.00"

    def test_negative_amount(self) -> None:
        result = fmt_currency(-500.0)
        assert "₹" in result


class TestNowStr:
    """Test timestamp formatting."""

    def test_returns_string(self) -> None:
        result = now_str()
        assert isinstance(result, str)

    def test_format_contains_dashes(self) -> None:
        result = now_str()
        assert "-" in result


class TestIDGenerators:
    """Test ID generation functions."""

    def test_transaction_id_format(self) -> None:
        tid = generate_transaction_id()
        assert tid.startswith("TXN-")
        assert len(tid) == 12  # TXN- + 8 chars

    def test_account_number_format(self) -> None:
        acc = generate_account_number()
        assert len(acc) == 10
        assert acc.isdigit()

    def test_account_number_unique(self) -> None:
        acc1 = generate_account_number()
        acc2 = generate_account_number()
        # With 10^10 possibilities, collision is astronomically unlikely
        assert acc1 != acc2

    def test_goal_id_format(self) -> None:
        gid = generate_goal_id()
        assert gid.startswith("GOAL-")
        assert len(gid) == 13  # GOAL- + 8 chars

    def test_loan_id_format(self) -> None:
        lid = generate_loan_id()
        assert lid.startswith("LON-")
        assert len(lid) == 12  # LON- + 8 chars

    def test_notification_id_format(self) -> None:
        nid = generate_notification_id()
        assert nid.startswith("NTF-")
        assert len(nid) == 13  # NTF- + 8 chars

    def test_all_ids_alphanumeric(self) -> None:
        for gen in [generate_transaction_id, generate_goal_id, generate_loan_id, generate_notification_id]:
            id_val = gen()
            # Remove prefix and check remaining chars are alphanumeric
            prefix_end = id_val.index("-") + 1
            suffix = id_val[prefix_end:]
            assert suffix.isalnum(), f"Non-alphanumeric chars in {id_val}"
