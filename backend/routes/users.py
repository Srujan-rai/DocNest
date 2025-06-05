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
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


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
    """
    Sends an HTML and plain-text invitation email to a user.

    Args:
        email (str): The recipient's email address.
        name (str): The recipient's name (can be empty).
        token (str): The unique invitation token.
    """
    signup_url = f"https://doc-nest-signup.vercel.app/?token={token}"
    # This is the user page they will be directed to *after* successful signup.
    # This information is more for your application logic post-signup,
    # rather than directly in this email sending function's core logic,
    # but good to keep in mind for the overall flow.
    # user_dashboard_url = "https://docnest-niveus-user.vercel.app/"


    # Create the root message and set the headers
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "You're Invited to Join DocNest!"
    msg["From"] = "DocNest Team <noreply@yourapp.com>" # Using a more descriptive sender
    msg["To"] = email

    # --- Create the plain-text version of your message ---
    text_content = f"""
Hi {name if name else "there"},

You've been invited to join DocNest!

DocNest is a robust knowledge base system for secure storage, retrieval, and management of hierarchical content like files and folders.

To get started, please click the link below to sign up using your Google account:
{signup_url}

This invitation is exclusively for {email} and will expire in 48 hours.

If you didn't request this invitation, please disregard this email. No further action is required.

Thanks,
The DocNest Team
"""
    part_text = MIMEText(text_content, "plain")
    msg.attach(part_text)

    # --- Create the HTML version of your message ---
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>You're Invited to DocNest!</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol';
            margin: 0;
            padding: 0;
            background-color: #f0f2f5; /* A light, neutral background */
            color: #333333;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}
        .email-container {{
            width: 100%;
            max-width: 600px;
            margin: 20px auto;
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden; /* Ensures border-radius is respected by children */
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }}
        .header {{
            background-color: #4A90E2; /* A welcoming blue, adjust to your brand */
            color: #ffffff;
            padding: 25px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 26px;
            font-weight: 600;
        }}
        .header img.logo {{ /* Optional: Add a logo */
            max-width: 150px;
            margin-bottom: 15px;
        }}
        .content {{
            padding: 25px 30px; /* More padding for content */
            line-height: 1.65;
            font-size: 16px;
            color: #333;
        }}
        .content p {{
            margin: 0 0 15px 0;
        }}
        .content strong {{
            color: #2c3e50;
        }}
        .button-container {{
            text-align: center;
            padding: 15px 0 25px 0;
        }}
        .button {{
            background-color: #5cb85c; /* A positive action color, e.g., green */
            color: #ffffff !important; /* Important to override default link color */
            padding: 14px 28px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            display: inline-block;
            font-size: 17px;
            border: none;
            cursor: pointer;
            transition: background-color 0.2s ease-in-out;
        }}
        .button:hover {{
            background-color: #4cae4c; /* Slightly darker on hover */
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            font-size: 13px;
            color: #888888;
            background-color: #f9f9f9;
            border-top: 1px solid #eeeeee;
        }}
        .footer a {{
            color: #4A90E2; /* Match header or brand color */
            text-decoration: none;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
        .important-note {{
            font-size: 14px;
            color: #777777;
            margin-top: 20px;
            padding: 10px;
            background-color: #f8f9fa;
            border-left: 3px solid #ffc107; /* An accent for important notes */
        }}
        .app-name {{
            font-weight: bold;
            color: #4A90E2; /* Brand color for emphasis */
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            {f'<img src="YOUR_DOCNEST_LOGO_URL_HERE" alt="DocNest Logo" class="logo">' if False else ''} 
            <h1>You're Invited!</h1>
        </div>
        <div class="content">
            <p>Hi {name if name else "there"},</p>
            <p>You've received an invitation to join <span class="app-name">DocNest</span>! We're excited to help you with our robust knowledge base system, designed for secure storage, retrieval, and management of hierarchical content like files and folders.</p>
            <p>To accept your invitation and create your account, please click the button below:</p>
        </div>
        <div class="button-container">
            <a href="{signup_url}" class="button">Accept Invitation & Sign Up</a>
        </div>
        <div class="content">
            <p>This invitation link is just for you (<strong>{email}</strong>) and will expire in <strong>48 hours</strong>.</p>
            <p class="important-note">If you weren't expecting this invitation, or if you believe it was sent in error, you can safely ignore this email. No account will be created unless you click the link above.</p>
        </div>
        <div class="footer">
            <p>&copy; { "2025" } DocNest by Niveus Solutions Part of NTT Data. All rights reserved.</p> 
            <p>If you have questions, please <a href="mailto:support@yourdocnestapp.com">contact our support team</a>.</p> 
            <p>The DocNest Team</p>
        </div>
    </div>
</body>
</html>
"""
    part_html = MIMEText(html_content, "html")
    msg.attach(part_html)

    # --- Send the email ---
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            # IMPORTANT: Storing credentials directly in code is not secure for production.
            # Consider using environment variables, a config file, or a secrets manager.
            # The password "tqlg oeif kebt ehzr" appears to be a Google App Password, which is good.
            smtp.login("srujan.rai@niveussolutions.com", "tqlg oeif kebt ehzr")
            smtp.send_message(msg)
        print(f"Invitation email successfully sent to {email}")
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Error: Failed to send email to {email}. Check credentials. Error: {e}")
    except smtplib.SMTPConnectError as e:
        print(f"SMTP Connect Error: Failed to connect to the server for {email}. Error: {e}")
    except smtplib.SMTPServerDisconnected as e:
        print(f"SMTP Server Disconnected: Connection lost while sending to {email}. Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while sending email to {email}: {e}")


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