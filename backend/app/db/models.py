"""
SQLAlchemy ORM models for the Cloud Security Platform.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.db.database import Base


class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="analyst")  # admin, analyst
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")


class Log(Base):
    """Security log entry model."""
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source_ip = Column(String(50), index=True)
    destination = Column(String(255))
    event_type = Column(String(50), index=True)
    severity_hint = Column(String(20))  # Optional hint from log source
    raw_data = Column(Text)
    
    # ML processing fields
    is_processed = Column(Boolean, default=False)
    anomaly_score = Column(Float, nullable=True)
    
    # Feature fields for ML
    failed_attempts = Column(Integer, default=0)
    bytes_transferred = Column(Integer, default=0)
    request_rate = Column(Float, default=0.0)
    unusual_time = Column(Boolean, default=False)
    geo_anomaly = Column(Boolean, default=False)


class Incident(Base):
    """Security incident model."""
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    severity = Column(String(20), nullable=False, index=True)  # Critical, High, Medium, Low
    status = Column(String(20), nullable=False, default="Detected", index=True)  # Detected, Investigating, Mitigated, Resolved
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Incident details
    source_ip = Column(String(50))
    destination = Column(String(255))
    description = Column(Text, nullable=False)
    anomaly_type = Column(String(100), nullable=False)
    confidence_score = Column(Float, nullable=False)
    recommended_action = Column(Text)
    
    # Reference to source log
    log_id = Column(Integer, ForeignKey("logs.id"), nullable=True)
    
    # Relationships
    actions = relationship("IncidentAction", back_populates="incident", order_by="IncidentAction.timestamp")


class IncidentAction(Base):
    """Action taken on an incident."""
    __tablename__ = "incident_actions"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    action_text = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    incident = relationship("Incident", back_populates="actions")


class AuditLog(Base):
    """Audit log for tracking all system actions."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50))  # incident, user, log, etc.
    target_id = Column(Integer, nullable=True)
    details = Column(Text)
    ip_address = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = relationship("User", back_populates="audit_logs")
