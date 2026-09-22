from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ForensicAnalysis(Base):
    __tablename__ = "forensic_analyses"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    overall_risk_score = Column(Float, default=0.0, nullable=False)  # 0 to 100
    risk_level = Column(String(20), default="LOW", nullable=False)   # LOW, MODERATE, HIGH, CRITICAL
    confidence_score = Column(Float, default=0.0, nullable=False)    # 0.0 to 1.0
    is_tampered_suspected = Column(Boolean, default=False, nullable=False)
    summary_notes = Column(Text, nullable=True)
    fusion_explanation = Column(Text, nullable=True)
    status = Column(String(30), default="pending", nullable=False)   # pending, processing, completed, failed
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    image = relationship("ClaimImage", back_populates="analysis")
    module_results = relationship("ForensicModuleResult", back_populates="analysis", cascade="all, delete-orphan")
    fairness_result = relationship("FairnessResult", back_populates="analysis", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ForensicAnalysis(id={self.id}, image_id={self.image_id}, score={self.overall_risk_score}, level='{self.risk_level}')>"


class ForensicModuleResult(Base):
    __tablename__ = "forensic_module_results"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("forensic_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    module_name = Column(String(50), nullable=False, index=True)  # ELA, PRNU, JPEG_DCT, OVERLAY
    score = Column(Float, default=0.0, nullable=False)            # 0.0 to 100.0
    confidence = Column(Float, default=0.0, nullable=False)       # 0.0 to 1.0
    anomaly_detected = Column(Boolean, default=False, nullable=False)
    details_json = Column(Text, nullable=True)
    artifact_path = Column(String(500), nullable=True)            # Mask, heatmap or annotated artifact path
    execution_time_ms = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    analysis = relationship("ForensicAnalysis", back_populates="module_results")

    def __repr__(self):
        return f"<ForensicModuleResult(id={self.id}, module='{self.module_name}', score={self.score})>"
