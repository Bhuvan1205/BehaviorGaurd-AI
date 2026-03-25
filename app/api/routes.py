from fastapi import APIRouter
from app.schemas.event_schema import EventRequest, EventResponse
from app.services.feature_engine import compute_features
from app.services.inference import predict
import numpy as np
from app.services.risk_engine import aggregate_risk
from app.services.alert_service import generate_alert
from app.services.validation_service import validate_event, validate_user_history
from app.services.logging_service import log_event
from app.services.user_service import validate_user_id
from app.services.model_service import get_model_version


router = APIRouter()

@router.post("/event")
def process_event(request: EventRequest):

    event = request.event.dict()
    history = request.user_history.dict()

    try:
        validate_event(event)
        validate_user_history(history)
        event["user_id"] = validate_user_id(event["user_id"])

    except ValueError as e:
        return {"error": str(e)}

    # STEP 2: Features
    features = compute_features(event, history)
    features = [float(x) for x in features]

    # STEP 3: Model
    result = predict(features)
    score = float(result["anomaly_score"])

    # STEP 4: Aggregation
    past_events = []  # temporary
    aggregated_risk = aggregate_risk(score, past_events)

    # STEP 5: Alert
    alert = generate_alert(event["user_id"], aggregated_risk)

    #STEP 6:LOGGING
    log_event({
        "user_id": event["user_id"],
        "features": features,
        "anomaly_score": score,
        "aggregated_risk": aggregated_risk,
        "alert": alert
    })
    model_version = get_model_version()
    return {
        "anomaly_flag": result["anomaly_flag"],
        "anomaly_score": score,
        "aggregated_risk": aggregated_risk,
        "alert": alert,
        "model_version": model_version
    }