# AI-Driven Cloud Security Incident Detection & Response Platform

A full-stack cybersecurity dashboard that uses Machine Learning to detect anomalies in security logs and automate incident response.

## 🎯 Features

- **JWT Authentication** with role-based access (Admin/Analyst)
- **ML-Powered Anomaly Detection** using Isolation Forest
- **Severity Classification** using Random Forest
- **Automated Incident Response** based on severity levels
- **Real-time Dashboard** with security metrics
- **Incident Management** with detailed views and response actions

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                 │
│            HTML/CSS/JavaScript (Vanilla)                        │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│    ┌──────────────────────────────────────────────────────┐     │
│    │  API Layer: Auth, Logs, Incidents, Dashboard         │     │
│    └──────────────────────────────────────────────────────┘     │
│    ┌────────────────────┐    ┌────────────────────────────┐     │
│    │   ML Pipeline      │    │    Service Layer           │     │
│    │  - Isolation Forest│    │  - Incident Creation       │     │
│    │  - Random Forest   │    │  - Response Execution      │     │
│    └────────────────────┘    └────────────────────────────┘     │
│    ┌──────────────────────────────────────────────────────┐     │
│    │          SQLite Database (SQLAlchemy)                │     │
│    └──────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- pip

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Start the Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

The backend will:
- Initialize the SQLite database
- Train ML models automatically (if not already trained)
- Seed demo data (users and sample incidents)

### 3. Open the Frontend

Open `frontend/index.html` in your browser:

```bash
open frontend/index.html
# or on Linux: xdg-open frontend/index.html
# or just double-click the file
```

### 4. Login

Use demo credentials:
- **Admin**: `admin` / `admin123`
- **Analyst**: `demo` / `demo123`

## 📁 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   │   ├── auth.py       # Login & JWT
│   │   │   ├── logs.py       # Log ingestion
│   │   │   ├── incidents.py  # Incident CRUD
│   │   │   └── dashboard.py  # Dashboard stats
│   │   ├── core/             # Core utilities
│   │   │   ├── config.py     # Configuration
│   │   │   └── security.py   # JWT & auth
│   │   ├── db/               # Database
│   │   │   ├── database.py   # SQLAlchemy setup
│   │   │   └── models.py     # ORM models
│   │   ├── ml/               # Machine Learning
│   │   │   ├── train_models.py
│   │   │   ├── inference.py
│   │   │   └── models/       # Saved models
│   │   ├── services/         # Business logic
│   │   │   ├── incident_service.py
│   │   │   └── response_service.py
│   │   ├── utils/
│   │   │   └── logger.py
│   │   └── main.py           # FastAPI app
│   └── requirements.txt
│
├── frontend/
│   ├── index.html            # Login page
│   ├── dashboard.html        # Dashboard
│   ├── incidents.html        # Incident list
│   ├── incident_details.html # Incident details
│   ├── style.css             # Styling
│   └── app.js                # Frontend logic
│
└── README.md
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | User login, returns JWT |
| GET | `/api/dashboard/stats` | Dashboard metrics |
| GET | `/api/incidents` | List all incidents |
| GET | `/api/incidents/{id}` | Incident details |
| POST | `/api/incidents/{id}/respond` | Trigger response |
| POST | `/api/logs` | Ingest security log |

## 🤖 ML Pipeline

### Anomaly Detection (Isolation Forest)
- Trained on synthetic normal behavior patterns
- Detects unusual patterns in security logs
- Features: failed attempts, data transfer, request rate, time, geo

### Severity Classification (Random Forest)
- Classifies detected anomalies into: Low, Medium, High, Critical
- Based on feature patterns from the log data

### Training
Models are trained automatically on first run using synthetic data that simulates:
- Normal user behavior
- Brute force attacks
- Data exfiltration
- API abuse
- Privilege escalation

## 🚨 Automated Response

| Severity | Actions |
|----------|---------|
| Low | Log only |
| Medium | Alert security team |
| High | Block IP + High priority alert |
| Critical | Block IP + Disable user + Forensics |

*Note: Response actions are simulated in this demo version.*

## 🔒 Security Features

- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control
- Audit logging for all actions

## 📊 Demo Mode

The system comes pre-seeded with:
- 2 demo users (admin and analyst)
- 10 sample security incidents
- 1000+ log entries
- Pre-trained ML models

This allows for immediate demonstration without real data.

## 🎓 For Viva/Presentation

Key points to explain:

1. **Login Flow**: JWT authentication with token storage
2. **Dashboard**: Real-time metrics from database
3. **ML Pipeline**: Feature extraction → Anomaly detection → Severity classification
4. **Incident Response**: Automated actions based on severity
5. **Architecture**: Clean separation of concerns (API, Services, ML, DB)

## 📝 License

MIT License - Free for educational and commercial use.
