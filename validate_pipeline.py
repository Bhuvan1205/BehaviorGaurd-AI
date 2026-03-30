import urllib.request, json

payload = {
    "user_id": "11111111-1111-1111-1111-111111111111",
    "event": {
        "timestamp": "2026-03-25T10:00:00",
        "logons": 5,
        "devices": 2
    },
    "user_history": [
        {"timestamp": "2026-03-24T09:00:00", "logons": 3, "devices": 1},
        {"timestamp": "2026-03-23T08:30:00", "logons": 4, "devices": 1}
    ]
}

req = urllib.request.Request(
    'http://localhost:8000/event', 
    data=json.dumps(payload).encode('utf-8'), 
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        print("SUCCESS:", response.read().decode())
except Exception as e:
    print("ERROR:", e.read().decode())

req_history = urllib.request.Request('http://localhost:8000/history?user_id=11111111-1111-1111-1111-111111111111')
try:
    with urllib.request.urlopen(req_history) as history_resp:
        print("\nHISTORY PULL SUCCESS:", history_resp.read().decode())
except Exception as e:
    print("\nHISTORY PULL ERROR:", getattr(e, 'read', lambda: str(e))())
