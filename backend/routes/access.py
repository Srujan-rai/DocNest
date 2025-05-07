from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from enum import Enum
from db import db
from prisma.errors import UniqueViolationError

router = APIRouter()

class AccessRole(str, Enum):
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"

class GrantAccess(BaseModel):
    email: EmailStr
    nodeId: int
    role: AccessRole

class UpdateAccess(BaseModel):
    email: EmailStr
    nodeId: int
    role: AccessRole

class RevokeAccess(BaseModel):
    email: EmailStr
    nodeId: int

async def get_all_child_nodes(parent_id: int) -> list[int]:
    result = []

    async def recurse(current_id: int):
        children = await db.node.find_many(where={"parentId": current_id})
        for child in children:
            result.append(child.id)
            await recurse(child.id)

    await recurse(parent_id)
    return result

@router.post("/api/access")
async def grant_access(data: GrantAccess):
    user = await db.user.find_unique(where={"email": data.email})
    if not user:
        try:
            user = await db.user.create(data={"email": data.email})
        except UniqueViolationError:
            user = await db.user.find_unique(where={"email": data.email})

    existing = await db.access.find_first(where={"userId": user.id, "nodeId": data.nodeId})
    if existing:
        raise HTTPException(400, detail=f"User already has {existing.role} access.")

    access = await db.access.create(data={
        "userId": user.id,
        "nodeId": data.nodeId,
        "role": data.role.value
    })

    return {"message": f"Access granted", "accessId": access.id}

@router.put("/api/access")
async def update_access(data: UpdateAccess):
    user = await db.user.find_unique(where={"email": data.email})
    if not user:
        raise HTTPException(404, detail="User not found")

    all_node_ids = [data.nodeId] + await get_all_child_nodes(data.nodeId)
    updated = []

    for node_id in all_node_ids:
        existing = await db.access.find_first(where={"userId": user.id, "nodeId": node_id})
        if existing:
            await db.access.update(where={"id": existing.id}, data={"role": data.role.value})
        else:
            await db.access.create(data={"userId": user.id, "nodeId": node_id, "role": data.role.value})
        updated.append(node_id)

    return {"message": f"Role updated recursively", "updatedNodes": updated}

@router.delete("/api/access")
async def revoke_access(data: RevokeAccess):
    user = await db.user.find_unique(where={"email": data.email})
    if not user:
        raise HTTPException(404, detail="User not found")

    all_node_ids = [data.nodeId] + await get_all_child_nodes(data.nodeId)
    revoked = []

    for node_id in all_node_ids:
        access = await db.access.find_first(where={"userId": user.id, "nodeId": node_id})
        if access:
            await db.access.delete(where={"id": access.id})
            revoked.append(node_id)

    return {"message": f"Access revoked recursively", "revokedNodes": revoked}
