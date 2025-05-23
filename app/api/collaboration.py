from fastapi import APIRouter, HTTPException, Depends, Query, Body
from bson import ObjectId
from datetime import datetime
from typing import List, Optional
from app.api.auth import get_current_user
from app.database import get_db
from app.utils.diff import diff_versions
from app.services.collab import CollaborationManager
from app.core.permissions import ensure_collaborator
from fastapi import WebSocket, WebSocketDisconnect
from app.models.collaboration import ShareEventRequest, ShareUser, PermissionUpdatePayload
from app.core.permissions import PermissionChecker

router = APIRouter()


@router.post("/events/{event_id}/share")
async def share_event(
    event_id: str,
    payload: ShareEventRequest,
    auth= Depends(PermissionChecker("events", "POST")),
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    event = await db["events"].find_one({"_id": ObjectId(event_id)})
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event["created_by"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the creator can share this event")

    collaborators = event.get("collaborators", [])
    new_collaborators = []

    for user in payload.users:
        if any(c.get("user_id") == user.user_id for c in collaborators):
            continue  # Already shared, skip

        new_collaborators.append({
            "user_id": user.user_id,
            "role": user.role
        })

    if not new_collaborators:
        raise HTTPException(status_code=400, detail="No new users to share with")

    await db["events"].update_one(
        {"_id": ObjectId(event_id)},
        {"$push": {"collaborators": {"$each": new_collaborators}}}
    )

    updated_event = await db["events"].find_one({"_id": ObjectId(event_id)})
    return {
        "message": "Event shared successfully",
        "collaborators": updated_event.get("collaborators", [])
    }




@router.get("/events/{event_id}/permissions")
async def get_permissions(
    event_id: str,
    auth=Depends(PermissionChecker("events", "GET")),
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    event = await db["events"].find_one(
        {"_id": ObjectId(event_id)},
        {"collaborators": 1, "created_by": 1}
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event["created_by"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the creator can view permissions")

    # Get all distinct roles from collaborators
    roles = list(set(collab["role"] for collab in event.get("collaborators", [])))
    # print(roles)
    # Fetch permissions for all roles
    role_perms_map = {
        doc["role"]: doc["permissions"]
        async for doc in db["permissions"].find({"role": {"$in": roles}})
    }
    # print(role_perms_map)
    # Build enriched collaborator list
    enriched_collaborators = []
    for collab in event.get("collaborators", []):
        enriched_collaborators.append({
            "user_id": collab["user_id"],
            "role": collab["role"],
            "permissions": role_perms_map.get(collab["role"], {})
        })

    return {
        "event_id": event_id,
        "owner": event["created_by"],
        "collaborators": enriched_collaborators
    }



@router.put("/events/{event_id}/permissions/{user_id}")
async def update_event_collaborator_role(
    event_id: str,
    user_id: str,
    role_update: dict = Body(..., example={"role": "Editor"}),  # expects {"role": "Editor"}
    current_user: dict = Depends(get_current_user),
    auth=Depends(PermissionChecker("events", "PUT"))
):
    db = get_db()

    event = await db["events"].find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event["created_by"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the creator can update roles")

    new_role = role_update.get("role")
    if not new_role:
        raise HTTPException(status_code=400, detail="Missing 'role' in request body")

    # Check if role exists in permissions collection
    permissions_doc = await db["permissions"].find_one({"role": new_role})
    if not permissions_doc:
        raise HTTPException(status_code=404, detail=f"Role '{new_role}' not found in permissions")
    
    # Get old role of collaborator
    old_role = None
    for collab in event.get("collaborators", []):
        if collab.get("user_id") == user_id:
            old_role = collab.get("role")
            break

    if old_role is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found in collaborators")

    if old_role == new_role:
        raise HTTPException(status_code=400, detail="New role is same as current role")
    
    # Update the role in collaborators array
    result = await db["events"].update_one(
        {"_id": ObjectId(event_id), "collaborators.user_id": user_id},
        {"$set": {"collaborators.$.role": new_role, "updated_at": datetime.utcnow()}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Update failed")

    return {"message": f"Role updated to '{new_role}' for user {user_id}"}



@router.delete("/events/{event_id}/permissions/{user_id}")
async def remove_collaborator(
    event_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user),
    auth=Depends(PermissionChecker("events", "DELETE"))
):
    db = get_db()
    events = db["events"]
    versions = db["event_versions"]

    # Find event
    event = await events.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event["created_by"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the creator can remove collaborators")

    # Check if user is in collaborators
    collaborators = event.get("collaborators", [])
    target = next((c for c in collaborators if c["user_id"] == user_id), None)

    if not target:
        raise HTTPException(status_code=404, detail="User not found in collaborators")

    # Remove collaborator
    await events.update_one(
        {"_id": ObjectId(event_id)},
        {"$pull": {"collaborators": {"user_id": user_id}}}
    )


    return {"message": f"Access removed for user {user_id}"}



