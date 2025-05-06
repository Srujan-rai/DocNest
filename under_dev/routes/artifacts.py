# backend/routes/artifacts.py

from fastapi import APIRouter, Depends, HTTPException
from db import db
from models import ArtifactCreate
from auth import get_current_user

router = APIRouter()

@router.get("/api/nodes/{node_id}/artifacts")
async def get_artifacts(node_id: int):
    artifacts = await db.artifact.find_many(where={"nodeId": node_id})
    return artifacts

@router.post("/api/artifacts")
async def create_artifact(payload: ArtifactCreate, user=Depends(get_current_user)):
    access = await db.access.find_first(
        where={
            "userId": user["id"],
            "nodeId": payload.nodeId,
            "role": {"in": ["ADMIN", "EDITOR"]}
        }
    )
    if not access:
        raise HTTPException(403, "You don't have permission to add artifacts here.")

    artifact = await db.artifact.create(
        data={
            "title": payload.title,
            "description": payload.description,
            "link": payload.link,
            "nodeId": payload.nodeId,
            "createdBy": user["id"]
        }
    )

    await db.access.create(
        data={
            "userId": user["id"],
            "artifactId": artifact.id,
            "role": "ADMIN"
        }
    )

    return artifact
