
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)

from app.database import Base


class EvidenceFile(Base):
    __tablename__ = "evidence_files"

    id = Column(Integer, primary_key=True, index=True)

    search_id = Column(
        String(100),
        ForeignKey("searches.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    match_id = Column(
        Integer,
        ForeignKey("search_matches.id", ondelete="CASCADE"),
        nullable=True
    )

    file_path = Column(String(2048), nullable=False)

    file_type = Column(String(50), default="image")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
