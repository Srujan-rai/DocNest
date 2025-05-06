from fastapi import APIRouter
from db import db

router = APIRouter()

@router.get("/api/tree")
async def get_tree():
    #await db.connect()
    nodes = await db.node.find_many(
        where={"parentId": None},
        include={"children": {"include": {"children": True}}}
    )
    #await db.disconnect()
    return nodes
