import urllib.request, urllib.error
import urllib.parse
req = urllib.request.Request("http://localhost:8001/history?user_id=1")
try:
    r = urllib.request.urlopen(req)
    print("HISTORY RESPONSE:")
    print(r.read())
except urllib.error.HTTPError as e:
    print("HISTORY 500 ERROR:")
    print(e.read().decode())

req_event = urllib.request.Request("http://localhost:8001/event", data=b'{"user_id":"1","event":{"timestamp":"2023-01-01T00:00:00Z","logon_count":1,"device_count":1}}', headers={"Content-Type": "application/json"}, method="POST")
try:
    r = urllib.request.urlopen(req_event)
    print("EVENT RESPONSE:")
    print(r.read())
except urllib.error.HTTPError as e:
    print("EVENT 500 ERROR:")
    print(e.read().decode())
