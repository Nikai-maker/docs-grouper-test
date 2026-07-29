import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GroupStatus(str, enum.Enum):
    open = "open"  # ещё принимает новые фото
    ready = "ready"  # таймаут истёк, готова к выдаче
    delivered = "delivered"  # внешний модуль забрал и подтвердил (ack)


class DocumentGroup(Base):
    __tablename__ = "document_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    status: Mapped[GroupStatus] = mapped_column(
        Enum(GroupStatus, name="group_status"), default=GroupStatus.open, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_photo_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    files: Mapped[list["DocumentFile"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class DocumentFile(Base):
    __tablename__ = "document_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_groups.id"), nullable=False)

    telegram_update_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    telegram_file_id: Mapped[str] = mapped_column(String, nullable=False)

    local_path: Mapped[str | None] = mapped_column(String, nullable=True)
    download_status: Mapped[str] = mapped_column(String, default="pending")

    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    group: Mapped["DocumentGroup"] = relationship(back_populates="files")
