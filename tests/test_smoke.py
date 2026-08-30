"""
Smoke tests – verify that all project modules import correctly after changes.
"""

from unionbank.entrypoints.cli.account import Account
from unionbank.entrypoints.cli.admin import Admin
from unionbank.entrypoints.cli.bank import Bank
from unionbank.entrypoints.cli.main import main_menu
from unionbank.utils import (
    hash_password,
    validate_email,
)
from unionbank.utils.logger import logger


class TestSmoke:
    """Verify that all project modules can be imported without errors."""

    def test_import_utils(self) -> None:
        assert hasattr(validate_email, "__call__")
        assert hasattr(hash_password, "__call__")

    def test_import_logger(self) -> None:
        assert logger is not None

    def test_import_account(self) -> None:
        assert Account is not None

    def test_import_bank(self) -> None:
        assert Bank is not None

    def test_import_admin(self) -> None:
        assert Admin is not None

    def test_import_main(self) -> None:
        assert main_menu is not None
