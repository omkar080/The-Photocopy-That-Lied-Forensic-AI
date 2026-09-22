from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.orm import relationship
from app.database import Base


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    claim_number = Column(String(50), unique=True, index=True, nullable=False)
    policy_number = Column(String(50), index=True, nullable=False)
    claimant_name = Column(String(100), nullable=False)
    incident_date = Column(DateTime, nullable=True)
    claim_type = Column(String(50), default="Auto Damage", nullable=False)
    status = Column(String(30), default="submitted", nullable=False)  # submitted, in_review, flagged, verified
    estimated_amount = Column(Float, default=0.0, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    images = relationship("ClaimImage", back_populates="claim", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="claim", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="claim", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Claim(id={self.id}, claim_number='{self.claim_number}', status='{self.status}')>"
