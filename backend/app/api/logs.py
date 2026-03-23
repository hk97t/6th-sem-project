"""
Log ingestion API endpoints.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Log
from app.core.security import get_current_user
from app.ml.inference import analyze_log
from app.services.incident_service import create_incident_from_log
from app.utils.logger import api_logger

router = APIRouter(prefix="/logs", tags=["Logs"])


class LogEntry(BaseModel):
    """Log entry request body."""
    source_ip: str
    destination: str
    event_type: str
    raw_data: Optional[str] = None
    
    # Feature fields for ML
    failed_attempts: int = 0
    bytes_transferred: int = 0
    request_rate: float = 0.0
    unusual_time: bool = False
    geo_anomaly: bool = False


class LogResponse(BaseModel):
    """Log ingestion response."""
    success: bool
    log_id: int
    incident_created: bool = False
    incident_id: Optional[int] = None
    message: str


@router.post("", response_model=LogResponse)
async def ingest_log(
    log_entry: LogEntry,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Ingest a security log and trigger ML analysis.
    
    Frontend integration point: POST /api/logs
    
    This endpoint:
    1. Stores the log in the database
    2. Runs ML anomaly detection
    3. Creates an incident if anomaly detected
    """
    api_logger.info(f"Ingesting log from {log_entry.source_ip}")
    
    # Create log entry
    log = Log(
        timestamp=datetime.utcnow(),
        source_ip=log_entry.source_ip,
        destination=log_entry.destination,
        event_type=log_entry.event_type,
        raw_data=log_entry.raw_data,
        failed_attempts=log_entry.failed_attempts,
        bytes_transferred=log_entry.bytes_transferred,
        request_rate=log_entry.request_rate,
        unusual_time=log_entry.unusual_time,
        geo_anomaly=log_entry.geo_anomaly
    )
    
    db.add(log)
    db.commit()
    db.refresh(log)
    
    # Run ML analysis
    incident_created = False
    incident_id = None
    
    try:
        ml_result = analyze_log({
            "failed_attempts": log_entry.failed_attempts,
            "bytes_transferred": log_entry.bytes_transferred,
            "request_rate": log_entry.request_rate,
            "unusual_time": log_entry.unusual_time,
            "geo_anomaly": log_entry.geo_anomaly
        })
        
        if ml_result and ml_result.get("is_anomaly"):
            # Create incident
            incident = create_incident_from_log(db, log, ml_result)
            incident_created = True
            incident_id = incident.id
            
            api_logger.info(f"Incident #{incident_id} created from log #{log.id}")
        
        # Mark log as processed
        log.is_processed = True
        if ml_result:
            log.anomaly_score = ml_result.get("confidence_score", 0)
        db.commit()
        
    except Exception as e:
        api_logger.error(f"ML analysis failed: {e}")
        # Log is still saved, just not processed
    
    message = "Log ingested successfully"
    if incident_created:
        message = f"Log ingested and incident #{incident_id} created"
    
    return LogResponse(
        success=True,
        log_id=log.id,
        incident_created=incident_created,
        incident_id=incident_id,
        message=message
    )


@router.get("/count")
async def get_log_count(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get total number of logs ingested."""
    count = db.query(Log).count()
    return {"total_logs": count}
