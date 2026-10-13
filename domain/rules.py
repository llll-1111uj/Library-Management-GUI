from datetime import datetime as Datetime, timedelta

MAX_BORROW = 3
MAX_RESERVE = 3
MAX_EXTENSION_DAYS = 7
DEFAULT_LOAN_DAYS = 7
MAX_LOAN_DAYS = 21


def find_delay(allowed_date, returned_date) -> int:
    if not allowed_date or not returned_date:
        return 0
    delta = returned_date - allowed_date
    if delta.days <= 0:
        return 0
    return delta.days


def find_bill(delay: int) -> int:
    if delay <= 0:
        return 0
    if delay <= 7:
        return 2 * delay
    return (2 * 7) + (5 * (delay - 7))


def clamp_loan_days(days) -> int:
    days = days if days is not None else DEFAULT_LOAN_DAYS
    if days > MAX_LOAN_DAYS:
        return MAX_LOAN_DAYS
    if days < 1:
        return DEFAULT_LOAN_DAYS
    return days


def can_borrow(active_count) -> bool:
    return active_count < MAX_BORROW


def can_reserve(active_count) -> bool:
    return active_count < MAX_RESERVE


def add_time(time: Datetime, days: int) -> Datetime:
    return time + timedelta(days=days)
