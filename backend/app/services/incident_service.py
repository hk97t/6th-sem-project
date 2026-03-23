"""
Incident Service - Handles incident creation and management.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from app.db.models import Incident, IncidentAction, Log
from app.ml.inference import analyze_log
from app.utils.logger import api_logger


def generate_description(anomaly_type: str, features: dict, source_ip: str, destination: str) -> str:
    """Generate a human-readable incident description."""
    
    descriptions = {
        "Brute Force Attack with Data Exfiltration": 
            f"Multiple failed authentication attempts ({features['failed_attempts']} failures) detected from {source_ip} "
            f"followed by large data transfer ({features['bytes_transferred']:,} bytes) to external destination. "
            f"Potential account compromise with subsequent data theft.",
        
        "Brute Force Attack":
            f"Multiple failed authentication attempts ({features['failed_attempts']} failures) detected from {source_ip}. "
            f"Pattern consistent with automated credential stuffing or brute force attack.",
        
        "Data Exfiltration":
            f"Abnormal data transfer pattern detected. {features['bytes_transferred']:,} bytes transferred from {destination} "
            f"to {source_ip}. Transfer rate and volume exceed normal baseline.",
        
        "API Abuse / DDoS Attempt":
            f"Elevated request rate ({features['request_rate']:.1f} req/s) detected from {source_ip} targeting {destination}. "
            f"Pattern indicates potential API abuse or distributed denial of service attempt.",
        
        "Suspicious Remote Access":
            f"Remote access detected from unusual geographic location during off-hours. "
            f"Source IP: {source_ip}. This deviates from established user behavior patterns.",
        
        "Geographic Anomaly":
            f"Access attempt from unexpected geographic location. Source IP: {source_ip}. "
            f"Location differs from user's established access patterns.",
        
        "Off-Hours Activity":
            f"System access detected outside normal business hours from {source_ip}. "
            f"Activity targeting {destination} may require verification.",
        
        "Elevated Request Rate":
            f"Request rate ({features['request_rate']:.1f} req/s) from {source_ip} exceeds normal threshold. "
            f"May indicate automated tool usage or compromised account.",
    }
    
    return descriptions.get(
        anomaly_type,
        f"Anomalous activity detected from {source_ip} targeting {destination}. "
        f"ML analysis flagged behavior as suspicious based on multiple indicators."
    )


def generate_recommendation(severity: str, anomaly_type: str) -> str:
    """Generate recommended action based on severity and anomaly type."""
    
    if severity == "Critical":
        return (
            "IMMEDIATE ACTION REQUIRED: 1) Block source IP at firewall level. "
            "2) Disable affected user accounts. 3) Initiate incident response protocol. "
            "4) Preserve all logs for forensic analysis. 5) Notify security team lead."
        )
    
    elif severity == "High":
        return (
            "URGENT: 1) Review affected user accounts for compromise. "
            "2) Consider temporary IP block pending investigation. "
            "3) Audit recent access logs for lateral movement. "
            "4) Escalate to security team if pattern persists."
        )
    
    elif severity == "Medium":
        return (
            "INVESTIGATE: 1) Review user activity for last 24 hours. "
            "2) Contact user to verify legitimate access. "
            "3) Monitor for repeated occurrences. "
            "4) Document findings in incident notes."
        )
    
    else:  # Low
        return (
            "MONITOR: 1) Log incident for trend analysis. "
            "2) No immediate action required. "
            "3) Review if similar patterns recur. "
            "4) May be false positive - validate with user if convenient."
        )


def create_incident_from_log(db: Session, log: Log, ml_result: dict) -> Incident:
    """
    Create an incident from a log entry and ML analysis result.
    
    Args:
        db: Database session
        log: Source log entry
        ml_result: ML analysis result dictionary
        
    Returns:
        Created Incident object
    """
    # Generate description
    description = generate_description(
        ml_result["anomaly_type"],
        ml_result["features"],
        log.source_ip or "Unknown",
        log.destination or "Unknown"
    )
    
    # Generate recommendation
    recommendation = generate_recommendation(
        ml_result["severity"],
        ml_result["anomaly_type"]
    )
    
    # Create incident
    incident = Incident(
        severity=ml_result["severity"],
        status="Detected",
        timestamp=datetime.utcnow(),
        source_ip=log.source_ip,
        destination=log.destination,
        description=description,
        anomaly_type=ml_result["anomaly_type"],
        confidence_score=ml_result["confidence_score"],
        recommended_action=recommendation,
        log_id=log.id
    )
    
    db.add(incident)
    db.commit()
    db.refresh(incident)
    
    # Add initial action
    initial_action = IncidentAction(
        incident_id=incident.id,
        action_text="Alert generated and sent to SOC team",
        timestamp=datetime.utcnow()
    )
    db.add(initial_action)
    db.commit()
    
    api_logger.info(f"Created incident #{incident.id} with severity {incident.severity}")
    
    return incident


def get_incident_list(db: Session) -> List[dict]:
    """
    Get list of incidents formatted for frontend.
    
    Returns list matching the frontend data contract:
    [{incident_id, severity, status, timestamp}, ...]
    """
    incidents = db.query(Incident).order_by(Incident.timestamp.desc()).all()
    
    return [
        {
            "incident_id": inc.id,
            "severity": inc.severity,
            "status": inc.status,
            "timestamp": inc.timestamp.strftime("%Y-%m-%d %H:%M")
        }
        for inc in incidents
    ]


def get_incident_details(db: Session, incident_id: int) -> Optional[dict]:
    """
    Get incident details formatted for frontend.
    
    Returns dict matching the frontend data contract.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if not incident:
        return None
    
    # Get actions
    actions = [action.action_text for action in incident.actions]
    
    return {
        "incident_id": incident.id,
        "severity": incident.severity,
        "status": incident.status,
        "timestamp": incident.timestamp.strftime("%Y-%m-%d %H:%M"),
        "source_ip": incident.source_ip or "Unknown",
        "destination": incident.destination or "Unknown",
        "description": incident.description,
        "anomaly_type": incident.anomaly_type,
        "confidence_score": incident.confidence_score,
        "actions_taken": actions,
        "recommended_action": incident.recommended_action
    }


def update_incident_status(db: Session, incident_id: int, status: str) -> Optional[Incident]:
    """Update incident status."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    
    if incident:
        incident.status = status
        db.commit()
        db.refresh(incident)
    
    return incident
