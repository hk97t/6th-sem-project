"""
CSV Upload API endpoint — Wireshark CSV import.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.core.security import get_current_user
from app.services.csv_service import process_wireshark_import
from app.utils.logger import api_logger

router = APIRouter(prefix="/csv", tags=["CSV Import"])


class SourceDetail(BaseModel):
    """Per-source analysis detail."""
    source_ip: str
    destination: str
    packet_count: int
    bytes_transferred: int
    anomaly_detected: bool
    incident_id: Optional[int] = None


class CsvUploadResponse(BaseModel):
    """Response for CSV upload."""
    success: bool
    message: str
    total_packets: int
    sources_analyzed: int
    incidents_created: int
    incident_ids: List[int] = []
    source_details: List[SourceDetail] = []


@router.post("/upload", response_model=CsvUploadResponse)
async def upload_wireshark_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a Wireshark CSV export for ML analysis.

    Accepts the standard Wireshark "Export Packet Dissections as CSV" format.
    Processes each unique source IP through the anomaly detection pipeline
    and creates incidents for any detected anomalies.

    Returns a summary of the analysis.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided.",
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are accepted. Please upload a Wireshark CSV export.",
        )

    api_logger.info(
        f"CSV upload received: '{file.filename}' by user {current_user['username']}"
    )

    # Read file contents
    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}",
        )

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Size limit — 10 MB
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 10 MB.",
        )

    # Process
    try:
        result = process_wireshark_import(db, contents)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        api_logger.error(f"CSV processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}",
        )

    msg = (
        f"Analyzed {result['total_packets']} packets from "
        f"{result['sources_analyzed']} sources. "
        f"{result['incidents_created']} incident(s) created."
    )

    return CsvUploadResponse(
        success=True,
        message=msg,
        total_packets=result["total_packets"],
        sources_analyzed=result["sources_analyzed"],
        incidents_created=result["incidents_created"],
        incident_ids=result["incident_ids"],
        source_details=result["source_details"],
    )
