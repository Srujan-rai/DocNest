from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from db import db
from auth import get_current_user
from datetime import datetime

router = APIRouter()

# --------------------
# Pydantic Models
# --------------------

class NodeCreate(BaseModel):
    name: str
    type: str
    parentId: Optional[int] = None
    description: Optional[str] = None

class NodeUpdate(BaseModel):
    name: str
    description: Optional[str] = None

class ArtifactModel(BaseModel):
    id: int
    title: str
    description: Optional[str]
    link: Optional[str]
    nodeId: int
    createdBy: Optional[int]
    createdAt: datetime
    updatedAt: Optional[datetime]

    class Config:
        orm_mode = True

class NodeGraph(BaseModel):
    id: int
    name: str
    type: str
    description: Optional[str]
    parentId: Optional[int]
    createdAt: datetime
    children: List["NodeGraph"] = []
    artifacts: List[ArtifactModel] = []

    class Config:
        orm_mode = True

NodeGraph.update_forward_refs()

# --------------------
# Create Node Endpoint
# --------------------

@router.post("/api/nodes")
async def create_node(payload: NodeCreate, user=Depends(get_current_user)):
    # If this is a child node, check permission
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
            "parentId": payload.parentId,
            "description": payload.description
        }
    )

    # Grant creator ADMIN access
    await db.access.create(
        data={
            "userId": user.id,
            "nodeId": node.id,
            "role": "ADMIN"
        }
    )

    return node

# --------------------
# Get Single Node
# --------------------

@router.get("/api/nodes/{node_id}")
async def get_node(node_id: int, user=Depends(get_current_user)):
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

# --------------------
# Update Node
# --------------------

@router.put("/api/nodes/{node_id}")
async def update_node(node_id: int, payload: NodeUpdate, user=Depends(get_current_user)):
    access = await db.access.find_first(
        where={
            "userId": user.id,
            "nodeId": node_id,
            "role": "ADMIN"
        }
    )
    if not access:
        raise HTTPException(403, "You don't have permission to update this node.")

    updated_node = await db.node.update(
        where={"id": node_id},
        data={
            "name": payload.name,
            "description": payload.description
        }
    )
    return updated_node


#Build the nodes graph


async def build_node_graph(node_id: int, user_id: int) -> Optional[NodeGraph]:
    # Check access for current node
    access = await db.access.find_first(
        where={
            "userId": user_id,
            "nodeId": node_id,
            "role": {"in": ["ADMIN", "EDITOR", "VIEWER"]}
        }
    )
    if not access:
        return None

    # Fetch node data
    node = await db.node.find_unique(where={"id": node_id})
    if not node:
        return None

    # Fetch children nodes
    children = await db.node.find_many(where={"parentId": node_id})

    # Recursively build children graph if accessible
    visible_children = []
    for child in children:
        child_graph = await build_node_graph(child.id, user_id)
        if child_graph:
            visible_children.append(child_graph)

    # Fetch artifacts for this node
    artifacts_raw = await db.artifact.find_many(where={"nodeId": node_id})
    
    # Map artifacts to Pydantic models if needed
    artifacts = [
        ArtifactModel(
            id=a.id,
            title=a.title,
            description=a.description,
            link=a.link,
            nodeId=a.nodeId,
            createdBy=a.createdBy,
            createdAt=a.createdAt.isoformat(),
            updatedAt=a.updatedAt.isoformat() if a.updatedAt else None
        )
        for a in artifacts_raw
    ]

    return NodeGraph(
        id=node.id,
        name=node.name,
        type=node.type,
        description=node.description,
        parentId=node.parentId,
        createdAt=node.createdAt.isoformat(),
        children=visible_children,
        artifacts=artifacts,
        access=None
    )

# Endpoint to get graph starting at node_id, filtered by user access
@router.get("/api/nodes/{node_id}/graph", response_model=NodeGraph)
async def get_node_graph(node_id: int, user=Depends(get_current_user)):
    graph = await build_node_graph(node_id, user.id)
    if not graph:
        raise HTTPException(403, "You do not have access to this node or its children.")
    return graph
