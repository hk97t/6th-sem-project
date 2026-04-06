"""
CSV Service — Parse Wireshark CSV exports and run through ML pipeline.

Handles the default Wireshark "Export Packet Dissections as CSV" format:
  No., Time, Source, Destination, Protocol, Length, Info
"""
import csv
import io
from collections import defaultdict
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import Log, Incident
from app.ml.inference import analyze_log
from app.services.incident_service import create_incident_from_log
from app.utils.logger import api_logger


# ── Wireshark CSV column names (case-insensitive matching) ─────
EXPECTED_COLUMNS = {"no.", "time", "source", "destination", "protocol", "length", "info"}

# Keywords that hint at auth-failure packets
AUTH_FAILURE_KEYWORDS = [
    "auth fail", "authentication failed", "login fail", "access denied",
    "401", "403", "bad password", "invalid credentials", "rejected",
    "denied", "retransmission",
]

# Protocols that typically carry auth traffic
AUTH_PROTOCOLS = {"kerberos", "ldap", "smb", "smb2", "ntlmssp", "radius", "ssh", "telnet"}

# Business hours range (used for unusual_time detection)
BUSINESS_HOUR_START = 9
BUSINESS_HOUR_END = 18


def parse_wireshark_csv(file_content: bytes) -> list[dict]:
    """
    Parse a Wireshark CSV export into a list of row dicts.

    Args:
        file_content: Raw CSV file bytes

    Returns:
        List of dicts with keys: no, time, source, destination, protocol, length, info

    Raises:
        ValueError: If the CSV format is invalid or missing required columns
    """
    try:
        text = file_content.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        text = file_content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise ValueError("CSV file is empty or has no header row.")

    # Normalize field names for matching
    normalized = {f.strip().strip('"').lower(): f for f in reader.fieldnames}
    missing = EXPECTED_COLUMNS - set(normalized.keys())

    if missing:
        # Be lenient — only require source, destination, length at minimum
        required = {"source", "destination", "length"}
        truly_missing = required - set(normalized.keys())
        if truly_missing:
            raise ValueError(
                f"CSV is missing required columns: {', '.join(truly_missing)}. "
                f"Expected Wireshark default CSV format with columns: {', '.join(EXPECTED_COLUMNS)}"
            )

    rows = []
    for raw_row in reader:
        # Build normalized row
        row = {}
        for key, original_key in normalized.items():
            row[key] = (raw_row.get(original_key) or "").strip().strip('"')

        # Parse length to int
        try:
            row["length"] = int(row.get("length", "0"))
        except (ValueError, TypeError):
            row["length"] = 0

        rows.append(row)

    if not rows:
        raise ValueError("CSV file contains headers but no data rows.")

    api_logger.info(f"Parsed {len(rows)} packets from Wireshark CSV")
    return rows


def _is_private_ip(ip: str) -> bool:
    """Check if an IP belongs to private RFC1918 ranges."""
    if not ip:
        return False
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        octets = [int(p) for p in parts]
    except ValueError:
        return False

    # 10.0.0.0/8
    if octets[0] == 10:
        return True
    # 172.16.0.0/12
    if octets[0] == 172 and 16 <= octets[1] <= 31:
        return True
    # 192.168.0.0/16
    if octets[0] == 192 and octets[1] == 168:
        return True
    # Loopback
    if octets[0] == 127:
        return True

    return False


def _detect_unusual_time(time_str: str) -> bool:
    """Check if packet timestamp is outside business hours."""
    if not time_str:
        return False

    # Wireshark time can be relative (e.g. "0.000000") or absolute
    # Try parsing absolute format first
    for fmt in ["%b %d, %Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%H:%M:%S"]:
        try:
            dt = datetime.strptime(time_str.split(".")[0], fmt)
            return dt.hour < BUSINESS_HOUR_START or dt.hour >= BUSINESS_HOUR_END
        except ValueError:
            continue

    return False


def _has_auth_failure(info: str, protocol: str) -> bool:
    """Check if packet info suggests an authentication failure."""
    info_lower = (info or "").lower()
    proto_lower = (protocol or "").lower()

    # Check info field for failure keywords
    for kw in AUTH_FAILURE_KEYWORDS:
        if kw in info_lower:
            return True

    # Auth protocol with RST or error
    if proto_lower in AUTH_PROTOCOLS and any(
        w in info_lower for w in ["error", "fail", "reject", "reset", "rst"]
    ):
        return True

    return False


