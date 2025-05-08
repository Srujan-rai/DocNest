from fastapi import APIRouter, UploadFile, Form, Depends, HTTPException
from db import db
from auth import get_current_user
from uuid import uuid4
import os
from supabase import create_client
from dotenv import load_dotenv
router = APIRouter()

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

        artifact = await db.artifact.create(
            data={
                "title": title,
                "description": description,
                "link": file_url,
                "nodeId": nodeId,
                "createdBy": user.id
            }
        )

        await db.access.create(
            data={
                "userId": user.id,
                "artifactId": artifact.id,
                "role": "ADMIN"
            }
        )

        return {"message": "File uploaded and artifact created ✅", "artifact": artifact}

    except Exception as e:
        print("Upload Error:", e)
        raise HTTPException(status_code=500, detail="Upload failed")
