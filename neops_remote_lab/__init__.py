from __future__ import annotations

from importlib.metadata import version as _dist_version, PackageNotFoundError

# Re-export public models from the models package for convenience
from .models import (
    DeviceInfoDto,
    LabStatusDto,
    AcquireResponseDto,
    SessionState,
    SessionInfoDto,
    CreateSessionResponseDto,
    SessionStatusResponseDto,
    ActiveSessionResponseDto,
)

try:
    __version__: str = _dist_version("neops_remote_lab")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = [
    "__version__",
    # Models
    "DeviceInfoDto",
    "LabStatusDto",
    "AcquireResponseDto",
    "SessionState",
    "SessionInfoDto",
    "CreateSessionResponseDto",
    "SessionStatusResponseDto",
    "ActiveSessionResponseDto",
]
