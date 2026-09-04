from pathlib import Path
"""Tests for UNION-BANK- CSV export module."""

import csv
import os
import tempfile

import pytest

from unionbank.utils.csv_export import export_transactions_to_csv, generate_csv_filename


class TestExportTransactionsToCsv:
    """Tests for transaction CSV export."""

    def test_creates_file(self, tmp_path: Path) -> None:
        filepath = str(tmp_path / "test.csv")
        records = [
            {"txn_id": "T001", "timestamp": "2025-01-01", "type": "DEPOSIT", "amount": 1000, "balance": 5000, "description": "Salary", "category": "Income"},
        ]
        result = export_transactions_to_csv("ACC001", records, filepath)
        assert os.path.exists(result)

    def test_csv_has_header(self, tmp_path: Path) -> None:
        filepath = str(tmp_path / "test.csv")
        export_transactions_to_csv("ACC001", [], filepath)
        with open(filepath) as f:
            reader = csv.reader(f)
            header = next(reader)
            assert "Transaction ID" in header[0]
            assert "Amount" in header[3]

    def test_deposit_positive_sign(self, tmp_path: Path) -> None:
        filepath = str(tmp_path / "test.csv")
        records = [
            {"txn_id": "T001", "timestamp": "2025-01-01", "type": "DEPOSIT", "amount": 500, "balance": 1000, "description": "", "category": "General"},
        ]
        export_transactions_to_csv("ACC001", records, filepath)
        with open(filepath) as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            row = next(reader)
            assert row[3].startswith("+")

    def test_withdraw_negative_sign(self, tmp_path: Path) -> None:
        filepath = str(tmp_path / "test.csv")
        records = [
            {"txn_id": "T002", "timestamp": "2025-01-02", "type": "WITHDRAW", "amount": 200, "balance": 800, "description": "ATM", "category": "General"},
        ]
        export_transactions_to_csv("ACC001", records, filepath)
        with open(filepath) as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)
            assert row[3].startswith("-")

    def test_empty_records(self, tmp_path: Path) -> None:
        filepath = str(tmp_path / "empty.csv")
        result = export_transactions_to_csv("ACC001", [], filepath)
        with open(result) as f:
            lines = f.readlines()
            assert len(lines) == 1  # Only header

    def test_creates_directory(self, tmp_path: Path) -> None:
        filepath = str(tmp_path / "subdir" / "test.csv")
        result = export_transactions_to_csv("ACC001", [], filepath)
        assert os.path.exists(result)


class TestGenerateCsvFilename:
    """Tests for CSV filename generation."""

    def test_contains_acc_no(self) -> None:
        filename = generate_csv_filename("ACC123")
        assert "ACC123" in filename

    def test_ends_with_csv(self) -> None:
        filename = generate_csv_filename("ACC001")
        assert filename.endswith(".csv")

    def test_contains_statement_prefix(self) -> None:
        filename = generate_csv_filename("ACC001")
        assert "statement_" in filename
