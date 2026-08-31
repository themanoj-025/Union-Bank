"""
Seed data constants and helper functions.

Extracted from seed_data.py for maintainability. Contains all the name
lists, address data, transaction types, and generation helpers.
"""

from __future__ import annotations

import random
import string
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Names, addresses, transaction types — ~5,000 accounts
# ---------------------------------------------------------------------------

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Sai",
    "Rohan", "Vihaan", "Krishna", "Ayaan", "Reyansh",
    "Ananya", "Diya", "Isha", "Priya", "Neha",
    "Anjali", "Pooja", "Kavya", "Meera", "Riya",
    "Arnav", "Dhruv", "Kabir", "Aarush", "Veer",
    "Myra", "Saanvi", "Aadhya", "Aisha", "Nisha",
    "Rahul", "Amit", "Suresh", "Rajesh", "Manoj",
    "Deepak", "Sanjay", "Vikram", "Ravi", "Sunil",
    "Sunita", "Geeta", "Suman", "Rekha", "Usha",
    "Ganesh", "Mohan", "Shyam", "Tapan", "Uday",
    "Lata", "Ashok", "Ramesh", "Mahesh", "Dinesh",
    "Kamla", "Savita", "Aarti", "Kiran", "Leela",
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar",
    "Patel", "Reddy", "Nair", "Iyer", "Mishra",
    "Joshi", "Desai", "Kapoor", "Chopra", "Mehta",
    "Rao", "Das", "Banerjee", "Mukherjee", "Chatterjee",
    "Tiwari", "Saxena", "Pandey", "Bhatt", "Yadav",
    "Agarwal", "Sinha", "Chauhan", "Malhotra", "Khanna",
]

ADDRESSES = [
    "MG Road, Bangalore", "Park Street, Kolkata", "Anna Salai, Chennai",
    "Connaught Place, Delhi", "Juhu, Mumbai", "Banjara Hills, Hyderabad",
    "Koregaon Park, Pune", "Civil Lines, Jaipur", "Hazratganj, Lucknow",
    "Sector 18, Noida", "Salt Lake, Kolkata", "Andheri West, Mumbai",
    "Koramangala, Bangalore", "Whitefield, Bangalore", "HSR Layout, Bangalore",
    "Powai, Mumbai", "Bandra West, Mumbai", "Thane, Mumbai",
    "Gurgaon Sector 21", "Noida Sector 62", "Dwarka, Delhi",
    "Rohini, Delhi", "Lajpat Nagar, Delhi", "Karol Bagh, Delhi",
    "Aundh, Pune", "Viman Nagar, Pune", "Hinjewadi, Pune",
    "T Nagar, Chennai", "Adyar, Chennai", "Velachery, Chennai",
    "Jubilee Hills, Hyderabad", "Madhapur, Hyderabad", "Gachibowli, Hyderabad",
    "Vaishali, Ghaziabad", "Indirapuram, Ghaziabad", "Crossings Republik, Ghaziabad",
    "Rajouri Garden, Delhi", "Paschim Vihar, Delhi", "Meerut Road, Ghaziabad",
    "HSR Layout 2nd Sector", "BTM Layout 2nd Stage", "JP Nagar 7th Phase",
    "Electronic City Phase 1", "Sarjapur Road", "Marathahalli",
    "Deccan Gymkhana, Pune", "Sadashiv Peth, Pune", "Kothrud, Pune",
    "Tolichowki, Hyderabad", "LB Nagar, Hyderabad", "Uppal, Hyderabad",
    "Ramapuram, Chennai", "Porur, Chennai", "Sholinganallur, Chennai",
    "Chembur, Mumbai", "Goregaon East, Mumbai", "Malad West, Mumbai",
    "Andheri Kurla Road", "Vikhroli, Mumbai", "Mulund West, Mumbai",
    "Borivali West, Mumbai", "Kandivali East, Mumbai", "Dahisar, Mumbai",
]

ACCOUNT_TYPES = ["savings", "current", "salary", "fixed_deposit"]
CURRENCIES = ["INR"]

# Realistic Indian bank branch codes
BRANCH_CODES = [
    "BLR001", "BLR002", "BLR003", "DEL001", "DEL002", "DEL003",
    "MUM001", "MUM002", "MUM003", "CHN001", "CHN002", "HYD001",
    "HYD002", "PUN001", "PUN002", "KOL001", "KOL002", "JAI001",
    "LKO001", "NOD001", "NOD002", "GZB001", "GZB002",
]

TxnCategory = str  # type alias

TRANSACTION_DESCRIPTIONS: list[TxnCategory] = [
    "Salary credit",
    "ATM withdrawal",
    "UPI payment",
    "NEFT transfer",
    "IMPS transfer",
    "Card payment",
    "Electricity bill",
    "Mobile recharge",
    "Rent payment",
    "Insurance premium",
    "Mutual fund SIP",
    "Fixed deposit interest",
    "Grocery store",
    "Restaurant",
    "Fuel",
    "Medical expense",
    "Education fee",
    "EMI payment",
    "Loan disbursement",
    "Loan repayment",
    "Credit card payment",
    "Shopping",
    "Travel",
    "Entertainment",
    "Subscription",
    "Cash deposit",
    "Cheque clearance",
    "Dividend credit",
    "Interest earned",
    "Tax refund",
    "Government subsidy",
    "Pension credit",
    "Commission received",
    "Freelance payment",
    "Gift received",
    "Family remittance",
    "Transfer received",
]


# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------

def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


def generate_phone() -> str:
    return str(random.randint(6, 9)) + "".join([str(random.randint(0, 9)) for _ in range(9)])


def generate_email(name: str) -> str:
    name_clean = name.lower().replace(" ", ".")
    domains = [
        "gmail.com",
        "yahoo.com",
        "outlook.com",
        "rediffmail.com",
        "hotmail.com",
        "email.com",
    ]
    domain = random.choice(domains)
    suffixes = ["", str(random.randint(1, 999)), str(random.randint(1990, 2005))]
    suffix = random.choice(suffixes)
    if suffix:
        return f"{name_clean}{suffix}@{domain}"
    return f"{name_clean}@{domain}"


_TXN_CHARS = string.ascii_uppercase + string.digits


def generate_txn_id() -> str:
    return "TXN-" + "".join(random.choices(_TXN_CHARS, k=8))
