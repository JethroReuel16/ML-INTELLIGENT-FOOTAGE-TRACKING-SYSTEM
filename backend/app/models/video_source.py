
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class VideoSource(Base):
    __tablename__ = "video_sources"

    id = Column(String(64), primary_key=True, index=True)

    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    name = Column(String(100), nullable=False)
    source_type = Column(String(30), nullable=False)
    url = Column(Text, nullable=False)

    location = Column(String(200), nullable=True)
    description = Column(String(500), nullable=True)

    last_connection_status = Column(
        String(50),
        nullable=False,
        default="not_tested",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
