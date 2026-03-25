from app.services.feature_engine import compute_features
from app.services.inference import predict

event = {
    "user_id": "U1",
    "timestamp": "2026-03-22T10:00:00",
    "device_id": "D1",
    "event_type": "login"
}

user_history = {
    "past_logins": [
        "2026-03-22T08:30:00",
        "2026-03-22T09:15:00",
        "2026-03-22T09:45:00"
    ],
    "logon_counts": [3, 3, 4, 3, 3, 4],
    "unique_pcs_history": [1, 1, 1, 1, 2, 1],

    "current_logon_count": 3,
    "current_logoff_count": 2,
    "current_unique_pcs": 1
}

features = compute_features(event, user_history)
result = predict(features)

print("FEATURES:", features)
print("RESULT:", result)