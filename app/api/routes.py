from fastapi import APIRouter
from app.schemas.event_schema import EventRequest, EventResponse
from app.services.feature_engine import compute_features
from app.services.inference import predict
import numpy as np

router = APIRouter()

@router.post("/event", response_model=EventResponse)
def process_event(request: EventRequest):
    # Extract data
    event = request.event
    user_history_raw = request.user_history

    # Convert Pydantic model to dict
    event_dict = event.dict()
    history_raw_dict = user_history_raw.dict()

    # Step 1: Feature computation
    features = compute_features(event_dict, history_raw_dict)
    print("FEATURES:", features)

    # Step 2: Convert numpy types → float (important for JSON)
    features = [float(x) for x in features]

    # Step 3: Model inference
    result = predict(features)

    return EventResponse(
        anomaly_flag=result["anomaly_flag"],
        anomaly_score=float(result["anomaly_score"])
    )
