"""
Incidents API endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Incident
from app.core.security import get_current_user
from app.services.incident_service import get_incident_list, get_incident_details, update_incident_status
from app.services.response_service import execute_response
from app.utils.logger import api_logger

router = APIRouter(prefix="/incidents", tags=["Incidents"])


class IncidentListItem(BaseModel):
    """Incident list item - matches frontend data contract."""
    incident_id: int
    severity: str
    status: str
    timestamp: str
    confidence_score: float = 0.0
    source_ip: str = ""
    description: str = ""


class IncidentDetail(BaseModel):
    """Incident details - matches frontend data contract."""
    incident_id: int
    severity: str
    status: str
    timestamp: str
    source_ip: str
    destination: str
    description: str
    anomaly_type: str
    confidence_score: float
    actions_taken: List[str]
    recommended_action: str


class ResponseTriggerRequest(BaseModel):
    """Response trigger request body."""
    action: str = "automated_response"


class ResponseTriggerResponse(BaseModel):
    """Response trigger response body."""
    success: bool
    message: str
    timestamp: str
    actions_taken: List[str] = []


@router.get("", response_model=List[IncidentListItem])
async def list_incidents(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of all incidents.
    
    Frontend integration point: GET /api/incidents
    
    Returns list matching frontend data contract:
    [{incident_id, severity, status, timestamp}, ...]
    """
    api_logger.info(f"Fetching incident list for user: {current_user['username']}")
    incidents = get_incident_list(db)
    return incidents


@router.get("/{incident_id}", response_model=IncidentDetail)
async def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get incident details by ID.
    
    Frontend integration point: GET /api/incidents/{id}
    
    Returns details matching frontend data contract.
    """
    api_logger.info(f"Fetching incident #{incident_id} for user: {current_user['username']}")
    
    details = get_incident_details(db, incident_id)
    
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident #{incident_id} not found"
        )
    
    return details


@router.post("/{incident_id}/respond", response_model=ResponseTriggerResponse)
async def trigger_response(
    incident_id: int,
    request: ResponseTriggerRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Trigger automated response for an incident.
    
    Frontend integration point: POST /api/incidents/{id}/respond
    
    Executes response actions based on severity:
    - Low: Log only
    - Medium: Alert
    - High: Block IP
    - Critical: Block IP + disable user
    """
    api_logger.info(f"Triggering response for incident #{incident_id} by user: {current_user['username']}")
    
    # Get incident
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident #{incident_id} not found"
        )
    
    # Execute response
    actions_taken = execute_response(db, incident, user_id=current_user.get("user_id"))
    
    from datetime import datetime
    
    return ResponseTriggerResponse(
        success=True,
        message=f"Response action '{request.action}' initiated for incident #{incident_id}",
        timestamp=datetime.utcnow().isoformat(),
        actions_taken=actions_taken
    )


@router.patch("/{incident_id}/status")
async def update_status(
    incident_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update incident status."""
    valid_statuses = ["Detected", "Investigating", "Mitigated", "Resolved"]
    
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    incident = update_incident_status(db, incident_id, status)
    
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident #{incident_id} not found"
        )
    
    return {"success": True, "incident_id": incident_id, "status": status}
