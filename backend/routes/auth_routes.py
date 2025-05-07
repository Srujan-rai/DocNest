# backend/routes/auth_routes.py
from fastapi import APIRouter, Depends
from auth import get_current_user
from db import db
router = APIRouter()

@router.post("/api/auth")
async def verify_user(user=Depends(get_current_user)):
    # Fetch all access roles for this user
    access_entries = await db.access.find_many(
        where={"userId": user.id}
    )

    roles = [
        {
            "role": entry.role,
            "nodeId": entry.nodeId,
        }
        for entry in access_entries if entry.nodeId is not None
    ]

    has_admin_access = any(r["role"] == "ADMIN" for r in roles)
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "roles": roles,
        "isAdmin": has_admin_access
    }
