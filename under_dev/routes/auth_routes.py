# backend/routes/auth_routes.py
from fastapi import APIRouter, Depends
from auth import get_current_user

router = APIRouter()

@router.post("/api/auth")
async def verify_user(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
    }
