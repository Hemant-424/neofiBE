from fastapi import APIRouter, Depends, HTTPException
from app.api.auth import get_current_user
from app.database import get_db
from bson import ObjectId
from app.core.permissions import PermissionChecker

router = APIRouter()

@router.get("/me")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get details of the currently authenticated user"""
    logger.info(f"Fetching profile for user: {current_user['email']}")
    return {
        "email": current_user["email"],
        "role_id": current_user.get("role_id", None),
        "is_active": current_user.get("is_active", True)
    }

@router.get("/list")
async def list_users(role: str = None, current_user: dict = Depends(get_current_user), auth=Depends(PermissionChecker("users", "GET"))):
    db = get_db()
    query = {"role_id": role.title()} if role else {}
    # print(current_user)
    logger.info(f"Listing users with role: {role} by {current_user['email']}")
    # Only allow admins to list users
    if current_user.get("role_id") != "Owner" and current_user.get("role_id") != "Admin":
        logger.warning(f"Unauthorized access attempt by {current_user['email']}")
        raise HTTPException(status_code=403, detail="Only owners/admins can list users.")
    else:
        users = await db["users"].find(query).to_list(length=None)
        for user in users:
            user["_id"] = str(user["_id"])
        return users


@router.post("/assign-role/{user_email}")
async def assign_role(user_email: str, role_id: str, current_user: dict = Depends(get_current_user), auth=Depends(PermissionChecker("users", "POST"))):
    """Assign a role to another user (admin-only)"""
    db = get_db()
    users_col = db["users"]
    logger.info(f"Assigning role '{role_id}' to user '{user_email}' by {current_user['email']}")
    # Only allow admins to assign roles
    if current_user.get("role_id") != "Admin" and current_user.get("role_id") != "Owner":
        logger.warning(f"Unauthorized role assignment attempt by {current_user['email']}")
        raise HTTPException(status_code=403, detail="Only admins can assign roles.")

    result = await users_col.update_one(
        {"email": user_email},
        {"$set": {"role_id": role_id}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info(f"Role '{role_id}' assigned to user '{user_email}' successfully")
    return {"message": f"Role '{role_id}' assigned to user '{user_email}'"}
