from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version

# Re-export public models from the models package for convenience
from .models import (
    AcquireResponseDto,
    ActiveSessionResponseDto,
    CreateSessionResponseDto,
    DeviceInfoDto,
    LabStatusDto,
    SessionInfoDto,
    SessionState,
    SessionStatusResponseDto,
)

try:
    __version__: str = _dist_version("neops_remote_lab")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = [
    "AcquireResponseDto",
    "ActiveSessionResponseDto",
    "CreateSessionResponseDto",
    # Models
    "DeviceInfoDto",
    "LabStatusDto",
    "SessionInfoDto",
    "SessionState",
    "SessionStatusResponseDto",
    "__version__",
]
