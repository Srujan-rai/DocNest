from fastapi import APIRouter, Depends, HTTPException
from db import db
from auth import get_current_user
from models import NodeCreate

router = APIRouter()

@router.post("/api/nodes")
async def create_node(payload: NodeCreate, user=Depends(get_current_user)):
    #await db.connect()
    print(payload)

    if payload.parentId:
        access = await db.access.find_first(
            where={
                "userId": user["id"],
                "nodeId": payload.parentId,
                "role": {"in": ["ADMIN", "EDITOR"]}
            }
        )
        if not access:
            #await db.disconnect()
            raise HTTPException(403, "You don't have permission to add a folder here.")

    node = await db.node.create(
        data = {
            "name": payload.name,
            "type": payload.type,
            "parentId": payload.parentId
        }
)

    await db.access.create(
        data = {
            "userId": user["id"],
            "nodeId": node.id,
            "role": "ADMIN"
        }
    )

    #await db.disconnect()
    return node

@router.get("/api/nodes/{node_id}")
async def get_node(node_id: int):
    node = await db.node.find_unique(where={"id": node_id})
    if not node:
        raise HTTPException(404, "Node not found")
    return node