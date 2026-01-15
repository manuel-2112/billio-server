from enum import Enum


class TableStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    PAYING = "paying"
