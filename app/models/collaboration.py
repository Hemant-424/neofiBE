from pydantic import BaseModel
from typing import List, Dict

class ShareUser(BaseModel):
    user_id: str
    role: str  # e.g., 'Viewer', 'Editor'

class ShareEventRequest(BaseModel):
    users: List[ShareUser]

class PermissionUpdatePayload(BaseModel):
    permissions: Dict[str, bool]