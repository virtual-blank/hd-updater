import msgspec
from datetime import time


class UserCreateSchema(msgspec.Struct):
    telegram_id: int
    hd_api: str


class SettingsPresetUpdateSchema(msgspec.Struct):
    name: str | msgspec.UnsetType = msgspec.UNSET
    time_from: time | None | msgspec.UnsetType = msgspec.UNSET
    time_to: time | None | msgspec.UnsetType = msgspec.UNSET
    days_of_week: list[int] | msgspec.UnsetType = msgspec.UNSET
    unassigned_requests: bool | msgspec.UnsetType = msgspec.UNSET
    assigned_to_me: bool | msgspec.UnsetType = msgspec.UNSET
    alerts: bool | msgspec.UnsetType = msgspec.UNSET


class UserSettingsOutputSchema(msgspec.Struct):
    name: str
    is_active: bool 
    time_from: str | None = None
    time_to: str | None = None
    days_of_week: list[int] = msgspec.field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])
    unassigned_requests: bool = True
    assigned_to_me: bool = True
    alerts: bool = True


class UserOutputSchema(msgspec.Struct):
    telegram_id: int
    hd_api: str
    hd_technician_name: str
    settings: list[UserSettingsOutputSchema] = msgspec.field(default_factory=list)


class UserProfileCache(msgspec.Struct):
    telegram_id: int
    hd_api: str
    hd_technician_name: str
    time_from: str | None = None  # "HH:MM:SS" or None
    time_to: str | None = None    # "HH:MM:SS" or None
    days_of_week: list[int] = msgspec.field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])
    unassigned_requests: bool = True
    assigned_to_me: bool = True
    alerts: bool = True