from fastapi import APIRouter, HTTPException, Depends
from app.schemas.role import RoleCreate, PermissionUpdate
from app.database import get_db
from app.api.auth import get_current_user
from app.core.permissions import PermissionChecker
from app.utils.logger import logger

router = APIRouter()

@router.post("/create-role")
async def create_role(role: RoleCreate, current_user: dict = Depends(get_current_user), auth=Depends(PermissionChecker("roles", "POST"))):
    db = get_db()
    roles_col = db["roles"]
    logger.info(f"Creating role: {role.role} by {current_user['email']}")
    existing = await roles_col.find_one({"role": role.role})
    if existing:
        logger.warning(f"Role {role.role} already exists")  
        raise HTTPException(status_code=400, detail="Role already exists")
    
    await roles_col.insert_one({
        "role": role.role.title(),
        "created_by": current_user["email"]
    })
    logger.info(f"Role {role.role} created successfully")
    return {"message": f"Role '{role.role}' created successfully"}


@router.post("/assign-permissions/{role}")
async def assign_permissions(role: str, perms: PermissionUpdate, current_user: dict = Depends(get_current_user), auth=Depends(PermissionChecker("roles", "POST"))):
    db = get_db()
    permissions_col = db["permissions"]
    logger.info(f"Assigning permissions to role: {role} by {current_user['email']}")
    # Check if role exists
    existing_role = await db["roles"].find_one({"role": role.title()}, {"_id": 0})
    if not existing_role:
        logger.warning(f"Role {role} does not exist")
        raise HTTPException(status_code=404, detail="Role not found")

    result = await permissions_col.update_one(
        {"role": role.title()},
        {"$set": {"permissions": perms.permissions}},
        upsert=True
    )
    logger.info(f"Permissions for role {role} updated successfully")

    return {"message": f"Permissions updated for role '{role}'"}

@router.get("/list-roles")
async def list_roles(current_user: dict = Depends(get_current_user), auth=Depends(PermissionChecker("roles", "GET"))):
    db = get_db()
    roles_col = db["roles"]
    logger.info(f"Listing roles by {current_user['email']}")
    roles = await roles_col.find().to_list(length=None)
    for role in roles:
        role["_id"] = str(role["_id"])
    logger.info(f"Roles listed successfully")
    return roles

@router.get("/role-permissions/{role}")
async def get_role_permissions(role: str, current_user: dict = Depends(get_current_user), auth=Depends(PermissionChecker("roles", "GET"))):
    db = get_db()
    permissions_col = db["permissions"]
    logger.info(f"Getting permissions for role: {role} by {current_user['email']}")
    role_permissions = await permissions_col.find_one({"role": role.title()},{"_id": 0})
    if not role_permissions:
        logger.warning(f"Permissions for role {role} not found")
        raise HTTPException(status_code=404, detail="Role not found")
    logger.info(f"Permissions for role {role} retrieved successfully")

    return role_permissions