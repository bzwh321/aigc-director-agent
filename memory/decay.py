from math import exp


def decay_score(days_since_last_used: int, half_life_days: int = 30) -> float:
    return exp(-0.693 * max(0, days_since_last_used) / half_life_days)
