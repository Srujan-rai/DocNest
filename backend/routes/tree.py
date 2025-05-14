from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from db import db
from auth import get_current_user  # ✅ Firebase auth import
from firebase_setup import db as firebase_db

router = APIRouter()

def build_tree(flat_nodes):
    nodes = [n.dict() if hasattr(n, "dict") else n for n in flat_nodes]
    node_map = {node["id"]: {**node, "children": []} for node in nodes}
    tree = []
    for node in node_map.values():
        parent_id = node.get("parentId")
        if parent_id is None:
            tree.append(node)
        elif parent_id in node_map:
            node_map[parent_id]["children"].append(node)
    return tree

# --- GET FULL TREE ---
@router.get("/api/tree")
async def get_full_tree():  # ✅ Protected
    flat_nodes = await db.node.find_many(include={"artifacts": True})
    return build_tree(flat_nodes)


@router.get("/api/tree/{node_id}")
async def get_subtree(node_id: int, user=Depends(get_current_user)):  # ✅ Protected
    root = await db.node.find_unique(where={"id": node_id}, include={"artifacts": True})
    if not root:
        raise HTTPException(status_code=404, detail="Node not found")

    flat_nodes = await db.node.find_many(include={"artifacts": True})
    tree = build_tree(flat_nodes)

    def find_subtree(nodes, target_id):
        for node in nodes:
            if node["id"] == target_id:
                return node
            if node.get("children"):
                result = find_subtree(node["children"], target_id)
                if result:
                    return result
        return None

    subtree = find_subtree(tree, node_id)
    return subtree or {"message": "Subtree not found"}

# --- DELETE NODE + ALL DESCENDANTS ---
@router.delete("/api/nodes/{node_id}")
async def delete_node(node_id: int, user=Depends(get_current_user)):
    node = await db.node.find_unique(where={"id": node_id})
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # ✅ Step 1: Enforce ADMIN role for deletion
    access = await db.access.find_first(
        where={
            "userId": user.id,
            "nodeId": node_id,
            "role": "ADMIN"
        }
    )
    if not access:
        raise HTTPException(status_code=403, detail="Only ADMIN can delete this node.")

    # ✅ Step 2: Fetch all descendants and delete
    all_nodes = await db.node.find_many()
    ids_to_delete = collect_descendant_ids(all_nodes, node_id)

    await db.artifact.delete_many(where={"nodeId": {"in": ids_to_delete}})
    await db.node.delete_many(where={"id": {"in": ids_to_delete}})

    return {"message": f"Deleted node {node_id} and {len(ids_to_delete)-1} descendants."}

# --- Recursive Helper ---
def collect_descendant_ids(nodes, root_id):
    nodes = [n.dict() if hasattr(n, "dict") else n for n in nodes]
    id_set = {root_id}
    stack = [root_id]
    while stack:
        current = stack.pop()
        children = [n["id"] for n in nodes if n["parentId"] == current]
        id_set.update(children)
        stack.extend(children)
    return list(id_set)
