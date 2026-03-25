import math
from datetime import datetime


LAMBDA = 0.5  # decay factor


def compute_weight(delta_hours: float) -> float:
    return math.exp(-LAMBDA * delta_hours)


def aggregate_risk(current_score: float, past_events: list):
    """
    past_events: list of dicts
    [
        {"score": -0.1, "timestamp": "2026-03-22T09:00:00"},
        ...
    ]
    """

    now = datetime.now()

    weighted_sum = 0.0
    total_weight = 0.0

    # include current event
    weighted_sum += current_score * 1.0
    total_weight += 1.0

    for event in past_events:
        try:
            past_time = datetime.fromisoformat(event["timestamp"])
            delta = abs((now - past_time).total_seconds()) / 3600.0
            weight = compute_weight(delta)

            weighted_sum += event["score"] * weight
            total_weight += weight

        except:
            continue

    if total_weight == 0:
        return -current_score  # fallback

    aggregated = weighted_sum / total_weight

    # convert to positive risk
    return -aggregated