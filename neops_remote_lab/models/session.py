from __future__ import annotations

from typing import Optional
from enum import Enum
from pydantic import BaseModel


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


class ActiveSessionResponseDto(SessionStatusResponseDto):  # type: ignore[misc]
    session_id: str
