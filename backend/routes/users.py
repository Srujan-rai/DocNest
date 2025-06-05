from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from db import db
from auth import get_current_user  # ⬅️ Firebase ID token validator
from firebase_setup import db as firebase_db
from datetime import datetime, timedelta
import uuid
import smtplib
from email.message import EmailMessage
import traceback
import  base64
import asyncio

def get_user_log_ref():
    return firebase_db.reference("/activityLogs")

async def fetch_user_logs():
    return get_user_log_ref().order_by_child("timestamp").get()

def push_user_log(log_data):
    get_user_log_ref().push(log_data)

def delete_user_log(key):
    get_user_log_ref().child(key).delete()

def format_log_message(action: str, actor: str, target: str, when: datetime) -> str:
    action_map = {
        "CREATE": f"{actor} created account for {target}",
        "UPDATE": f"{actor} updated user {target}",
        "DELETE": f"{actor} deleted user {target}"
    }
    return f"{action_map[action]} at {when.strftime('%Y-%m-%d %H:%M UTC')}"



router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

def send_invite_email(email: str, name: str, token: str):
    signup_url = f"https://doc-nest-signup.vercel.app/?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "You're Invited to DocNest"
    msg["From"] = "noreply@yourapp.com"
    msg["To"] = email

    msg.set_content(f"""
        Hi ,

        You've been invited to join DocNest.

        Click the link below to sign up using your Google account:

        {signup_url}

        This invite is valid only for {email} and will expire in 48 hours.

        If you didn’t request this, you can ignore the email.

        - The DocNest Team
""")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login("srujan.rai@niveussolutions.com", "tqlg oeif kebt ehzr")
        smtp.send_message(msg)



@router.get("/api/users")
async def list_users(user=Depends(get_current_user)):
    # Check if current user has any ADMIN role
    admin_access = await db.access.find_first(
        where={
            "userId": user.id,
            "role": "ADMIN"
        }
    )
    if not admin_access:
        raise HTTPException(status_code=403, detail="Access denied. Admins only.")

    # Proceed to fetch users if the user is an admin
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



@router.get("/api/users/{email}")
async def get_user_access(email: str, user=Depends(get_current_user)):
    # ✅ Only allow ADMIN users to query others
    access_check = await db.access.find_first(
        where={
            "userId": user.id,
            "role": "ADMIN"
        }
    )
    if not access_check:
        raise HTTPException(403, "Only admins can view user access")

    target = await db.user.find_unique(where={"email": email})
    if not target:
        raise HTTPException(404, "User not found")

    access = await db.access.find_many(
        where={"userId": target.id},
        include={"node": True}
    )

    return {
        "id": target.id,
        "email": target.email,
        "name": target.name,
        "roles": [
            {
                "role": a.role,
                "nodeId": a.nodeId,
                "nodeName": a.node.name if a.node else None
            }
            for a in access if a.nodeId is not None
        ]
    }
@router.post("/api/users")
async def create_user(payload: UserCreate, user=Depends(get_current_user)):
    try:
        existing = await db.user.find_unique(where={"email": payload.email})
        if existing:
            raise HTTPException(400, "User already exists.")

        # ✅ 2. Generate secure token and expiry
        token = str(uuid.uuid4())
        expires_at = (datetime.utcnow() + timedelta(days=2)).isoformat()

        safe_email = base64.urlsafe_b64encode(payload.email.encode()).decode()

        invite_ref = firebase_db.reference(f"invites/{safe_email}")
        invite_ref.set({
            "token": token,
            "used": False,
            "email": payload.email,
            "name": payload.name or "",
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at
        })

        send_invite_email(payload.email, payload.name, token)
        
        now = datetime.utcnow()
        log_data = {
            "action": "CREATE",
            "email": payload.email,
            "performedBy": user.email,
            "timestamp": now.isoformat(),
            "message": format_log_message("CREATE", user.email, payload.email, now)
        }

        user_create = asyncio.create_task(db.user.create(data={"email": payload.email, "name": payload.name}))
        logs_fetch = asyncio.create_task(fetch_user_logs())
        _, logs = await asyncio.gather(user_create, logs_fetch)

        if logs and len(logs) >= 10:
            oldest = sorted(logs.items(), key=lambda i: i[1]["timestamp"])[0][0]
            delete_user_log(oldest)

        push_user_log(log_data)

        return {"message": f"Invite sent to {payload.email} and user is created"}

    except Exception as e:
        print("🔥 Error during invite flow:", e)
        traceback.print_exc()
        raise HTTPException(500, f"Internal Server Error: {str(e)}")
    
    
@router.put("/api/users/{user_id}")
async def update_user(user_id: int, payload: UserUpdate, user=Depends(get_current_user)):
    target = await db.user.find_unique(where={"id": user_id})
    if not target:
        raise HTTPException(404, "User not found.")

    now = datetime.utcnow()
    updated_email = payload.email or target.email

    log_data = {
        "action": "UPDATE",
        "email": updated_email,
        "performedBy": user.email,
        "timestamp": now.isoformat(),
        "message": format_log_message("UPDATE", user.email, updated_email, now)
    }

    update_task = asyncio.create_task(db.user.update(
        where={"id": user_id},
        data={"email": payload.email, "name": payload.name}
    ))
    logs_task = asyncio.create_task(fetch_user_logs())

    result, logs = await asyncio.gather(update_task, logs_task)

    if logs and len(logs) >= 10:
        oldest = sorted(logs.items(), key=lambda i: i[1]["timestamp"])[0][0]
        delete_user_log(oldest)

    push_user_log(log_data)

    return result 


@router.delete("/api/users/{id}")
async def delete_user(id: str, user=Depends(get_current_user)):
    target = await db.user.find_unique(where={"email": id})
    if not target:
        raise HTTPException(404, "User not found.")

    admin_access = await db.access.find_first(
        where={"userId": user.id, "role": "ADMIN"}
    )
    if not admin_access:
        raise HTTPException(403, "Only admins can delete users.")

    now = datetime.utcnow()
    log_data = {
        "action": "DELETE",
        "email": id,
        "performedBy": user.email,
        "timestamp": now.isoformat(),
        "message": format_log_message("DELETE", user.email, id, now)
    }

    delete_access = asyncio.create_task(db.access.delete_many(where={"userId": target.id}))
    delete_user = asyncio.create_task(db.user.delete(where={"email": id}))
    logs_task = asyncio.create_task(fetch_user_logs())

    await asyncio.gather(delete_access, delete_user)
    logs = await logs_task

    if logs and len(logs) >= 10:
        oldest = sorted(logs.items(), key=lambda i: i[1]["timestamp"])[0][0]
        delete_user_log(oldest)

    push_user_log(log_data)

    return {"message": f"User {id} deleted successfully"}  # ✅ No frontend change