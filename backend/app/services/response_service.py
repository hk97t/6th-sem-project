"""
Response Service - Handles automated incident response actions.

Severity → Action mapping:
- Low: Log only
- Medium: Alert
- High: Block IP (simulated)
- Critical: Block IP + disable user (simulated)
"""
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from app.db.models import Incident, IncidentAction, AuditLog
from app.utils.logger import security_logger


def execute_response(db: Session, incident: Incident, user_id: int = None) -> List[str]:
    """
    Execute automated response based on incident severity.
    
    Args:
        db: Database session
        incident: Incident to respond to
        user_id: ID of user triggering the response
        
    Returns:
        List of actions taken
    """
    actions_taken = []
    
    if incident.severity == "Low":
        actions_taken = execute_low_severity_response(db, incident)
    elif incident.severity == "Medium":
        actions_taken = execute_medium_severity_response(db, incident)
    elif incident.severity == "High":
        actions_taken = execute_high_severity_response(db, incident)
    elif incident.severity == "Critical":
        actions_taken = execute_critical_severity_response(db, incident)
    
    # Update incident status
    incident.status = "Response Initiated"
    
    # Record actions in database
    for action_text in actions_taken:
        action = IncidentAction(
            incident_id=incident.id,
            action_text=action_text,
            timestamp=datetime.utcnow()
        )
        db.add(action)
    
    # Create audit log
    audit = AuditLog(
        user_id=user_id,
        action="trigger_response",
        target_type="incident",
        target_id=incident.id,
        details=f"Response triggered for {incident.severity} severity incident. Actions: {', '.join(actions_taken)}",
        timestamp=datetime.utcnow()
    )
    db.add(audit)
    
    db.commit()
    
    security_logger.info(f"Response executed for incident #{incident.id}: {actions_taken}")
    
    return actions_taken


def execute_low_severity_response(db: Session, incident: Incident) -> List[str]:
    """Handle low severity incidents - logging only."""
    security_logger.info(f"Low severity response for incident #{incident.id}")
    
    actions = [
        "Incident logged for trend analysis",
        "No immediate action required",
        "Added to monitoring queue"
    ]
    
    return actions


def execute_medium_severity_response(db: Session, incident: Incident) -> List[str]:
    """Handle medium severity incidents - alert generation."""
    security_logger.warning(f"Medium severity response for incident #{incident.id}")
    
    # Simulate sending alert
    simulate_send_alert(incident)
    
    actions = [
        "Alert sent to security team",
        "User activity flagged for review",
        "24-hour monitoring enabled"
    ]
    
    return actions


def execute_high_severity_response(db: Session, incident: Incident) -> List[str]:
    """Handle high severity incidents - IP blocking."""
    security_logger.warning(f"High severity response for incident #{incident.id}")
    
    # Simulate blocking IP
    if incident.source_ip:
        simulate_block_ip(incident.source_ip)
    
    # Simulate sending alert
    simulate_send_alert(incident, priority="high")
    
    actions = [
        f"Source IP {incident.source_ip or 'Unknown'} blocked at firewall",
        "High priority alert sent to security team",
        "Session tokens invalidated",
        "Enhanced monitoring activated"
    ]
    
    return actions


def execute_critical_severity_response(db: Session, incident: Incident) -> List[str]:
    """Handle critical severity incidents - full response."""
    security_logger.critical(f"Critical severity response for incident #{incident.id}")
    
    # Simulate blocking IP
    if incident.source_ip:
        simulate_block_ip(incident.source_ip)
    
    # Simulate disabling user
    simulate_disable_user(incident)
    
    # Simulate emergency alert
    simulate_send_alert(incident, priority="critical")
    
    actions = [
        f"Source IP {incident.source_ip or 'Unknown'} blocked at firewall",
        "Affected user account temporarily disabled",
        "All active sessions terminated",
        "Critical alert sent to security team lead",
        "Incident response protocol initiated",
        "Forensic log preservation started"
    ]
    
    return actions


# ============================================
# SIMULATION FUNCTIONS
# These simulate actions that would interact
# with external systems in production
# ============================================

def simulate_block_ip(ip_address: str):
    """
    Simulate blocking an IP address at the firewall.
    
    In production, this would call:
    - AWS Security Groups API
    - Firewall API (iptables, pf, etc.)
    - WAF rules API
    """
    security_logger.info(f"[SIMULATED] Blocking IP: {ip_address}")
    # In production: call firewall API
    # Example: requests.post(f"{FIREWALL_API}/block", json={"ip": ip_address})


def simulate_disable_user(incident: Incident):
    """
    Simulate disabling a user account.
    
    In production, this would call:
    - Identity provider API (Okta, Auth0, AD)
    - Internal user service
    """
    security_logger.info(f"[SIMULATED] Disabling user associated with incident #{incident.id}")
    # In production: call identity provider API
    # Example: requests.post(f"{IDP_API}/users/{user_id}/disable")


def simulate_send_alert(incident: Incident, priority: str = "normal"):
    """
    Simulate sending an alert notification.
    
    In production, this would call:
    - Slack webhook
    - PagerDuty API
    - Email service
    - SMS gateway
    """
    security_logger.info(f"[SIMULATED] Sending {priority} priority alert for incident #{incident.id}")
    # In production: call notification service
    # Example: requests.post(SLACK_WEBHOOK, json={"text": f"Security Alert: {incident.description}"})
