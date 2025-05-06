# backend/routes/uploads.py

import os
import uuid
from fastapi import APIRouter, File, Form, UploadFile, Depends, HTTPException
from supabase import create_client
from db import db
from auth import get_current_user

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = "docnest-uploads"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@router.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    nodeId: int = Form(...),
    user=Depends(get_current_user)
):
    access = await db.access.find_first(
        where={
            "userId": user["id"],
            "nodeId": nodeId,
            "role": {"in": ["ADMIN", "EDITOR"]}
        }
    )
    if not access:
        raise HTTPException(status_code=403, detail="Permission denied.")

    # Create a unique file name
    filename = f"{uuid.uuid4().hex}_{file.filename}"

    # Upload to Supabase Storage
    try:
        contents = await file.read()
        supabase.storage.from_(SUPABASE_BUCKET).upload(filename, contents, {"content-type": file.content_type})
        file_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    # Create artifact
    artifact = await db.artifact.create(
        data={
            "title": title,
            "description": description,
            "link": file_url,
            "nodeId": nodeId,
            "createdBy": user["id"]
        }
    )

    # Optional: Grant access to uploader
    await db.access.create(
        data={
            "userId": user["id"],
            "artifactId": artifact.id,
            "role": "ADMIN"
        }
    )

    return artifact
