from fastapi import APIRouter, UploadFile, Form, Depends, HTTPException
from db import db
from auth import get_current_user
from uuid import uuid4
import os
from supabase import create_client
from dotenv import load_dotenv
from firebase_setup import db as firebase_db
from datetime import datetime
import asyncio

router = APIRouter()

def get_activity_log_ref():
    return firebase_db.reference("/activityLogs")

async def fetch_activity_logs():
    return get_activity_log_ref().order_by_child("timestamp").get()

def push_activity_log(log_data):
    get_activity_log_ref().push(log_data)

def delete_activity_log(key):
    get_activity_log_ref().child(key).delete()

def format_artifact_upload_message(actor: str, artifact_title: str, node_id: int, when: datetime) -> str:
    return f"{actor} uploaded and created artifact '{artifact_title}' under node {node_id} at {when.strftime('%Y-%m-%d %H:%M UTC')}"

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')  # Replace with actual Supabase URL
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_KEY')  # Replace with actual service_role key
SUPABASE_BUCKET = "docnest-uploads"

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

@router.post("/api/upload")
async def upload_file(
    file: UploadFile,
    title: str = Form(...),
    description: str = Form(...),
    nodeId: int = Form(...),
    user=Depends(get_current_user)
):
    # Authorization: Only ADMIN or EDITOR on the node
    access = await db.access.find_first(
        where={
            "userId": user.id,
            "nodeId": nodeId,
            "role": {"in": ["ADMIN", "EDITOR"]}
        }
    )
    if not access:
        raise HTTPException(status_code=403, detail="Permission denied to upload here.")

    try:
        contents = await file.read()
        filename = f"{uuid4().hex}_{file.filename}"
        supabase.storage.from_(SUPABASE_BUCKET).upload(
            filename,
            contents,
            {"content-type": file.content_type}
        )

        file_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"

        # Create artifact and fetch logs in parallel
        artifact_task = asyncio.create_task(db.artifact.create(
            data={
                "title": title,
                "description": description,
                "link": file_url,
                "nodeId": nodeId,
                "createdBy": user.id
            }
        ))
        logs_task = asyncio.create_task(fetch_activity_logs())

        artifact, logs = await asyncio.gather(artifact_task, logs_task)

        await db.access.create(
            data={
                "userId": user.id,
                "artifactId": artifact.id,
                "role": "ADMIN"
            }
        )

        now = datetime.utcnow()
        log_data = {
            "action": "UPLOAD",
            "type": "ARTIFACT",
            "email": user.email,
            "performedBy": user.email,
            "timestamp": now.isoformat(),
            "message": format_artifact_upload_message(user.email, title, nodeId, now)
        }

        if logs and len(logs) >= 10:
            oldest = sorted(logs.items(), key=lambda i: i[1]["timestamp"])[0][0]
            delete_activity_log(oldest)

        push_activity_log(log_data)

        return {"message": "File uploaded and artifact created ✅", "artifact": artifact}

    except Exception as e:
        print("Upload Error:", e)
        raise HTTPException(status_code=500, detail="Upload failed")
