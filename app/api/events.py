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
from app.utils.diff import diff_versions

router = APIRouter()

# Create a new event
@router.post("/events")
async def create_event(event: EventCreate, current_user: dict = Depends(get_current_user), auth=Depends(PermissionChecker("events", "POST"))):
    db = get_db()
    event_data = event.dict()
    event_data.update({
        "created_by": current_user["email"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "collaborators": event.collaborators or []
    })
    result = await db["events"].insert_one(event_data)
    return {"message": "Event created", "event_id": str(result.inserted_id)}



#get events with date filtering and pagination per page
@router.get("/events")
async def get_events(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user_id: Optional[str] = Query(None, description="Filter by a specific user ID"),
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    events_collection = db["events"]
    # print(current_user)
    # If no user_id passed, default to current user
    target_user_id = user_id
    target_user_email = current_user["email"]  # creator email only from logged-in user

    # Base access filter: creator or collaborator
    filters = {
        "$or": [
            {"created_by": target_user_email if not user_id else {"$exists": True}},  # allow creator check only for self
            {"collaborators.user_id": target_user_id}
        ]
    }

    # Date range filter
    if start_date or end_date:
        date_range = {}
        try:
            if start_date:
                date_range["$gte"] = datetime.fromisoformat(start_date)
            if end_date:
                date_range["$lte"] = datetime.fromisoformat(end_date)
            filters["start_time"] = date_range
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Pagination 
    skip = (page - 1) * per_page

    # Query events
    cursor = events_collection.find(filters).sort("start_time", 1).skip(skip).limit(per_page)
    events = []
    async for event in cursor:
        event["_id"] = str(event["_id"])
        for field in ["start_time", "end_time", "created_at", "updated_at"]:
            if field in event and isinstance(event[field], datetime):
                event[field] = event[field].isoformat()
        events.append(event)

    # Total count
    total_count = await events_collection.count_documents(filters)
    total_pages = (total_count + per_page - 1) // per_page

    data = {
        "page": page,
        "per_page": per_page,
        "total_events": total_count,
        "total_pages": total_pages,
        "events": events
    }
    return data



# Get a specific event by ID
@router.get("/events/{event_id}")
async def get_event(event_id: str, current_user: dict = Depends(get_current_user), auth=Depends(PermissionChecker("events", "GET"))):
    db = get_db()
    # print(event_id)
    event = await db["events"].find_one({"_id": ObjectId(event_id)})
    event["_id"] = str(event["_id"])
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event["created_by"] == current_user["email"]:
        # event["_id"] = str(event["_id"])
        return event

    collaborator = next((c for c in event.get("collaborators", []) if c["email"] == current_user["email"]), None)
    if not (collaborator and collaborator.get("permissions", {}).get("view", False)):
        raise HTTPException(status_code=403, detail="You do not have view permission")

    return event



# Update an event (with version logging)
@router.put("/events/{event_id}")
async def update_event(event_id: str, update: EventUpdate, current_user: dict = Depends(get_current_user), auth=Depends(PermissionChecker("events", "PUT"))):
    db = get_db()
    event = await db["events"].find_one({"_id": ObjectId(event_id)})
    event["_id"] = str(event["_id"])
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event["created_by"] == current_user["email"]:
        has_permission = True
    else:
        collaborator = next((c for c in event.get("collaborators", []) if c["email"] == current_user["email"]), None)
        has_permission = collaborator and collaborator.get("permissions", {}).get("edit", False)

    if not has_permission:
        raise HTTPException(status_code=403, detail="You do not have edit access")

    # Save version
    diff = diff_versions(event, update.dict())
    await db["event_versions"].insert_one({
        "event_id": event_id,
        "data": event,
        "diff": diff,
        "changed_by": current_user["email"],
        "timestamp": datetime.utcnow()
    })

    await db["events"].update_one({"_id": ObjectId(event_id)}, {"$set": update.dict()})
    return {"message": "Event updated"}



# Delete an event
@router.delete("/events/{event_id}")
async def delete_event(event_id: str, current_user: dict = Depends(get_current_user), auth=Depends(PermissionChecker("events", "DELETE"))):
    db = get_db()
    event = await db["events"].find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event["created_by"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Only the creator can delete the event")

    await db["events"].delete_one({"_id": ObjectId(event_id)})
    return {"message": "Event deleted successfully"}


# Batch create events
@router.post("/events/batch")
async def create_batch_events(events: List[EventCreate], current_user: dict = Depends(get_current_user), auth=Depends(PermissionChecker("events", "POST"))):
    db = get_db()
    now = datetime.utcnow()

    docs = []
    for e in events:
        doc = e.dict()
        doc.update({
            "created_by": current_user["email"],
            "created_at": now,
            "updated_at": now,
            "collaborators": e.collaborators or []
        })
        docs.append(doc)

    result = await db["events"].insert_many(docs)
    return {"message": f"{len(result.inserted_ids)} events created"}




