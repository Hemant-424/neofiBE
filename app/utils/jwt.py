from datetime import datetime, timedelta
from jose import jwt, JWTError

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# def create_access_token(data: dict):
    
#     expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     data.update({"exp": expire, "type": "access"})
#     return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    # print(data)
    claims = {"email": data["sub"],"company":"neofi","developers": "hemantsingh", "iat": datetime.utcnow()}
    to_encode = claims.copy()
    if expires_delta:
        expire_at = datetime.utcnow() + expires_delta
    else:
        expire_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire_at})
    encoded_jwt = jwt.encode(
        to_encode, 
        SECRET_KEY, 
        algorithm=ALGORITHM)

    return encoded_jwt

# def create_refresh_token(data: dict):
#     expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
#     data.update({"exp": expire, "type": "refresh"})
#     return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM), expire
def create_refresh_token(data: dict):
    # print(data)
    claims = {"email": data["sub"],"company":"neofi","developers": "hemantsingh", "iat": datetime.utcnow()}
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    claims.update({"exp": expire, "type": "refresh"})
    refresh_token = jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)
    return refresh_token, expire

def decode_access_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
