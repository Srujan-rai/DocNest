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
        Hi {name},

        You've been invited to join DocNest.

        Click the link below to sign up using your Google account:

        {signup_url}

        This invite is valid only for {email} and will expire in 48 hours.

        If you didn’t request this, you can ignore the email.

        - The DocNest Team
""")

    # 🔒 Use App Password or SMTP relay for Gmail or your SMTP service
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login("srujan.int@niveussolutions.com", "tqlg oeif kebt ehzr")
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
        await db.user.create(data={"email": payload.email, "name": payload.name})

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
    return await db.user.update(
        where={"id": user_id},
        data={"email": payload.email, "name": payload.name}
    )

@router.delete("/api/users/{id}")
async def delete_user(id: str, user=Depends(get_current_user)):
    target = await db.user.find_unique(where={"email": id})
    if not target:
        raise HTTPException(404, "User not found.")
    admin_access = await db.access.find_first(
        where={
            "userId": user.id,
            "role": "ADMIN"
        }
    )
    if not admin_access:
        raise HTTPException(403, "Only admins can delete users.")
    await db.access.delete_many(where={"userId": target.id})
    await db.user.delete(where={"email": id})
    return {"message": f"User {id} deleted successfully"}