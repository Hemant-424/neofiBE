from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict
from datetime import datetime


class Collaborator(BaseModel):
    email: EmailStr
    permissions: Dict[str, Dict[str, bool]]  # e.g., {"events": {"GET": True, "POST": False}}

    
class EventBase(BaseModel):
    title: str
    description: Optional[str] = ""
    start_time: datetime
    end_time: datetime
    location: Optional[str] = ""
    is_recurring: Optional[bool] = False
    reccurrence_pattern: Optional[str] = ""  # e.g., "daily", "weekly", "monthly"
    collaborators: Optional[List[Collaborator]] = []

class EventCreate(EventBase):
    pass

class EventUpdate(EventBase):
    pass

class EventInDB(EventBase):
    id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


