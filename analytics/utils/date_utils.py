from datetime import datetime, timedelta
from django.utils import timezone
from typing import Tuple

def parse_date_range(start_date=None, end_date=None, period=None) -> Tuple[datetime, datetime]:
    """
    Parse and return start and end dates based on input parameters.
    
    Args:
        start_date: ISO format date string (YYYY-MM-DD)
        end_date: ISO format date string (YYYY-MM-DD)
        period: Predefined period ('today', 'week', 'month', 'quarter', 'year')
    
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    now = timezone.now()
    
    if period:
        if period == 'today':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == 'week':
            start = now - timedelta(days=7)
            end = now
        elif period == 'month':
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == 'quarter':
            start = now - timedelta(days=90)
            end = now
        elif period == 'year':
            start = now - timedelta(days=365)
            end = now
        else:
            # Default to last 30 days
            start = now - timedelta(days=30)
            end = now
    elif start_date and end_date:
        try:
            start = timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
            end = timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d').replace(
                hour=23, minute=59, second=59
            ))
        except ValueError:
            # Default to last 30 days on error
            start = now - timedelta(days=30)
            end = now
    else:
        # Default to last 30 days
        start = now - timedelta(days=30)
        end = now
    
    return start, end


def get_previous_period(start_date: datetime, end_date: datetime) -> Tuple[datetime, datetime]:
    """
    Get the previous period of the same duration for comparison.
    """
    duration = end_date - start_date
    prev_end = start_date
    prev_start = prev_end - duration
    return prev_start, prev_end


def calculate_growth_percentage(current: float, previous: float) -> str:
    """
    Calculate growth percentage between two values.
    """
    if previous == 0:
        return "+100%" if current > 0 else "0%"
    
    growth = ((current - previous) / previous) * 100
    sign = "+" if growth >= 0 else ""
    return f"{sign}{growth:.1f}%"
