# Utils: Date parsing for natural language dates

import re
from datetime import datetime, timedelta

from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta


def parse_relative_date(date_str: str | None) -> datetime | None:
    """
    Parse a relative or absolute date string.
    Handles: "tomorrow", "next week", "in 3 days", "two weeks later", "2024-01-15", etc.
    """
    if not date_str:
        return None

    date_str = date_str.lower().strip()
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Word to number mapping
    word_numbers = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "a": 1,
        "an": 1,
    }

    # Relative terms
    if date_str == "today":
        return today

    if date_str == "tomorrow":
        return today + timedelta(days=1)

    if date_str in ("next week", "a week", "one week"):
        return today + timedelta(weeks=1)

    if date_str in ("next month", "a month", "one month"):
        return today + relativedelta(months=1)
    if date_str in ("this month", "this_month"):
        return today.replace(day=1)

    # "in X days/weeks" or "X days/weeks later/from now"
    patterns = [
        r"in\s+(\w+)\s+(day|days|week|weeks)",
        r"(\w+)\s+(day|days|week|weeks)\s+(later|from now)",
        r"(\w+)\s+(day|days|week|weeks)",
    ]

    for pattern in patterns:
        match = re.match(pattern, date_str)
        if match:
            num_str = match.group(1)
            unit = match.group(2)

            # Convert word to number
            if num_str in word_numbers:
                num = word_numbers[num_str]
            elif num_str.isdigit():
                num = int(num_str)
            else:
                continue

            if "week" in unit:
                return today + timedelta(weeks=num)
            else:
                return today + timedelta(days=num)

    # Day names
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, day in enumerate(days):
        if day in date_str:
            current_day = today.weekday()
            days_ahead = i - current_day
            if days_ahead <= 0:
                days_ahead += 7
            if "next" in date_str:
                days_ahead += 7
            return today + timedelta(days=days_ahead)

    # Try parsing as absolute date
    try:
        parsed = date_parser.parse(date_str, fuzzy=True)
        return parsed.replace(hour=0, minute=0, second=0, microsecond=0)
    except (ValueError, TypeError):
        pass

    return None


def format_relative_date(dt: datetime | None) -> str:
    """
    Format a datetime as a human-readable relative string.
    """
    if not dt:
        return "No date"

    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    target = dt.replace(hour=0, minute=0, second=0, microsecond=0)

    diff = (target - today).days

    if diff == 0:
        return "Today"
    elif diff == 1:
        return "Tomorrow"
    elif diff == -1:
        return "Yesterday"
    elif 0 < diff <= 7:
        return target.strftime("%A")  # Day name
    elif diff < 0:
        return f"{abs(diff)} days ago"
    else:
        return target.strftime("%b %d, %Y")
