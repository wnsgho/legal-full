from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class Neo4jConnectionInfo(BaseModel):
    serverUrl: str
    username: str
    password: str
    database: str
    limit: Optional[int] = 1000


class Neo4jNode(BaseModel):
    id: int
    labels: List[str]
    properties: Dict[str, Any]


class Neo4jRelationship(BaseModel):
    id: int
    type: str
    start_node: int
    end_node: int
    properties: Dict[str, Any]


class Neo4jGraphDataResponse(BaseModel):
    success: bool
    nodes: List[Neo4jNode]
    relationships: List[Neo4jRelationship]
    database: str


class Neo4jStatsResponse(BaseModel):
    success: bool
    nodeCount: int
    relationshipCount: int
    database: str
