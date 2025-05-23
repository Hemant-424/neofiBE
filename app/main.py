from fastapi import FastAPI
from app.api import auth, users, roles, events, collaboration,eventVersion
from app.database import connect_db, get_db
from fastapi.middleware.cors import CORSMiddleware
import datetime

app = FastAPI(title="NeoFi Backend")

@app.get("/")
async def root():
    return {"message": "Welcome to NeoFi Backend!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/version")
async def version():
    return {"version": "1.0.0"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routes
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(roles.router, prefix="/api/roles", tags=["Roles"])
app.include_router(events.router, prefix="/api", tags=["Events"])
app.include_router(collaboration.router, prefix="/api", tags=["Collaboration"])
app.include_router(eventVersion.router, prefix="/api", tags=["Event Versioning"])

@app.on_event("startup")
async def startup_db():
    await connect_db()


#take this username and password from terminal
@app.on_event("startup")
async def create_owner_user():
    db = get_db()
    owner_email = "owner@neofi.com"
    users_col = db["users"]

    existing = await users_col.find_one({"email": owner_email})
    if not existing:
        from app.core.security import get_password_hash
        await users_col.insert_one({
            "email": owner_email,
            "hashed_password": get_password_hash("owner@123"),
            "role_id": "owner",
            "is_active": True,
            "created_at": datetime.datetime.utcnow()
        })
        #create default role
        await db["roles"].insert_one({
            "role": "owner",
            "created_by": owner_email})
        #create default permissions
        await db["permissions"].insert_one({
            "role": "owner",
            "permissions": {
                "events": {"GET": True, "POST": True, "PUT": True, "DELETE": True},
                "collaborators": {"GET": True, "POST": True, "PUT": True, "DELETE": True},
                "users": {"GET": True, "POST": True, "PUT": True, "DELETE": True},
                "roles": {"GET": True, "POST": True, "PUT": True, "DELETE": True}
            }
        })
        print("Owner user created (owner@neofi.com / owner@123)")
    else:
        # print("Owner user already exists")
        pass


        
