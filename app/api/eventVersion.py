from fastapi import APIRouter, HTTPException, Depends, Query
from bson import ObjectId
from datetime import datetime
from typing import List, Optional
from app.schemas.event import EventCreate, EventUpdate
from app.api.auth import get_current_user
from app.database import get_db
from app.utils.diff import diff_versions
from app.services.collab import CollaborationManager
from app.core.permissions import ensure_collaborator
from fastapi import WebSocket, WebSocketDisconnect
from app.core.permissions import PermissionChecker

import json

router = APIRouter()


@router.get("/events/{event_id}/history/{version_id}")
async def get_event_version(
    event_id: str,
    version_id: str,
    current_user: dict = Depends(get_current_user),
    auth=Depends(PermissionChecker("events", "GET") )
):
    db = get_db()

    version = await db["event_versions"].find_one({
        "_id": ObjectId(version_id),
        "event_id": event_id
    })

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Format the output (convert _id and timestamp)
    version["_id"] = str(version["_id"])
    if "timestamp" in version:
        version["timestamp"] = version["timestamp"].isoformat()

    return {
        "event_id": event_id,
        "version": version
    }

@router.post("/events/{event_id}/rollback/{version_id}")
async def rollback_event_version(
    event_id: str,
    version_id: str,
    current_user: dict = Depends(get_current_user),
    auth=Depends(PermissionChecker("events", "POST") )
):
    db = get_db()
    events = db["events"]
    versions = db["event_versions"]

    # Fetch version to roll back to
    version = await versions.find_one({
        "_id": ObjectId(version_id),
        "event_id": event_id
    })
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    # version["_id"] = str(version["_id"])

    # Fetch current event
    event = await events.find_one({"_id": ObjectId(event_id)})
    # print(event)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Backup current state to versions
    current_snapshot = event.copy()
    # current_snapshot.pop("_id", None)
    current_snapshot["_id"] = str(current_snapshot["_id"])
 

    rollback_data = version.get("data", {}).copy()
    rollback_data.pop("_id", None)
    rollback_data["updated_at"] = datetime.utcnow()
    # print(rollback_data)

    diff = diff_versions(current_snapshot, rollback_data)
    # print(diff)
    # diff = json.loads(DeepDiff(current_snapshot, rollback_data, ignore_order=True).to_json())

    await versions.insert_one({
        "event_id": event_id,
        "change_type": "rollback",
        "data": current_snapshot,
        "diff": diff,
        "changed_by": current_user["email"],
        "timestamp": datetime.utcnow(),
        "reason": f"Rollback to version {version_id}"
    })

    # print(ObjectId(event_id))
    # Apply rollback
    result = await events.update_one(
        {"_id": ObjectId(event_id)},
        {"$set": rollback_data}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Rollback failed")

    updated_event = await events.find_one({"_id": ObjectId(event_id)})
    updated_event["_id"] = str(updated_event["_id"])
    # print(updated_event)

    return {
        "message": f"Rolled back to version {version_id}",
        "event": updated_event
    }


@router.get("/events/{event_id}/changelog")
async def get_event_changelog(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    auth=Depends(PermissionChecker("events", "GET") )
):
    db = get_db()
    versions = await db["event_versions"].find(
        {"event_id": event_id},{"_id": 0}
    ).sort("timestamp", 1).to_list(length=None)
    # print(versions)
    for v in versions:
        # v["_id"] = str(v["_id"])
        v["timestamp"] = v["timestamp"].isoformat()

    return {
        "event_id": event_id,
        "changelog": versions
    }



@router.get("/events/{event_id}/diff/{version_id_1}/{version_id_2}")
async def get_event_diff(
    event_id: str,
    version_id_1: str,
    version_id_2: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()

    # Fetch both versions
    v1 = await db["event_versions"].find_one({"_id": ObjectId(version_id_1), "event_id": event_id})
    v2 = await db["event_versions"].find_one({"_id": ObjectId(version_id_2), "event_id": eve    nt_id})

    if not v1 or not v2:
        raise HTTPException(status_code=404, detail="One or both versions not found")

    d1 = v1.get("data", {})
    d2 = v2.get("data", {})

    # Perform diff
    diff = diff_versions(d1, d2)


    return {
        "event_id": event_id,
        "version_1": str(v1["_id"]),
        "version_2": str(v2["_id"]),
        "diff": diff
    }


@router.get("/events/{event_id}/versions/data")
async def get_all_event_versions_data(
    event_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    versions_cursor = db["event_versions"].find(
        {"event_id": event_id}
    ).sort("timestamp", 1)

    versions = []
    async for version in versions_cursor:
        version_id = str(version["_id"])
        snapshot = version.get("data", {})
        snapshot["version_id"] = version_id
        snapshot["change_type"] = version.get("change_type", "update")
        snapshot["timestamp"] = version.get("timestamp").isoformat() if "timestamp" in version else None
        snapshot["changed_by"] = version.get("changed_by")

        versions.append(snapshot)

    if not versions:
        raise HTTPException(status_code=404, detail="No versions found")

    return {
        "event_id": event_id,
        "versions_data": versions
    }



manager = CollaborationManager()

@router.websocket("/ws/collaborate/{event_id}")
async def collaborate_event(event_id: str, websocket: WebSocket):
    await manager.connect(event_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(event_id, data)
    except WebSocketDisconnect:
        manager.disconnect(event_id, websocket)


from app.core.permissions import ensure_collaborator

@router.websocket("/ws/collaborate/{event_id}")
async def collaborate_event(event_id: str, websocket: WebSocket):
    await websocket.accept()
    token = websocket.query_params.get("token")
    email = decode_access_token(token).get("sub")
    db = get_db()
    await ensure_collaborator(event_id, email, db)

    await manager.connect(event_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(event_id, data)
    except WebSocketDisconnect:
        manager.disconnect(event_id, websocket)
