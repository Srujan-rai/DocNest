from pydantic import BaseModel
from typing import Optional

class ArtifactCreate(BaseModel):
    title: str
    description: str
    link: str
    nodeId: int

class NodeCreate(BaseModel):
    name: str
    type: str
    parentId: Optional[int] = None
