
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


class SearchMatch(Base):
    __tablename__ = "search_matches"

    id = Column(Integer, primary_key=True, index=True)

    search_id = Column(
        String(100),
        ForeignKey("searches.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    rank = Column(Integer, nullable=True)
    track_id = Column(Integer, nullable=True)

    class_id = Column(Integer, nullable=True)
    class_name = Column(String(150), nullable=True)

    match_status = Column(String(50), nullable=True)

    similarity_score = Column(Float, nullable=True)
    ranking_score = Column(Float, nullable=True)
    top3_average = Column(Float, nullable=True)
    average_similarity = Column(Float, nullable=True)

    timestamp = Column(Float, nullable=True)
    frame_number = Column(Integer, nullable=True)

    bbox = Column(JSONB, nullable=True)

    detection_confidence = Column(Float, nullable=True)
    frames_observed = Column(Integer, nullable=True)

    evidence_image = Column(String(2048), nullable=True)

    original_payload = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    search = relationship("SearchRecord", back_populates="matches")
