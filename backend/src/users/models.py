
from database.db import Base
from database.mixins import Uuid7PkMixin, TimeStampMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, BigInteger, String, Integer
import uuid
from datetime import time
from sqlalchemy.dialects.postgresql import ARRAY


class User(Uuid7PkMixin, TimeStampMixin, Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    hd_api: Mapped[str | None]
    hd_technician_name: Mapped[str | None]

    settings_presets: Mapped[list["SettingsPreset"]] = relationship(
        "SettingsPreset", back_populates="user", cascade="all, delete-orphan", passive_deletes=True, lazy="raise_on_sql"
    )


class SettingsPreset(Uuid7PkMixin, TimeStampMixin, Base):
    __tablename__ = "settings_presets"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(25))
    is_active: Mapped[bool] = mapped_column(default=False)
    time_from: Mapped[time | None] = mapped_column(nullable=True, default=None)
    time_to: Mapped[time | None] = mapped_column(nullable=True, default=None)
    # дни недели: 0-понедельник, 1-вторник, 2-среда и тд.
    days_of_week: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=lambda: [0, 1, 2, 3, 4, 5, 6])
    unassigned_requests: Mapped[bool] = mapped_column(default=True)
    assigned_to_me: Mapped[bool] = mapped_column(default=True)
    alerts: Mapped[bool] = mapped_column(default=True)

    user: Mapped["User"] = relationship("User", back_populates="settings_presets", lazy="raise_on_sql")
