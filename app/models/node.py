from enum import Enum
from typing import List, Literal, Optional

from pydantic import ConfigDict, BaseModel, Field


class NodeStatus(str, Enum):
    connected = "connected"
    connecting = "connecting"
    error = "error"
    disabled = "disabled"


class NodeSettings(BaseModel):
    min_node_version: str = "v0.2.0"
    certificate: str


class Node(BaseModel):
    name: str
    address: str
    port: int = 62050
    api_port: int = 62051
    usage_coefficient: float = Field(gt=0, default=1.0)


class NodeCreate(Node):
    add_as_new_host: bool = True
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "DE node",
            "address": "192.168.1.1",
            "port": 62050,
            "api_port": 62051,
            "add_as_new_host": True,
            "usage_coefficient": 1
        }
    })


class NodeModify(Node):
    name: Optional[str] = Field(None, nullable=True)
    address: Optional[str] = Field(None, nullable=True)
    port: Optional[int] = Field(None, nullable=True)
    api_port: Optional[int] = Field(None, nullable=True)
    status: Optional[NodeStatus] = Field(None, nullable=True)
    usage_coefficient: Optional[float] = Field(None, nullable=True)
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "DE node",
            "address": "192.168.1.1",
            "port": 62050,
            "api_port": 62051,
            "status": "disabled",
            "usage_coefficient": 1.0
        }
    })


class NodeResponse(Node):
    id: int
    xray_version: Optional[str] = None
    status: NodeStatus
    message: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class NodeEgressModify(BaseModel):
    """One outbound proxy configuration for one Marzban-Node."""
    protocol: str = Field(pattern="^(http|socks)$")
    udp_mode: str = Field("legacy", pattern="^(legacy|proxy|tcp_only)$")
    server: str = Field(min_length=1, max_length=253)
    port: int = Field(ge=1, le=65535)
    username: Optional[str] = Field(None, max_length=256)
    password: Optional[str] = Field(None, max_length=256)


class NodeEgressResponse(BaseModel):
    configured: bool
    udp_mode: str = "legacy"
    protocol: Optional[str] = None
    server: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    has_password: bool = False


class NodeRelayModify(BaseModel):
    mode: Literal["direct", "relay"]
    source: Literal["main"] = "main"
    entry_address: Optional[str] = Field(None, max_length=253)
    allocation: Literal["auto", "manual"] = "auto"
    listen_port: Optional[int] = Field(None, ge=1024, le=65535, strict=True)
    inbound_tag: Optional[str] = Field(None, max_length=256)
    model_config = ConfigDict(extra="forbid")


class NodeRelayResponse(BaseModel):
    configured: bool
    mode: Literal["direct", "relay"] = "direct"
    source: Literal["main"] = "main"
    entry_address: Optional[str] = None
    allocation: Literal["auto", "manual"] = "auto"
    listen_port: Optional[int] = None
    inbound_tag: Optional[str] = None
    target_address: Optional[str] = None
    target_port: Optional[int] = None
    status: Literal["inactive", "pending", "running", "error"] = "inactive"
    error: Optional[str] = None


class NodeUsageResponse(BaseModel):
    node_id: Optional[int] = None
    node_name: str
    uplink: int
    downlink: int


class NodesUsageResponse(BaseModel):
    usages: List[NodeUsageResponse]
