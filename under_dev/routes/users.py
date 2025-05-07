from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from db import db

router = APIRouter()


class UserCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None


@router.get("/api/users")
async def list_users():
    users = await db.user.find_many(
        include={
            "access": {
                "include": {"node": True}
            }
        }
    )
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "roles": [
                {
                    "role": a.role,
                    "nodeId": a.nodeId,
                    "nodeName": a.node.name if a.node else None
                } for a in u.access
            ]
        }
        for u in users
    ]


@router.post("/api/users")
async def create_user(payload: UserCreate):
    existing = await db.user.find_unique(where={"email": payload.email})
    if existing:
        raise HTTPException(400, "User already exists.")
    return await db.user.create(data={"email": payload.email, "name": payload.name})


@router.put("/api/users/{user_id}")
async def update_user(user_id: int, payload: UserUpdate):
    user = await db.user.find_unique(where={"id": user_id})
    if not user:
        raise HTTPException(404, "User not found.")
    return await db.user.update(
        where={"id": user_id},
        data={"email": payload.email, "name": payload.name}
    )
