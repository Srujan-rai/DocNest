from fastapi import APIRouter, Depends, HTTPException
from db import db
from auth import get_current_user
from models import NodeCreate

router = APIRouter()

@router.post("/api/nodes")
async def create_node(payload: NodeCreate, user=Depends(get_current_user)):
    # If this is a child node, check permission to write to its parent
    if payload.parentId:
        access = await db.access.find_first(
            where={
                "userId": user.id,
                "nodeId": payload.parentId,
                "role": {"in": ["ADMIN", "EDITOR"]}
            }
        )
        if not access:
            raise HTTPException(403, "You don't have permission to add a folder here.")

    # Create node
    node = await db.node.create(
        data={
            "name": payload.name,
            "type": payload.type,
            "parentId": payload.parentId
        }
    )

    # Give creator ADMIN access to the new node
    await db.access.create(
        data={
            "userId": user.id,
            "nodeId": node.id,
            "role": "ADMIN"
        }
    )

    return node

@router.get("/api/nodes/{node_id}")
async def get_node(node_id: int, user=Depends(get_current_user)):
    # Optional: check if the user has access to this node
    access = await db.access.find_first(
        where={
            "userId": user.id,
            "nodeId": node_id,
            "role": {"in": ["ADMIN", "EDITOR", "VIEWER"]}
        }
    )
    if not access:
        raise HTTPException(403, "You do not have access to view this node.")

    node = await db.node.find_unique(where={"id": node_id})
    if not node:
        raise HTTPException(404, "Node not found")
    return node
