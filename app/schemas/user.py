from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    email: EmailStr
    role_id: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class TokenLogoutRequest(BaseModel):
    refresh_token: str