from fastapi import APIRouter, Depends, HTTPException
from db import db
from auth import get_current_user
from firebase_setup import db as firebase_db
from typing import List

router = APIRouter()

def get_activity_log_ref():
    return firebase_db.reference("/activityLogs")

async def fetch_activity_logs():
    return get_activity_log_ref().order_by_child("timestamp").get()

async def enrich_logs_with_users(logs: dict):
    emails = list({log.get("email") for log in logs.values() if log.get("email")})
    users = await db.user.find_many(where={"email": {"in": emails}})
    user_map = {u.email: {"id": u.id, "name": u.name} for u in users}

    enriched = []
    for key, log in logs.items():
        enriched.append({
            "id": key,
            **log,
            "userDetails": user_map.get(log.get("email"))
        })
    return enriched

@router.get("/api/activity", response_model=List[dict])
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

        enriched = await enrich_logs_with_users(raw_logs)
        enriched.sort(key=lambda x: x["timestamp"], reverse=True)
        return enriched

    except Exception as e:
        print("🔥 Error retrieving activity logs:", e)
        raise HTTPException(status_code=500, detail="Failed to fetch activity logs")
