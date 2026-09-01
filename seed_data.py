"""
seed_data.py  –  Generate ~5,000 sample accounts with transaction history.

Writes directly to SQLite via the repository layer (no JSON files).

Usage:
    python seed_data.py         # (takes ~10-15 seconds due to bcrypt)
    python seed_data.py --slow  # (hashes each password individually, ~15 seconds)
    python seed_data.py --fast  # (pre-computed hash, ~2 seconds — default)
"""

import os
import random
import secrets
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal

# Set testing-friendly env vars so Config doesn't require real secrets
os.environ.setdefault("UNION_BANK_TESTING", "1")
os.environ.setdefault("JWT_SECRET", secrets.token_hex(32))
os.environ.setdefault("FLASK_SECRET_KEY", secrets.token_hex(24))

from unionbank.config import settings
from unionbank.utils.hashing import hash_password

from seed_helpers import (
    ADDRESSES,
    BRANCH_CODES,
    FIRST_NAMES,
    LAST_NAMES,
    TRANSACTION_DESCRIPTIONS,
    TRANSACTION_TYPES,
    TXN_WEIGHTS,
    TYPE_CATEGORY_MAP,
    DEPOSIT_DESCRIPTIONS,
    TRANSFER_IN_DESCRIPTIONS,
    TRANSFER_OUT_DESCRIPTIONS,
    WITHDRAW_DESCRIPTIONS,
    random_date,
    generate_email,
    generate_phone,
    generate_txn_id,
)

NUM_ACCOUNTS = 5000
MIN_TXNS_PER_ACCOUNT = 8
MAX_TXNS_PER_ACCOUNT = 20
DEFAULT_PASSWORD = os.environ.get("SEED_PASSWORD", "Password@123")
START_DATE = datetime(2022, 1, 1)
END_DATE = datetime(2024, 12, 31)
GENDERS = ["Male", "Female"]

# Split names by gender for realistic generation
FIRST_NAMES_MALE = [n for n in FIRST_NAMES if n not in (
    "Ananya", "Diya", "Isha", "Priya", "Neha", "Anjali", "Pooja",
    "Kavya", "Meera", "Riya", "Myra", "Saanvi", "Aadhya", "Aisha",
    "Nisha", "Sunita", "Geeta", "Suman", "Rekha", "Usha", "Kamla",
    "Savita", "Aarti", "Kiran", "Leela", "Lata",
)]
FIRST_NAMES_FEMALE = [n for n in FIRST_NAMES if n not in FIRST_NAMES_MALE]


