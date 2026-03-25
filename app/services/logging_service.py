import json
from datetime import datetime


def log_event(data: dict):
    """
    Logs structured system data
    """

    log = {
        "timestamp": datetime.now().isoformat(),
        "data": data
    }

    print(json.dumps(log, indent=2))