from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class NodeType(str, Enum):
    SKILL = "skill"
    ROLE = "role"
    COURSE = "course"
    USER = "user"

class LinkType(str, Enum):
    REQUIRES = "REQUIRES"
    TEACHES = "TEACHES"
    HAS_SKILL = "HAS_SKILL"
    PART_OF = "PART_OF"

class Node(BaseModel):
    id: str
    type: NodeType
    category: Optional[str] = None
    title: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

class Link(BaseModel):
    source: str
    target: str
    type: LinkType
    weight: float = 1.0

class GraphData(BaseModel):
    nodes: list[Node] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)

class ExtractionResult(BaseModel):
    nodes: list[Node] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
    success: bool = True
    method: str = "llm"
