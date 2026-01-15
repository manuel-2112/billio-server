from enum import Enum


class AccountStatus(str, Enum):
    OPEN = "open"
    PAID = "paid"
    CANCELLED = "cancelled"