def aggregate_features(rows: list[dict]) -> list[dict]:
    """
    Aggregate raw Wireshark packet rows into per-source-IP feature sets
    suitable for the ML pipeline.

    Features extracted:
    - failed_attempts: count of packets with auth failure indicators
    - bytes_transferred: total bytes (sum of Length)
    - request_rate: packets per second (approx)
    - unusual_time: any packet outside business hours
    - geo_anomaly: source is a public (non-RFC1918) IP

    Args:
        rows: List of parsed CSV row dicts

    Returns:
        List of feature dicts, one per unique source IP
    """
    sources: dict[str, dict] = defaultdict(lambda: {
        "failed_attempts": 0,
        "bytes_transferred": 0,
        "packet_count": 0,
        "unusual_time": False,
        "geo_anomaly": False,
        "destinations": set(),
        "first_time": None,
        "last_time": None,
    })

    for row in rows:
        src = row.get("source", "").strip()
        if not src:
            continue

        data = sources[src]
        data["packet_count"] += 1
        data["bytes_transferred"] += row.get("length", 0)

        # Auth failure detection
        if _has_auth_failure(row.get("info", ""), row.get("protocol", "")):
            data["failed_attempts"] += 1

        # Unusual time
        if _detect_unusual_time(row.get("time", "")):
            data["unusual_time"] = True

        # Geo anomaly (public IP)
        if not _is_private_ip(src):
            data["geo_anomaly"] = True

        # Track destinations
        dst = row.get("destination", "")
        if dst:
            data["destinations"].add(dst)

        # Track time range (using relative time as float seconds)
        time_str = row.get("time", "")
        try:
            t = float(time_str)
            if data["first_time"] is None or t < data["first_time"]:
                data["first_time"] = t
            if data["last_time"] is None or t > data["last_time"]:
                data["last_time"] = t
        except (ValueError, TypeError):
            pass

    # Build feature list
    features = []
    for src_ip, data in sources.items():
        # Calculate request rate (packets per second)
        duration = 1.0  # default 1 second to avoid division by zero
        if data["first_time"] is not None and data["last_time"] is not None:
            d = data["last_time"] - data["first_time"]
            if d > 0:
                duration = d
        request_rate = data["packet_count"] / duration

        # Pick primary destination (most common would be better, but set → first)
        primary_dst = next(iter(data["destinations"]), "Unknown")

        features.append({
            "source_ip": src_ip,
            "destination": primary_dst,
            "failed_attempts": data["failed_attempts"],
            "bytes_transferred": data["bytes_transferred"],
            "request_rate": round(request_rate, 2),
            "unusual_time": data["unusual_time"],
            "geo_anomaly": data["geo_anomaly"],
            "packet_count": data["packet_count"],
        })

    api_logger.info(f"Aggregated features for {len(features)} unique source IPs")
    return features


def process_wireshark_import(db: Session, file_content: bytes) -> dict:
    """
    Full pipeline: parse CSV → aggregate features → ML analysis → create incidents.

    Args:
        db: Database session
        file_content: Raw CSV file bytes

    Returns:
        Summary dict with keys:
        - total_packets: int
        - sources_analyzed: int
        - incidents_created: int
        - incident_ids: list[int]
        - source_details: list[dict] — per-source summary
    """
    # 1. Parse
    rows = parse_wireshark_csv(file_content)

    # 2. Aggregate
    feature_sets = aggregate_features(rows)

    # 3. Run ML + create incidents
    incidents_created = 0
    incident_ids = []
    source_details = []

    for feat in feature_sets:
        ml_input = {
            "failed_attempts": feat["failed_attempts"],
            "bytes_transferred": feat["bytes_transferred"],
            "request_rate": feat["request_rate"],
            "unusual_time": feat["unusual_time"],
            "geo_anomaly": feat["geo_anomaly"],
        }

        detail = {
            "source_ip": feat["source_ip"],
            "destination": feat["destination"],
            "packet_count": feat["packet_count"],
            "bytes_transferred": feat["bytes_transferred"],
            "anomaly_detected": False,
            "incident_id": None,
        }

        try:
            ml_result = analyze_log(ml_input)

            if ml_result and ml_result.get("is_anomaly"):
                # Create a log entry first (source for the incident)
                log = Log(
                    timestamp=datetime.utcnow(),
                    source_ip=feat["source_ip"],
                    destination=feat["destination"],
                    event_type="wireshark_import",
                    raw_data=f"Wireshark CSV import — {feat['packet_count']} packets",
                    is_processed=True,
                    anomaly_score=ml_result.get("confidence_score", 0),
                    failed_attempts=feat["failed_attempts"],
                    bytes_transferred=feat["bytes_transferred"],
                    request_rate=feat["request_rate"],
                    unusual_time=feat["unusual_time"],
                    geo_anomaly=feat["geo_anomaly"],
                )
                db.add(log)
                db.commit()
                db.refresh(log)

                # Create incident
                incident = create_incident_from_log(db, log, ml_result)
                incidents_created += 1
                incident_ids.append(incident.id)

                detail["anomaly_detected"] = True
                detail["incident_id"] = incident.id

        except Exception as e:
            api_logger.error(f"ML analysis failed for source {feat['source_ip']}: {e}")

        source_details.append(detail)

    summary = {
        "total_packets": len(rows),
        "sources_analyzed": len(feature_sets),
        "incidents_created": incidents_created,
        "incident_ids": incident_ids,
        "source_details": source_details,
    }

    api_logger.info(
        f"Wireshark import complete: {len(rows)} packets, "
        f"{len(feature_sets)} sources, {incidents_created} incidents created"
    )

    return summary
