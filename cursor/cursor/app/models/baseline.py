from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class DeviceBaseline(Base):
    __tablename__ = "device_baselines"

    id = Column(Integer, primary_key=True, index=True)
    device_make = Column(String(100), nullable=False, index=True)
    device_model = Column(String(100), nullable=False, index=True)
    sensor_type = Column(String(50), default="CMOS", nullable=True)
    typical_prnu_variance = Column(Float, default=0.015, nullable=False)
    typical_compression_quality = Column(Integer, default=90, nullable=False)
    standard_noise_floor = Column(Float, default=0.02, nullable=False)
    sample_count = Column(Integer, default=1, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    fairness_results = relationship("FairnessResult", back_populates="baseline")

    def __repr__(self):
        return f"<DeviceBaseline(id={self.id}, model='{self.device_make} {self.device_model}')>"
