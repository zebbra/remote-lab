from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class LabStatusDto(BaseModel):  # type: ignore[misc]
    """Server-side lab status extending the base lab status with API-specific fields."""

    running: bool = Field(..., description="Whether a lab is currently running")
    topology: Optional[str] = Field(None, description="Path of the running topology file")
    ref_count: int = Field(0, description="How many clients currently hold the lab")
    devices: List["DeviceInfoDto"] = Field(default_factory=list)
    netlab_status: Optional[str] = Field(None, description="Raw output of `netlab status` if available")


class AcquireResponseDto(BaseModel):  # type: ignore[misc]
    reused: bool
    devices: List["DeviceInfoDto"]


class DeviceInfoDto(BaseModel):  # type: ignore[misc]
    """Full information about a Netlab node as exchanged via the API."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Node name as reported by Netlab")
    raw: Dict[str, Any] = Field(..., description="Raw `netlab inspect` dictionary for the node")
