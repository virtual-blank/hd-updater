import msgspec
import uuid
from datetime import time




class UserSettingsOutputSchema(msgspec.Struct):
    name: str
    is_active: bool 
    time_from: str | None = None  # Формат "HH:MM:SS" или None
    time_to: str | None = None    # Формат "HH:MM:SS" или None
    days_of_week: list[int] = msgspec.field( default_factory=lambda:[0, 1, 2, 3, 4, 5, 6])
    unassigned_requests: bool = True
    assigned_to_me: bool = True
    alerts: bool = True


class UserOutputSchema(msgspec.Struct):
    telegram_id: int
    hd_api: str
    hd_technician_name: str
    settings: list[UserSettingsOutputSchema] = []


class UserProfileCache(msgspec.Struct):
    telegram_id: int
    hd_api: str
    hd_technician_name: str
    time_from: str | None = None  # Формат "HH:MM:SS" или None
    time_to: str | None = None    # Формат "HH:MM:SS" или None
    days_of_week: list[int] = msgspec.field( default_factory=lambda:[0, 1, 2, 3, 4, 5, 6])
    unassigned_requests: bool = True
    assigned_to_me: bool = True
    alerts: bool = True