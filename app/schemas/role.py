from pydantic import BaseModel
from typing import Dict

class RoleCreate(BaseModel):
    role: str

class PermissionUpdate(BaseModel):
    permissions: Dict[str, Dict[str, bool]]  # e.g., { "event": { "GET": True, "POST": False } }
