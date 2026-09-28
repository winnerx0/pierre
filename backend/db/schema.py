import enum
from datetime import datetime

from sqlalchemy import Enum, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Status(enum.Enum):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"


class Base(DeclarativeBase):
    pass


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[Status] = mapped_column(Enum(Status), nullable=False)
    createdAt: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