def seed_data(fast_mode: bool = True) -> None:
    """
    Generate sample data and write directly to SQLite via the repository layer.

    Uses SQLAlchemy metadata drop_all/create_all to reset the database —
    portable across all OSes and avoids Windows WAL-file-locking issues.

    IMPORTANT: Uses raw session.add() for AccountModel objects and updates
    them in-place to avoid the `autoflush=False` identity-map issue where
    repo.update() would create a duplicate INSERT for pending objects.

    Args:
        fast_mode: If True, use a single pre-computed bcrypt hash for all accounts
                   (much faster, ~2 seconds vs ~15 seconds for 5000 accounts).
    """
    from unionbank.domain.entities import Account, Transaction, TransactionType
    from unionbank.infrastructure.database import (
        ModelBase,
        close_session,
        get_engine,
        get_session,
        reset_engine,
    )
    from unionbank.infrastructure.mappers import map_account_to_model
    from unionbank.infrastructure.persistence import AccountModel
    from unionbank.infrastructure.repositories import (
        SqlAlchemyTransactionRepository,
    )

    print(f"\n  {'=' * 50}")
    print(f"  Seeding {NUM_ACCOUNTS:,} sample accounts...")
    print(f"  {'=' * 50}\n")

    # Reset engine and drop + recreate all tables (portable, avoids Windows file-locking)
    reset_engine()
    engine = get_engine()
    ModelBase.metadata.drop_all(bind=engine)
    ModelBase.metadata.create_all(bind=engine)
    print("  Fresh database tables created via SQLAlchemy metadata.\n")

    # Pre-compute password hash
    if fast_mode:
        print("  Fast mode: using single hash for all accounts")
        hashed_password = hash_password(DEFAULT_PASSWORD)
    else:
        print(f"  Hashing password '{DEFAULT_PASSWORD}' for each account...")
        hashed_password = None

    session = get_session()
    txn_repo = SqlAlchemyTransactionRepository(session)

    used_account_numbers: set[str] = set()
    start_time = time.time()

    for i in range(NUM_ACCOUNTS):
        gender = random.choice(GENDERS)
        first_name = random.choice(FIRST_NAMES_MALE if gender == "Male" else FIRST_NAMES_FEMALE)
        last_name = random.choice(LAST_NAMES)
        full_name = f"{first_name} {last_name}"

        age = random.randint(18, 75)
        mobile = generate_phone()
        email = generate_email(full_name)
        initial_balance = round(random.uniform(500, 500000), 2)
        created_date = random_date(START_DATE, END_DATE - timedelta(days=30))
        pwd_hash = hashed_password if fast_mode else hash_password(DEFAULT_PASSWORD)

        # Generate unique account number using a Python set
        acc_no = str(secrets.randbelow(9_000_000_000) + 1_000_000_000)
        while acc_no in used_account_numbers:
            acc_no = str(secrets.randbelow(9_000_000_000) + 1_000_000_000)
        used_account_numbers.add(acc_no)

        account = Account(
            account_number=acc_no,
            name=full_name,
            age=age,
            gender=gender,
            mobile=mobile,
            email=email,
            password=pwd_hash,
            balance=Decimal(str(initial_balance)),
            is_active=True,
            is_frozen=False,
            created_at=created_date,
            updated_at=created_date,
        )

        data = map_account_to_model(account)
        account_model = AccountModel(**data)
        session.add(account_model)

        # Generate transactions
        num_txns = random.randint(MIN_TXNS_PER_ACCOUNT, MAX_TXNS_PER_ACCOUNT)
        running_balance = Decimal(str(initial_balance))
        txn_dates = sorted([random_date(created_date, END_DATE) for _ in range(num_txns)])

        for txn_date in txn_dates:
            txn_type = random.choices(TRANSACTION_TYPES, weights=TXN_WEIGHTS, k=1)[0]
            category = random.choice(TYPE_CATEGORY_MAP[txn_type])

            if txn_type == "DEPOSIT":
                amount = Decimal(str(round(random.uniform(500, 100000), 2)))
                running_balance += amount
                description = random.choice(DEPOSIT_DESCRIPTIONS)
            elif txn_type == "WITHDRAW":
                max_wd = max(Decimal("100"), running_balance * Decimal("0.3"))
                amount = min(Decimal(str(round(random.uniform(50, 50000), 2))), max_wd)
                running_balance -= amount
                description = random.choice(WITHDRAW_DESCRIPTIONS)
            elif txn_type == "TRANSFER_OUT":
                max_tr = max(Decimal("100"), running_balance * Decimal("0.5"))
                amount = min(Decimal(str(round(random.uniform(100, 25000), 2))), max_tr)
                running_balance -= amount
                description = random.choice(TRANSFER_OUT_DESCRIPTIONS)
            else:
                amount = Decimal(str(round(random.uniform(500, 50000), 2)))
                running_balance += amount
                description = random.choice(TRANSFER_IN_DESCRIPTIONS)

            if running_balance < 0:
                running_balance = Decimal("0")

            txn = Transaction(
                txn_id=generate_txn_id(),
                account_number=acc_no,
                type=TransactionType(txn_type),
                amount=amount,
                balance=running_balance,
                description=description,
                category=category,
                timestamp=txn_date,
            )
            txn_repo.create(txn)

        account_model.balance = running_balance

        if (i + 1) % 500 == 0 or i == 0:
            elapsed = time.time() - start_time
            pct = (i + 1) / NUM_ACCOUNTS * 100
            print(
                f"  [{i + 1:>5,}/{NUM_ACCOUNTS:,}] accounts generated ({pct:.0f}%) - {elapsed:.1f}s"
            )

    session.commit()

    total_txns = txn_repo.count()
    total_accounts = session.query(AccountModel).count()
    from sqlalchemy import func

    total_balance = float(
        session.query(func.sum(AccountModel.balance))
        .filter(AccountModel.is_active.is_(True), AccountModel.is_frozen.is_(False))
        .scalar()
        or Decimal("0.00")
    )
    elapsed = time.time() - start_time

    close_session()

    print(f"\n  {'=' * 50}")
    print("  Seeding Complete!")
    print(f"  {'=' * 50}")
    print(f"     Accounts      : {total_accounts:>8,}")
    print(f"     Transactions  : {total_txns:>8,}")
    if total_accounts:
        print(f"     Avg txns/acct : {total_txns / total_accounts:>8.1f}")
    print(f"     Total balance : Rs.{total_balance:>12,.2f}")
    print(f"     Time taken    : {elapsed:>8.1f}s")
    print(f"  {'=' * 50}\n")


if __name__ == "__main__":
    fast_mode = "--slow" not in sys.argv
    seed_data(fast_mode=fast_mode)
