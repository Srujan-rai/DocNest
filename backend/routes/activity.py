from fastapi import APIRouter, Depends, HTTPException
from db import db
from auth import get_current_user
from firebase_setup import db as firebase_db
from typing import List, Dict

router = APIRouter()

def get_activity_log_ref():
    return firebase_db.reference("/activityLogs")  # ✅ use /activityLogs

async def fetch_activity_logs():
    return get_activity_log_ref().order_by_child("timestamp").get()

@router.get("/api/activity", response_model=List[Dict[str, str]])
async def get_activity(user=Depends(get_current_user)):
    # ✅ Admin-only access check
    is_admin = await db.access.find_first(
        where={"userId": user.id, "role": "ADMIN"}
    )
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admins only.")

    try:
        raw_logs = await fetch_activity_logs()
        if not raw_logs:
            return []

        simplified = [
            {"id": key, "message": log["message"]}
            for key, log in raw_logs.items()
            if "message" in log
        ]

        sorted_logs = sorted(simplified, key=lambda x: raw_logs[x["id"]]["timestamp"], reverse=True)
        return sorted_logs

    except Exception as e:
        print("🔥 Error retrieving activity logs:", e)
        raise HTTPException(status_code=500, detail="Failed to fetch activity logs")
    