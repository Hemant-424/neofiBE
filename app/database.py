from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import Request
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()



# MongoDB connection URL
MONGO_URI = os.getenv("MONGO_URL")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")


# MONGO_URI = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URI)
db = None

async def connect_db():
    global db
    db = client[MONGO_DB_NAME]

def get_db():
    return db
