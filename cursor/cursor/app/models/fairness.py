from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class FairnessResult(Base):
    __tablename__ = "fairness_results"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("forensic_analyses.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    device_baseline_id = Column(Integer, ForeignKey("device_baselines.id", ondelete="SET NULL"), nullable=True, index=True)
    device_model = Column(String(100), nullable=True)
    baseline_noise_level = Column(Float, default=0.0, nullable=False)
    observed_noise_level = Column(Float, default=0.0, nullable=False)
    baseline_compression_factor = Column(Float, default=0.0, nullable=False)
    observed_compression_factor = Column(Float, default=0.0, nullable=False)
    deviation_score = Column(Float, default=0.0, nullable=False)
    adjusted_score = Column(Float, default=0.0, nullable=False)
    adjustment_delta = Column(Float, default=0.0, nullable=False)
    fairness_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    analysis = relationship("ForensicAnalysis", back_populates="fairness_result")
    baseline = relationship("DeviceBaseline", back_populates="fairness_results")

    def __repr__(self):
        return f"<FairnessResult(id={self.id}, analysis_id={self.analysis_id}, device='{self.device_model}')>"
