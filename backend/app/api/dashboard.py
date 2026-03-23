"""
Dashboard API endpoints.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Log, Incident
from app.core.security import get_current_user
from app.utils.logger import api_logger

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class DashboardStats(BaseModel):
    """Dashboard statistics - matches frontend data contract."""
    total_logs_ingested: int
    total_incidents_detected: int
    critical_incidents: int
    high_incidents: int


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get dashboard statistics.
    
    Frontend integration point: GET /api/dashboard/stats
    
    Returns stats matching frontend data contract:
    {total_logs_ingested, total_incidents_detected, critical_incidents, high_incidents}
    """
    api_logger.info(f"Fetching dashboard stats for user: {current_user['username']}")
    
    # Count logs
    total_logs = db.query(Log).count()
    
    # Count incidents
    total_incidents = db.query(Incident).count()
    critical_count = db.query(Incident).filter(Incident.severity == "Critical").count()
    high_count = db.query(Incident).filter(Incident.severity == "High").count()
    
    return DashboardStats(
        total_logs_ingested=total_logs,
        total_incidents_detected=total_incidents,
        critical_incidents=critical_count,
        high_incidents=high_count
    )
