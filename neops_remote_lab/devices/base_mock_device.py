from __future__ import annotations

from abc import ABC, abstractmethod

from neops_workflow_engine_client.models.device_type_dto import DeviceTypeDto


class BaseMockDevice(ABC):
    @property
    @abstractmethod
    def host(self) -> str:
        pass

    @property
    @abstractmethod
    def ip(self) -> str:
        pass

    @property
    @abstractmethod
    def username(self) -> str:
        pass

    @property
    @abstractmethod
    def password(self) -> str:
        pass

    @property
    @abstractmethod
    def device_type(self) -> str:
        pass

    def __str__(self) -> str:
        return f"{self.device_type} device at {self.ip} with username {self.username}"

    def to_neops_device(self) -> DeviceTypeDto:
        return DeviceTypeDto(
            id=f"{self.device_type}-{self.ip}",  # TODO use a more unique ID
            hostname=self.host,
            ip=self.ip,
            username=self.username,
            vendor=self.device_type,
        )
