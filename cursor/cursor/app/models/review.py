from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_id = Column(Integer, ForeignKey("forensic_analyses.id", ondelete="SET NULL"), nullable=True, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    decision = Column(String(50), nullable=False)  # approved, manual_audit_required, flagged_for_investigation
    comments = Column(Text, nullable=True)
    is_final = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    claim = relationship("Claim", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")

    def __repr__(self):
        return f"<Review(id={self.id}, claim_id={self.claim_id}, decision='{self.decision}')>"
