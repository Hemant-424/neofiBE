from fastapi import Depends, HTTPException, status
from app.api.auth import get_current_user
from app.database import get_db

class PermissionChecker:
    def __init__(self, resource: str, method: str):
        self.resource = resource
        self.method = method

    async def __call__(self, user=Depends(get_current_user)):
        db = get_db()
        if not user.get("role_id"):
            raise HTTPException(status_code=403, detail="No role assigned")

        role = user["role_id"]
        permissions = await db["permissions"].find_one({"role": role})
        if not permissions:
            raise HTTPException(status_code=403, detail="No permissions found")

        resource_perms = permissions["permissions"].get(self.resource, {})
        if not resource_perms.get(self.method, False):
            raise HTTPException(status_code=403, detail="Permission denied")



async def ensure_collaborator(event_id: str, user_email: str, db):
    event = await db["events"].find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event["created_by"] != user_email and user_email not in event.get("collaborators", []):
        raise HTTPException(status_code=403, detail="You are not a collaborator")
