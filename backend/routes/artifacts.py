from fastapi import APIRouter, Depends, HTTPException
from db import db
from models import ArtifactCreate
from auth import get_current_user
from firebase_setup import db as firebase_db
from datetime import datetime
import asyncio
from pydantic import BaseModel

class ArtifactUpdate(BaseModel):
    title: str

router = APIRouter()

def get_activity_log_ref():
    return firebase_db.reference("/activityLogs")

async def fetch_activity_logs():
    return get_activity_log_ref().order_by_child("timestamp").get()

def push_activity_log(log_data):
    get_activity_log_ref().push(log_data)

def delete_activity_log(key):
    get_activity_log_ref().child(key).delete()

def format_artifact_message(action: str, actor: str, title: str, node_id: int, when: datetime) -> str:
    if action == "CREATE":
        return f"{actor} created artifact '{title}' under node {node_id} at {when.strftime('%Y-%m-%d %H:%M UTC')}"
    elif action == "DELETE":
        return f"{actor} deleted artifact '{title}' from node {node_id} at {when.strftime('%Y-%m-%d %H:%M UTC')}"
    elif action == "UPDATE":
        return f"{actor} updated artifact '{title}' under node {node_id} at {when.strftime('%Y-%m-%d %H:%M UTC')}"



# Viewer/Editor/Admin can read artifacts — but only where they have node access
@router.get("/api/nodes/{node_id}/artifacts")
async def get_artifacts(node_id: int, user=Depends(get_current_user)):
    access = await db.access.find_first(
        where={
            "userId": user.id,
            "nodeId": node_id,
            "role": {"in": ["ADMIN", "EDITOR", "VIEWER"]}
        }
    )
    if not access:
        raise HTTPException(status_code=403, detail="You don't have access to this node.")

    artifacts = await db.artifact.find_many(where={"nodeId": node_id})
    return artifacts

@router.post("/api/artifacts")
async def create_artifact(payload: ArtifactCreate, user=Depends(get_current_user)):
    access = await db.access.find_first(
        where={
            "userId": user.id,
            "nodeId": payload.nodeId,
            "role": {"in": ["ADMIN", "EDITOR"]}
        }
    )
    if not access:
        raise HTTPException(status_code=403, detail="You don't have permission to add artifacts here.")

    artifact_task = asyncio.create_task(db.artifact.create(
        data={
            "title": payload.title,
            "description": payload.description,
            "link": payload.link,
            "nodeId": payload.nodeId,
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
        "action": "CREATE",
        "type": "ARTIFACT",
        "email": user.email,
        "performedBy": user.email,
        "timestamp": now.isoformat(),
        "message": format_artifact_message("CREATE", user.email, payload.title, payload.nodeId, now)
    }

    if logs and len(logs) >= 10:
        oldest = sorted(logs.items(), key=lambda x: x[1]["timestamp"])[0][0]
        delete_activity_log(oldest)

    push_activity_log(log_data)

    return artifact



@router.delete("/api/artifacts/{artifact_id}")
async def delete_artifact(artifact_id: int, user=Depends(get_current_user)):
    artifact = await db.artifact.find_unique(where={"id": artifact_id})
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    access = await db.access.find_first(
        where={
            "userId": user.id,
            "OR": [
                {"artifactId": artifact.id},
                {"nodeId": artifact.nodeId}
            ],
            "role": "ADMIN"
        }
    )
    if not access:
        raise HTTPException(status_code=403, detail="You are not allowed to delete this artifact.")

    delete_task = asyncio.create_task(db.artifact.delete(where={"id": artifact_id}))
    logs_task = asyncio.create_task(fetch_activity_logs())
    await delete_task
    logs = await logs_task

    now = datetime.utcnow()
    log_data = {
        "action": "DELETE",
        "type": "ARTIFACT",
        "email": user.email,
        "performedBy": user.email,
        "timestamp": now.isoformat(),
        "message": format_artifact_message("DELETE", user.email, artifact.title, artifact.nodeId, now)
    }

    if logs and len(logs) >= 10:
        oldest = sorted(logs.items(), key=lambda x: x[1]["timestamp"])[0][0]
        delete_activity_log(oldest)

    push_activity_log(log_data)

    return {"message": f"Artifact {artifact_id} deleted."}

@router.put("/api/artifacts/{artifact_id}")
async def update_artifact(artifact_id: int, payload: ArtifactUpdate, user=Depends(get_current_user)):
    artifact = await db.artifact.find_unique(where={"id": artifact_id})
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Check if user is ADMIN on artifact or its parent node
    access = await db.access.find_first(
        where={
            "userId": user.id,
            "OR": [
                {"artifactId": artifact.id},
                {"nodeId": artifact.nodeId}
            ],
            "role": "ADMIN"
        }
    )
    if not access:
        raise HTTPException(status_code=403, detail="You don't have permission to rename this file.")

    
    update_task = asyncio.create_task(db.artifact.update(
        where={"id": artifact_id},
        data={"title": payload.title}))
    logs_task = asyncio.create_task(fetch_activity_logs())
    
    updated_artifact, logs = await asyncio.gather(update_task, logs_task)
    
    now = datetime.utcnow()
    log_data = {
        "action": "UPDATE",
        "type": "ARTIFACT",
        "email": user.email,
        "performedBy": user.email,
        "timestamp": now.isoformat(),
        "message": format_artifact_message("CREATE", user.email, payload.title, payload.nodeId, now)
    }

    if logs and len(logs) >= 10:
        oldest = sorted(logs.items(), key=lambda x: x[1]["timestamp"])[0][0]
        delete_activity_log(oldest)

    push_activity_log(log_data)
    
    return updated_artifact