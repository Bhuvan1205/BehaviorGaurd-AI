def get_risk_level(risk: float) -> str:
    if risk < 0.05:
        return "LOW"
    elif risk < 0.10:
        return "MEDIUM"
    else:
        return "HIGH"


def should_trigger_alert(risk: float) -> bool:
    return risk >= 0.10


def generate_alert(user_id: str, risk: float):
    level = get_risk_level(risk)

    return {
        "user_id": user_id,
        "risk": risk,
        "level": level,
        "alert": should_trigger_alert(risk)
    }