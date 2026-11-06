"""Return-window rules for the synthetic NovaMart order data."""
from datetime import date


def return_eligibility(tier: str, order_date: str, today: date) -> bool:
    window = {'standard': 30, 'premium': 60}.get(tier.casefold())
    if window is None:
        return False
    try:
        age = (today - date.fromisoformat(order_date)).days
    except (ValueError, TypeError):
        return False
    return 0 <= age <= window
