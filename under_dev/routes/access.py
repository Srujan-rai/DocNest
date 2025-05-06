from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from enum import Enum
from db import db
from prisma.errors import UniqueViolationError

router = APIRouter()

# Define allowed roles matching your Prisma enum
class AccessRole(str, Enum):
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"

# Request schema
class GrantAccess(BaseModel):
    email: EmailStr
    nodeId: int
    role: AccessRole

@router.post("/api/access")
async def grant_access(data: GrantAccess):
    # Step 1: Check if user exists
    user = await db.user.find_unique(where={"email": data.email})

    # Step 2: Try to create if not found
    if not user:
        try:
            user = await db.user.create(data={"email": data.email})
        except UniqueViolationError:
            # If race condition occurs, fetch the user again
            user = await db.user.find_unique(where={"email": data.email})

    # Step 3: Check if access already exists
    access = await db.access.find_first(
        where={"userId": user.id, "nodeId": data.nodeId}
    )
    if access:
        raise HTTPException(
            status_code=400,
            detail=f"User already has {access.role} access to this node."
        )

    # Step 4: Grant access
    granted = await db.access.create(data={
        "userId": user.id,
        "nodeId": data.nodeId,
        "role": data.role.value  # store enum value
    })

    # Step 5: Return a clean response
    return {
        "message": f"{data.role.value} access granted to {data.email} for node {data.nodeId}.",
        "accessId": granted.id
    }
