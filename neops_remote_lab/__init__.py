from __future__ import annotations

try:  # Python 3.8+ importlib.metadata backport for runtime resolution
    from importlib.metadata import PackageNotFoundError, version as _dist_version
except Exception:  # pragma: no cover
    _dist_version = None  # type: ignore[assignment]
    PackageNotFoundError = Exception  # type: ignore[misc,assignment]

# Public models re-exported at the package root for convenient imports
from .models import (  # noqa: F401
    DeviceInfoDto,
    LabStatusDto,
    AcquireResponseDto,
    SessionState,
    SessionInfoDto,
    CreateSessionResponseDto,
    SessionStatusResponseDto,
    ActiveSessionResponseDto,
)


def _resolve_version() -> str:
    """Return installed distribution version; fallback to '0.0.0' when unavailable.

    Using importlib.metadata ensures the version matches the built wheel uploaded to PyPI.
    """
    dist_name = "neops_remote_lab"
    try:
        if _dist_version is None:  # type: ignore[truthy-function]
            return "0.0.0"
        return _dist_version(dist_name)
    except PackageNotFoundError:  # pragma: no cover - during editable installs or tests
        return "0.0.0"


__version__: str = _resolve_version()

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
