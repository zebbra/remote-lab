from __future__ import annotations

from typing import Any

from neops_remote_lab.devices.base_mock_device import BaseMockDevice

__all__ = ["NetlabDevice"]


class NetlabDevice(BaseMockDevice):
    """
    Lightweight wrapper around ``netlab inspect`` data.

    *All* original keys are preserved in :pyattr:`raw` so you can surface new
    convenience properties later without re-running the lab.
    """

    def __init__(self, node_name: str, inspect_data: dict[str, Any]) -> None:
        self._node_name = node_name
        self.raw = inspect_data  # keep full original data for later use

        # Extract and validate mandatory fields once
        self._host: str = str(self._get_required("mgmt", "ipv4"))
        self._ip: str = self._host  # alias for clarity
        self._username: str = str(self._get_required("ansible_user"))
        self._password: str = str(self._get_required("ansible_ssh_pass", default=""))
        self._device_type: str = str(self._get_required("ansible_network_os"))

    def _get_required(self, *keys: str, default: Any = None) -> Any:
        """Get a required nested value from raw data, raising ValueError if missing."""
        data = self.raw
        for key in keys:
            if not isinstance(data, dict) or key not in data:
                path = ".".join(keys)
                if default is not None:
                    return default
                raise ValueError(f"Device {self._node_name}: missing '{path}' in inspect data ")
            data = data[key]
        return data

    # -- BaseMockDevice -------------------------------------------------
    @property
    def host(self) -> str:  # type: ignore[override]
        return self._host

    @property
    def ip(self) -> str:  # type: ignore[override]
        return self._ip

    @property
    def username(self) -> str:  # type: ignore[override]
        return self._username

    @property
    def password(self) -> str:  # type: ignore[override]
        return self._password

    @property
    def device_type(self) -> str:  # type: ignore[override]
        return self._device_type

    # -- extras ---------------------------------------------------------
    @property
    def name(self) -> str:
        return self._node_name

    def __repr__(self) -> str:
        return f"<NetlabDevice {self.name}: {self.username}@{self.host} " f"({self.device_type})>"
