from pydantic import BaseModel
from typing import List


class Event(BaseModel):
    user_id: str
    timestamp: str
    device_id: str
    event_type: str  # "login" or "logout"


from typing import List, Optional
from pydantic import BaseModel


class UserHistory(BaseModel):
    past_logins: List[str] = []
    logon_counts: List[int] = []
    unique_pcs_history: List[int] = []

    current_logon_count: Optional[int] = 1
    current_logoff_count: Optional[int] = 0
    current_unique_pcs: Optional[int] = 1


class EventRequest(BaseModel):
    event: Event
    user_history: UserHistory


class EventResponse(BaseModel):
    anomaly_flag: int
    anomaly_score: float
