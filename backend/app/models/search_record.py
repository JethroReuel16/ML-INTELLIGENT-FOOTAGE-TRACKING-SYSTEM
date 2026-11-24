
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Float,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class SearchRecord(Base):
    __tablename__ = "searches"

    id = Column(String(100), primary_key=True, index=True)

    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    source_id = Column(
        String(64),
        ForeignKey("video_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    status = Column(String(50), nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=True)

    reference_data = Column(JSONB, nullable=True)
    video_metadata = Column(JSONB, nullable=True)
    search_settings = Column(JSONB, nullable=True)

    video_path = Column(String(2048), nullable=True)
    reference_image_path = Column(String(2048), nullable=True)

    duration = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)
    frame_count = Column(Integer, nullable=True)

    result_payload = Column(JSONB, nullable=True)
    summary_payload = Column(JSONB, nullable=True)

    imported_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    matches = relationship(
        "SearchMatch",
        back_populates="search",
        cascade="all, delete-orphan"
    )
