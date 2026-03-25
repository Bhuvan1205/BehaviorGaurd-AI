def validate_user_id(user_id: str) -> str:
    """
    Validate and sanitize user_id
    """

    if not user_id:
        raise ValueError("user_id is required")

    # strip spaces
    user_id = user_id.strip()

    # basic format check
    if len(user_id) < 2:
        raise ValueError("user_id too short")

    # optional: enforce alphanumeric (recommended)
    if not user_id.replace("_", "").isalnum():
        raise ValueError("user_id must be alphanumeric")

    return user_id