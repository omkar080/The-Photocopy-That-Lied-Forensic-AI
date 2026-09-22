from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ClaimImage(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False, default=0)
    mime_type = Column(String(50), default="image/jpeg", nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)
    md5_hash = Column(String(32), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    metadata_json = Column(Text, nullable=True)  # EXIF camera model, timestamp, GPS, etc.
    upload_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    claim = relationship("Claim", back_populates="images")
    analysis = relationship("ForensicAnalysis", back_populates="image", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ClaimImage(id={self.id}, claim_id={self.claim_id}, filename='{self.filename}')>"
