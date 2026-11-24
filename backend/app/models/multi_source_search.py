
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class MultiSourceSearch(Base):
    __tablename__ = "multi_source_searches"

    id = Column(String(100), primary_key=True, index=True)

    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    status = Column(String(50), nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=True)

    source_count = Column(Integer, default=0)
    successful_sources = Column(Integer, default=0)
    failed_sources = Column(Integer, default=0)

    settings = Column(JSONB, nullable=True)
    matches_payload = Column(JSONB, nullable=True)

    original_payload = Column(JSONB, nullable=True)

    imported_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    items = relationship(
        "MultiSourceItem",
        back_populates="multi_search",
        cascade="all, delete-orphan"
    )


class MultiSourceItem(Base):
    __tablename__ = "multi_source_items"

    id = Column(Integer, primary_key=True, index=True)

    multi_search_id = Column(
        String(100),
        ForeignKey("multi_source_searches.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    source_id = Column(
        String(64),
        ForeignKey("video_sources.id", ondelete="SET NULL"),
        nullable=True
    )

    search_id = Column(
        String(100),
        ForeignKey("searches.id", ondelete="SET NULL"),
        nullable=True
    )

    source_name = Column(String(150), nullable=True)
    source_type = Column(String(30), nullable=True)

    status = Column(String(50), nullable=True)
    match_count = Column(Integer, default=0)
    message = Column(String(1000), nullable=True)

    original_payload = Column(JSONB, nullable=True)

    multi_search = relationship(
        "MultiSourceSearch",
        back_populates="items"
    )
