from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LabStatusDto(BaseModel):  # type: ignore[misc]
    """Server-side lab status extending the base lab status with API-specific fields."""

    running: bool = Field(..., description="Whether a lab is currently running")
    topology: str | None = Field(None, description="Path of the running topology file")
    ref_count: int = Field(0, description="How many clients currently hold the lab")
    devices: list[DeviceInfoDto] = Field(default_factory=list)
    netlab_status: str | None = Field(None, description="Raw output of `netlab status` if available")


class AcquireResponseDto(BaseModel):  # type: ignore[misc]
    reused: bool
    devices: list[DeviceInfoDto]


class DeviceInfoDto(BaseModel):  # type: ignore[misc]
    """Full information about a Netlab node as exchanged via the API."""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="Node name as reported by Netlab")
    raw: dict[str, Any] = Field(..., description="Raw `netlab inspect` dictionary for the node")
