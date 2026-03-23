"""
Cloud Security Platform - Main FastAPI Application

This is the entry point for the backend API server.
Run with: uvicorn app.main:app --reload --port 8000
"""
import random
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import CORS_ORIGINS, API_PREFIX
from app.core.security import get_password_hash
from app.db.database import init_db, SessionLocal
from app.db.models import User, Log, Incident, IncidentAction
from app.api import auth, logs, incidents, dashboard
from app.utils.logger import api_logger


def seed_demo_data():
    """
    Seed the database with demo users and sample incidents.
    This creates a demo-ready environment for presentations.
    """
    db = SessionLocal()
    
    try:
        # Check if data already exists
        if db.query(User).count() > 0:
            api_logger.info("Database already seeded, skipping")
            return
        
        api_logger.info("Seeding demo data...")
        
        # Create demo users
        users = [
            User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                name="Admin User",
                role="admin",
                is_active=True
            ),
            User(
                username="demo",
                hashed_password=get_password_hash("demo123"),
                name="Demo User",
                role="analyst",
                is_active=True
            )
        ]
        
        for user in users:
            db.add(user)
        db.commit()
        
        # Create sample logs
        log_templates = [
            {"source_ip": "192.168.1.105", "destination": "Production Database Server", "event_type": "auth_failure"},
            {"source_ip": "10.0.0.55", "destination": "AWS S3 Bucket", "event_type": "data_transfer"},
            {"source_ip": "203.0.113.50", "destination": "Web Application Firewall", "event_type": "sql_injection"},
            {"source_ip": "172.16.0.23", "destination": "Internal API Gateway", "event_type": "api_request"},
            {"source_ip": "192.168.50.12", "destination": "Active Directory", "event_type": "privilege_escalation"},
        ]
        
        for i, template in enumerate(log_templates):
            log = Log(
                timestamp=datetime.utcnow(),
                source_ip=template["source_ip"],
                destination=template["destination"],
                event_type=template["event_type"],
                is_processed=True,
                anomaly_score=random.uniform(60, 99)
            )
            db.add(log)
        db.commit()
        
        # Create sample incidents matching the frontend mock data structure
        sample_incidents = [
            {
                "severity": "Critical",
                "status": "Detected",
                "source_ip": "192.168.1.105",
                "destination": "Production Database Server",
                "description": "Multiple failed authentication attempts detected followed by successful login from an unrecognized IP address. Potential brute force attack with account compromise.",
                "anomaly_type": "Brute Force Attack",
                "confidence_score": 94.5,
                "recommended_action": "Verify user identity through secondary channel. If unauthorized, reset credentials and audit all recent account activity.",
                "actions": ["Alert generated and sent to SOC team", "Account temporarily locked", "Session tokens invalidated"]
            },
            {
                "severity": "High",
                "status": "Investigating",
                "source_ip": "10.0.0.55",
                "destination": "AWS S3 Bucket",
                "description": "Unusual data exfiltration pattern detected. Large volume of data being transferred to external endpoint outside business hours.",
                "anomaly_type": "Data Exfiltration",
                "confidence_score": 87.2,
                "recommended_action": "Block outbound traffic to suspicious endpoint. Review access logs and identify data accessed.",
                "actions": ["Alert generated and sent to SOC team", "Network traffic logged for analysis"]
            },
            {
                "severity": "Critical",
                "status": "Detected",
                "source_ip": "203.0.113.50",
                "destination": "Web Application Firewall",
                "description": "SQL injection attempts detected on login form. Multiple payloads attempting to bypass authentication.",
                "anomaly_type": "SQL Injection Attack",
                "confidence_score": 98.1,
                "recommended_action": "Review and patch application code. Conduct security audit of all input fields.",
                "actions": ["WAF rule triggered - requests blocked", "Source IP added to blocklist"]
            },
            {
                "severity": "Medium",
                "status": "Mitigated",
                "source_ip": "172.16.0.23",
                "destination": "Internal API Gateway",
                "description": "Abnormal API usage pattern detected. Single user making excessive requests outside normal usage profile.",
                "anomaly_type": "API Abuse",
                "confidence_score": 72.8,
                "recommended_action": "Monitor user activity. Consider implementing stricter rate limits if behavior continues.",
                "actions": ["Rate limiting applied to user", "User notified of policy violation", "Incident logged for compliance"]
            },
            {
                "severity": "High",
                "status": "Detected",
                "source_ip": "192.168.50.12",
                "destination": "Active Directory",
                "description": "Privilege escalation attempt detected. Standard user account attempting to access admin-level resources.",
                "anomaly_type": "Privilege Escalation",
                "confidence_score": 89.3,
                "recommended_action": "Investigate user workstation for malware. Review user permissions and recent activity.",
                "actions": ["Access attempt denied", "Alert sent to security team"]
            },
            {
                "severity": "Low",
                "status": "Resolved",
                "source_ip": "10.10.10.5",
                "destination": "File Server",
                "description": "Unusual file access pattern detected during maintenance window. Confirmed as authorized maintenance activity.",
                "anomaly_type": "Anomalous File Access",
                "confidence_score": 45.6,
                "recommended_action": "No further action required. Incident closed.",
                "actions": ["Activity verified with IT operations", "Marked as false positive", "Detection model updated"]
            },
            {
                "severity": "High",
                "status": "Investigating",
                "source_ip": "Unknown",
                "destination": "Email Gateway",
                "description": "Phishing campaign detected targeting executive accounts. Multiple employees received sophisticated spear-phishing emails.",
                "anomaly_type": "Phishing Attack",
                "confidence_score": 91.7,
                "recommended_action": "Conduct security awareness training. Monitor for any credential compromise.",
                "actions": ["Malicious emails quarantined", "Users notified of threat", "Email filters updated"]
            },
            {
                "severity": "Critical",
                "status": "Detected",
                "source_ip": "203.0.113.50",
                "destination": "Cloud Infrastructure",
                "description": "Unauthorized cloud resource provisioning detected. New compute instances created outside change management process.",
                "anomaly_type": "Unauthorized Resource Creation",
                "confidence_score": 96.4,
                "recommended_action": "Terminate unauthorized resources. Review and revoke compromised credentials. Audit cloud access policies.",
                "actions": ["New resources flagged for review", "Cloud admin team notified"]
            },
            {
                "severity": "Medium",
                "status": "Resolved",
                "source_ip": "192.168.1.200",
                "destination": "VPN Gateway",
                "description": "Multiple VPN connection attempts from unusual geographic location. User traveling - confirmed legitimate access.",
                "anomaly_type": "Geographic Anomaly",
                "confidence_score": 68.2,
                "recommended_action": "No further action required. Consider implementing travel notification system.",
                "actions": ["User contacted for verification", "Access confirmed legitimate", "Travel recorded in system"]
            },
            {
                "severity": "Low",
                "status": "Resolved",
                "source_ip": "10.0.0.15",
                "destination": "Development Server",
                "description": "Port scanning activity detected from developer workstation. Confirmed as authorized penetration testing.",
                "anomaly_type": "Port Scanning",
                "confidence_score": 52.1,
                "recommended_action": "No further action required. Ensure pen testing is properly documented.",
                "actions": ["Activity verified with security team", "Confirmed authorized testing", "Incident closed"]
            }
        ]
        
        # Create incidents with staggered timestamps
        base_time = datetime.utcnow()
        for i, inc_data in enumerate(sample_incidents):
            # Stagger timestamps by hours
            hours = 14 - i
            minutes = (60 - (i * 7)) % 60  # Ensure valid minute range
            timestamp = datetime(2026, 2, 1, max(8, hours), minutes)
            
            incident = Incident(
                severity=inc_data["severity"],
                status=inc_data["status"],
                timestamp=timestamp,
                source_ip=inc_data["source_ip"],
                destination=inc_data["destination"],
                description=inc_data["description"],
                anomaly_type=inc_data["anomaly_type"],
                confidence_score=inc_data["confidence_score"],
                recommended_action=inc_data["recommended_action"]
            )
            db.add(incident)
            db.commit()
            db.refresh(incident)
            
            # Add actions
            for action_text in inc_data["actions"]:
                action = IncidentAction(
                    incident_id=incident.id,
                    action_text=action_text,
                    timestamp=timestamp
                )
                db.add(action)
        
        # Seed log count to show realistic numbers
        # Add dummy log entries to get a high count
        for i in range(1000):
            log = Log(
                timestamp=datetime.utcnow(),
                source_ip=f"10.0.{random.randint(0,255)}.{random.randint(1,254)}",
                destination="Various Systems",
                event_type="normal_activity",
                is_processed=True,
                anomaly_score=random.uniform(0, 30)
            )
            db.add(log)
        
        db.commit()
        api_logger.info("Demo data seeded successfully")
        
    except Exception as e:
        api_logger.error(f"Error seeding demo data: {e}")
        db.rollback()
    finally:
        db.close()


def train_models_if_needed():
    """Train ML models if they don't exist."""
    import os
    from app.core.config import ML_MODELS_PATH
    
    if not os.path.exists(os.path.join(ML_MODELS_PATH, "isolation_forest.pkl")):
        api_logger.info("ML models not found, training...")
        from app.ml.train_models import train_all_models
        train_all_models()
    else:
        api_logger.info("ML models already exist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    api_logger.info("Starting Cloud Security Platform API...")
    init_db()
    train_models_if_needed()
    seed_demo_data()
    api_logger.info("API server started successfully")
    
    yield
    
    # Shutdown
    api_logger.info("Shutting down Cloud Security Platform API...")


# Create FastAPI application
app = FastAPI(
    title="Cloud Security Platform API",
    description="AI-Driven Cloud Security Incident Detection & Response Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(logs.router, prefix=API_PREFIX)
app.include_router(incidents.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "name": "Cloud Security Platform API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Run with: uvicorn app.main:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
