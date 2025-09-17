from __future__ import annotations

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


# Forward reference of DeviceInfoDto requires it defined first.
class DeviceInfoDto(BaseModel):  # type: ignore[misc]
    """Full information about a Netlab node as exchanged via the API."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Node name as reported by Netlab")
    raw: Dict[str, Any] = Field(..., description="Raw `netlab inspect` dictionary for the node")


class LabStatusDto(BaseModel):  # type: ignore[misc]
    """Server-side lab status extending the base lab status with API-specific fields."""

    running: bool = Field(..., description="Whether a lab is currently running")
    topology: Optional[str] = Field(None, description="Path of the running topology file")
    ref_count: int = Field(0, description="How many clients currently hold the lab")
    devices: List[DeviceInfoDto] = Field(default_factory=list)
    netlab_status: Optional[str] = Field(None, description="Raw output of `netlab status` if available")


# Response returned by POST /lab
class AcquireResponseDto(BaseModel):  # type: ignore[misc]
    reused: bool
    devices: List[DeviceInfoDto]


# --- Session Models ---


class SessionState(str, Enum):
    WAITING = "waiting"
    ACTIVE = "active"


class SessionInfoDto(BaseModel):  # type: ignore[misc]
    id: str
    status: SessionState
    position: int
    created_at: float
    last_seen_at: float
    topology_name: Optional[str] = None


class CreateSessionResponseDto(BaseModel):  # type: ignore[misc]
    session_id: str
    position: int


class SessionStatusResponseDto(BaseModel):  # type: ignore[misc]
    status: SessionState
    position: int


# Response for GET /active-session
class ActiveSessionResponseDto(SessionStatusResponseDto):  # type: ignore[misc]
    session_id: str
