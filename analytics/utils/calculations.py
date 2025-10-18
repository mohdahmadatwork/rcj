from decimal import Decimal
from typing import List, Dict, Any

def calculate_percentage(part: int, total: int) -> float:
    """Calculate percentage with error handling."""
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)


def safe_avg(values: List[float]) -> float:
    """Calculate average safely."""
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def format_currency(amount: Decimal) -> float:
    """Format currency to 2 decimal places."""
    return float(round(amount, 2))
