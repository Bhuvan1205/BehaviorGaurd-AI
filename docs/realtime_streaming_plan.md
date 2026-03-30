# Realtime Streaming Migration Plan

## Why the current flow is not realtime

Today the platform behaves like a simulator, not a streaming UEBA system:

- The frontend simulator sends only `logons` and `devices`.
- The frontend also fetches prior history and pushes `user_history` into `/event`.
- The backend depends on caller-supplied history instead of building behavioral context from stored events.
- The monitoring page polls `/history` every 5 seconds instead of subscribing to a live stream.

That means the browser is acting like a mini feature-engineering service, which is the wrong boundary for production.

## Target architecture

The system should move to an event-driven pipeline:

1. Enterprise source emits raw activity logs.
2. An ingest adapter normalizes each log into a common event schema.
3. The event is published to a stream or message queue.
4. A stream consumer reads each event and stores the raw event.
5. The backend builds user history from the database or fast cache.
6. Features are computed server-side from the current event plus recent history.
7. The trained model scores the event immediately.
8. Risk scores and alerts are persisted.
9. The UI receives updates through WebSocket or Server-Sent Events.

## Recommended event schema

Replace the current simulator-style payload with a normalized activity event:

```json
{
  "event_id": "uuid",
  "user_id": "USR-1023",
  "event_type": "login",
  "event_timestamp": "2026-03-29T09:02:11Z",
  "device_id": "PC-014",
  "ip_address": "10.10.4.21",
  "source_system": "windows-adapter",
  "status": "SUCCESS",
  "metadata": {
    "department": "finance",
    "host_name": "fin-lt-14"
  }
}
```

Minimum required fields for the first version:

- `event_id`
- `user_id`
- `event_type`
- `event_timestamp`
- `device_id`

## Backend changes

### 1. Split ingestion from inference

Add two clear backend responsibilities:

- `POST /ingest/events`
  Accepts normalized raw events from connectors or demo producers.
- `stream processor`
  Reads events, computes features, writes risk scores, and emits analyst updates.

For a simple local first version, `/ingest/events` can synchronously write the event and trigger processing. Later it can publish to Kafka or Redis Streams.

### 2. Stop accepting `user_history` from the client

The route in [app/api/routes.py](C:\Users\vinja\Desktop\BehaviorGaurd-AI\app\api\routes.py) currently trusts frontend-supplied history. That should be removed.

The backend should instead:

- fetch the user’s recent event windows from PostgreSQL
- aggregate recent logons, logoffs, and distinct devices
- build `past_logins`, `logon_counts`, and `unique_pcs_history`
- call `compute_features(...)`
- run the model

This makes the inference pipeline deterministic and production-safe.

### 3. Add a history builder service

Create a backend service such as:

- `app/services/history_service.py`

Responsibilities:

- fetch last `N` windows for a user
- compute current window aggregates
- return the exact structure expected by [app/services/feature_engine.py](C:\Users\vinja\Desktop\BehaviorGaurd-AI\app\services\feature_engine.py)

### 4. Add a stream abstraction

Recommended progression:

- Phase 1: PostgreSQL-backed ingest plus synchronous processing
- Phase 2: Redis Streams for lightweight realtime queues
- Phase 3: Kafka for production-scale multi-consumer streaming

For this project, Redis Streams is the best next step because it is much lighter to demo than Kafka.

### 5. Push updates to the UI

The current monitoring page at [frontend-v2/src/pages/MonitoringPage.jsx](C:\Users\vinja\Desktop\BehaviorGaurd-AI\frontend-v2\src\pages\MonitoringPage.jsx) is polling.

Replace or complement polling with:

- WebSocket endpoint such as `/ws/alerts`
- or SSE endpoint such as `/stream/alerts`

The backend should publish:

- new risk score
- anomaly decision
- alert open/close changes
- latest user event

## Frontend changes

### Remove manual history handling from simulator

The simulator page at [frontend-v2/src/pages/SimulatorPage.jsx](C:\Users\vinja\Desktop\BehaviorGaurd-AI\frontend-v2\src\pages\SimulatorPage.jsx) currently:

- loads recent history into browser state
- sends that history back to the backend

That should change to:

- send only the new event
- show the response from backend-computed inference

### Add a live event console

Useful demo UI blocks:

- event ticker showing incoming log lines
- current user risk card
- top active alerts
- live anomaly timeline
- connection status badge

## Demo strategy without a real enterprise feed

You do not need a real office network to demonstrate realtime behavior.

Use a `demo event producer` that streams realistic events continuously from seeded personas.

### Demo setup

1. Seed users, departments, devices, and baseline behavior.
2. Run a local producer that emits login events every few seconds.
3. Keep most traffic normal for the current time and weekday.
4. Inject occasional anomalies:
   - too many logins in a short period
   - login from an unseen device
   - login at unusual hours
   - multiple devices for one user in a short window
5. Feed those events into `/ingest/events` or the queue.
6. Show the monitoring dashboard updating live.

### Why this is valid

This is still a realtime demo because:

- events arrive continuously, not in a static batch
- the backend computes features from accumulated history
- the model scores each event immediately
- the UI updates as the stream advances

The only synthetic piece is the source of the events, not the streaming architecture.

## Practical implementation phases

### Phase 1: Fix the current architecture

- Remove `user_history` from public event requests.
- Build user history in the backend from stored events.
- Keep using PostgreSQL and the current model.
- Keep frontend polling temporarily.

Outcome:
The system becomes event-driven on the backend even before full streaming UI support.

### Phase 2: Add realtime delivery

- Add WebSocket or SSE updates from the backend.
- Update monitoring UI to subscribe instead of poll.
- Show new risk windows instantly.

Outcome:
The analyst experience becomes visibly realtime.

### Phase 3: Add a real stream broker

- Introduce Redis Streams or Kafka.
- Add producer and consumer services.
- Decouple ingestion from model scoring.

Outcome:
The architecture becomes production-like and scalable.

### Phase 4: Add source connectors

Possible adapters:

- Windows Event Logs
- Active Directory / LDAP auth events
- VPN logs
- EDR logs
- Linux auth logs
- SIEM forwarders

Outcome:
The demo pipeline can later connect to genuine live systems.

## Suggested first implementation tasks in this repo

1. Refactor [app/api/routes.py](C:\Users\vinja\Desktop\BehaviorGaurd-AI\app\api\routes.py) so `/event` no longer accepts `user_history`.
2. Add `history_service.py` to derive recent behavior from `events.login_events`.
3. Convert the simulator page to send only one event payload.
4. Add a simple `/stream/alerts` or WebSocket endpoint.
5. Add a `demo_stream_producer.py` script that continuously emits realistic events.

## Positioning for your presentation

Say it this way:

> Our original objective was live anomaly detection from continuously arriving employee activity, not manual simulation. The current build proves the ML scoring and dashboard flow, but the next milestone is replacing browser-driven history injection with server-side realtime event ingestion and stream processing. For the demo, we will use a synthetic live event producer that behaves like an office starting its workday, so the system can still demonstrate true streaming inference without needing access to a real company network.
