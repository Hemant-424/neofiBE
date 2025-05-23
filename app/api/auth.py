from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.schemas.user import UserCreate, TokenRefreshRequest, TokenLogoutRequest
from app.utils.jwt import create_access_token, decode_access_token, create_refresh_token
from app.core.security import get_password_hash, verify_password
from app.database import get_db
from app.models.user import User
from pymongo.errors import DuplicateKeyError
from jose import JWTError
import datetime

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@router.post("/register")
async def register(user: UserCreate):
    db = get_db()
    users_col = db["users"]

    existing_user = await users_col.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    user_dict = {
        "email": user.email,
        "hashed_password": hashed_password,
        "role_id": None,
        "is_active": True,
        "created_at": datetime.datetime.utcnow()
    }

    try:
        await users_col.insert_one(user_dict)
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="User already exists")

    return {"message": "User registered successfully"}


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_db()
    users = db["users"]
    refresh_tokens = db["refresh_tokens"]

    user = await users.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": user["email"]})
    refresh_token, expires_at = create_refresh_token({"sub": user["email"]})

    
    await refresh_tokens.insert_one({
        "token": refresh_token,
        "email": user["email"],
        "created_at": datetime.datetime.utcnow(),
        "expires_at": expires_at,
        "revoked": False
    })

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }



@router.post("/refresh")
async def refresh_token(payload: TokenRefreshRequest):
    db = get_db()
    refresh_tokens = db["refresh_tokens"]
    token = payload.refresh_token

    # Step 1: Decode and validate structure
    try:
        payload = decode_access_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        email = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Step 2: Check DB for token status
    token_doc = await refresh_tokens.find_one({
        "token": token,
        "email": email,
        "revoked": False
    })

    if not token_doc:
        raise HTTPException(status_code=401, detail="Token not found or already revoked")

    if token_doc["expires_at"] < datetime.datetime.utcnow():
        await refresh_tokens.update_one({"_id": token_doc["_id"]}, {"$set": {"revoked": True}})
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Step 3: Revoke the old token
    await refresh_tokens.update_one(
        {"_id": token_doc["_id"]},
        {"$set": {"revoked": True}}
    )

    # Step 4: Issue new tokens
    new_access_token = create_access_token({"sub": email})
    new_refresh_token, new_expiry = create_refresh_token({"sub": email})

    await refresh_tokens.insert_one({
        "token": new_refresh_token,
        "email": email,
        "created_at": datetime.datetime.utcnow(),
        "expires_at": new_expiry,
        "revoked": False
    })

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout(payload: TokenLogoutRequest):
    db = get_db()
    refresh_token = payload.refresh_token

    result = await db["refresh_tokens"].update_one(
        {"token": refresh_token},
        {"$set": {"revoked": True}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Token not found or already revoked")

    return {"message": "Logged out successfully"}



async def get_current_user(token: str = Depends(oauth2_scheme)):
    db = get_db()
    users_col = db["users"]
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials / Token has expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        email: str = payload.get("email")
        # print(payload)
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await users_col.find_one({"email": email})
    if user is None:
        raise credentials_exception
    return user
