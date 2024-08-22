from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pydantic import BaseModel
from passlib.context import CryptContext
from bson import ObjectId
import logging

app = FastAPI()

# MongoDB connection
try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["mydatabase"]
    users_collection = db["users"]
except Exception as e:
    logging.error(f"Error connecting to MongoDB: {e}")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(BaseModel):
    username: str
    email: str
    password: str

class Credentials(BaseModel):
    email: str
    password: str

class LinkID(BaseModel):
    user_id: str
    id_to_link: str

def serialize_object_id(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    raise TypeError("Type not serializable")

@app.post("/register")
def register_user(user: User):
    try:
        hashed_password = pwd_context.hash(user.password)
        user_dict = {
            "username": user.username,
            "email": user.email,
            "password": hashed_password,
            "linked_ids": []
        }
        users_collection.insert_one(user_dict)
        return {"msg": "User registered successfully"}
    except Exception as e:
        logging.error(f"Error in register_user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/login")
def login_user(credentials: Credentials):
    try:
        user = users_collection.find_one({"email": credentials.email})
        if not user or not pwd_context.verify(credentials.password, user["password"]):
            raise HTTPException(status_code=400, detail="Invalid credentials")
        return {"msg": "Login successful"}
    except Exception as e:
        logging.error(f"Error in login_user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/link-id")
def link_id(link_data: LinkID):
    try:
        user_id = ObjectId(link_data.user_id)  # Convert string to ObjectId
        user = users_collection.find_one({"_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        users_collection.update_one(
            {"_id": user_id},
            {"$push": {"linked_ids": link_data.id_to_link}}
        )
        return {"msg": "ID linked successfully"}
    except Exception as e:
        logging.error(f"Error in link_id: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/join")
def join_collections():
    try:
        data = list(users_collection.aggregate([
            {"$lookup": {
                "from": "another_collection",
                "localField": "linked_ids",
                "foreignField": "_id",
                "as": "joined_data"
            }}
        ]))
        return [dict(item, **{'_id': serialize_object_id(item['_id'])}) for item in data]
    except Exception as e:
        logging.error(f"Error in join_collections: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/chain-delete")
def chain_delete(user_id: str):
    try:
        user_id = ObjectId(user_id)  # Convert string to ObjectId
        result = users_collection.delete_one({"_id": user_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return {"msg": "User and related data deleted successfully"}
    except Exception as e:
        logging.error(f"Error in chain_delete: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
    except Exception as e:
        logging.error(f"Error starting the server: {e}")
