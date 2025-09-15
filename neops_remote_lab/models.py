from __future__ import annotations

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

from neops_remote_lab.netlab.lab_manager import LabStatus as BaseLabStatus


# Forward reference of DeviceInfo requires it defined first.
class DeviceInfo(BaseModel):  # type: ignore[misc]
    """Full information about a Netlab node as exchanged via the API."""

    name: str = Field(..., description="Node name as reported by Netlab")
    raw: Dict[str, Any] = Field(..., description="Raw `netlab inspect` dictionary for the node")


class LabStatus(BaseModel):  # type: ignore[misc]
    """Server-side lab status extending the base lab status with API-specific fields."""

    running: bool = Field(..., description="Whether a lab is currently running")
    topology: Optional[str] = Field(None, description="Path of the running topology file")
    ref_count: int = Field(0, description="How many clients currently hold the lab")
    devices: List[DeviceInfo] = Field(default_factory=list)
    netlab_status: Optional[str] = Field(None, description="Raw output of `netlab status` if available")

    @classmethod
    def from_base_status(cls, base_status: BaseLabStatus, netlab_status: Optional[str] = None) -> LabStatus:
        """Create a server LabStatus from the base LabManager status."""
        return cls(
            running=base_status.running,
            topology=base_status.topology,
            ref_count=base_status.ref_count,
            devices=[DeviceInfo(name=d.name, raw=d.raw) for d in base_status.devices],
            netlab_status=netlab_status,
        )


# Response returned by POST /lab
class AcquireResponse(BaseModel):  # type: ignore[misc]
    reused: bool
    devices: List[DeviceInfo]


# --- Session Models ---


class SessionState(str, Enum):
    WAITING = "waiting"
    ACTIVE = "active"


class SessionInfo(BaseModel):  # type: ignore[misc]
    id: str
    status: SessionState
    position: int
    created_at: float
    last_seen_at: float
    topology_name: Optional[str] = None


class CreateSessionResponse(BaseModel):  # type: ignore[misc]
    session_id: str
    position: int


class SessionStatusResponse(BaseModel):  # type: ignore[misc]
    status: SessionState
    position: int


# Response for GET /active-session
class ActiveSessionResponse(SessionStatusResponse):  # type: ignore[misc]
    session_id: str
