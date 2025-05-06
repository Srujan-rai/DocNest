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
    return await db.user.find_many()


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


@router.get("/api/users")
async def list_users():
    users = await db.user.find_many(
        include={
            "access": True  # include all node-level roles
        }
    )
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "roles": [a.role for a in u.access]  # list of assigned roles
        }
        for u in users
    ]
