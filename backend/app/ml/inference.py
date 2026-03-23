"""
ML Inference for Cloud Security Platform.

This module provides inference functions for:
1. Anomaly detection using Isolation Forest
2. Severity classification using Random Forest
"""
import os
import pickle
import numpy as np
from typing import Tuple, Optional

from app.utils.logger import ml_logger

# Path to saved models
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

# Global model cache
_anomaly_model = None
_anomaly_scaler = None
_severity_model = None
_severity_scaler = None

# Severity mapping
SEVERITY_MAP = {0: "Low", 1: "Medium", 2: "High", 3: "Critical"}


def load_models():
    """Load trained models from disk."""
    global _anomaly_model, _anomaly_scaler, _severity_model, _severity_scaler
    
    if _anomaly_model is not None:
        return  # Already loaded
    
    try:
        ml_logger.info("Loading ML models...")
        
        with open(os.path.join(MODELS_DIR, "isolation_forest.pkl"), "rb") as f:
            _anomaly_model = pickle.load(f)
        
        with open(os.path.join(MODELS_DIR, "anomaly_scaler.pkl"), "rb") as f:
            _anomaly_scaler = pickle.load(f)
        
        with open(os.path.join(MODELS_DIR, "random_forest.pkl"), "rb") as f:
            _severity_model = pickle.load(f)
        
        with open(os.path.join(MODELS_DIR, "severity_scaler.pkl"), "rb") as f:
            _severity_scaler = pickle.load(f)
        
        ml_logger.info("ML models loaded successfully")
        
    except FileNotFoundError as e:
        ml_logger.warning(f"ML models not found: {e}")
        ml_logger.warning("Run train_models.py first to train the models")
        raise


def extract_features(log_data: dict) -> np.ndarray:
    """
    Extract ML features from a log entry.
    
    Args:
        log_data: Dictionary containing log information
        
    Returns:
        Feature vector as numpy array
    """
    features = np.array([
        log_data.get("failed_attempts", 0),
        log_data.get("bytes_transferred", 0),
        log_data.get("request_rate", 0.0),
        1 if log_data.get("unusual_time", False) else 0,
        1 if log_data.get("geo_anomaly", False) else 0,
    ]).reshape(1, -1)
    
    return features


def detect_anomaly(features: np.ndarray) -> Tuple[bool, float]:
    """
    Detect if the given features represent an anomaly.
    
    Args:
        features: Feature vector (1 x n_features)
        
    Returns:
        is_anomaly: Boolean indicating if anomaly detected
        anomaly_score: Anomaly score (lower = more anomalous)
    """
    load_models()
    
    # Scale features
    features_scaled = _anomaly_scaler.transform(features)
    
    # Get prediction (-1 = anomaly, 1 = normal)
    prediction = _anomaly_model.predict(features_scaled)[0]
    
    # Get anomaly score (negative = more anomalous)
    score = _anomaly_model.score_samples(features_scaled)[0]
    
    # Convert score to 0-100 confidence (inverted and normalized)
    # Typical scores range from -0.5 (very anomalous) to 0.1 (normal)
    confidence = max(0, min(100, (1 - score) * 100))
    
    is_anomaly = prediction == -1
    
    ml_logger.info(f"Anomaly detection: is_anomaly={is_anomaly}, score={score:.4f}, confidence={confidence:.1f}%")
    
    return is_anomaly, confidence


def classify_severity(features: np.ndarray) -> Tuple[str, float]:
    """
    Classify the severity of an anomaly.
    
    Args:
        features: Feature vector (1 x n_features)
        
    Returns:
        severity: Severity label (Low, Medium, High, Critical)
        confidence: Classification confidence (0-100)
    """
    load_models()
    
    # Scale features
    features_scaled = _severity_scaler.transform(features)
    
    # Get prediction
    prediction = _severity_model.predict(features_scaled)[0]
    
    # Get prediction probabilities
    probabilities = _severity_model.predict_proba(features_scaled)[0]
    confidence = probabilities[prediction] * 100
    
    severity = SEVERITY_MAP.get(prediction, "Medium")
    
    ml_logger.info(f"Severity classification: severity={severity}, confidence={confidence:.1f}%")
    
    return severity, confidence


def analyze_log(log_data: dict) -> Optional[dict]:
    """
    Full ML analysis pipeline for a log entry.
    
    Args:
        log_data: Dictionary containing log information
        
    Returns:
        Analysis result dict if anomaly detected, None otherwise
    """
    try:
        # Extract features
        features = extract_features(log_data)
        
        # Detect anomaly
        is_anomaly, anomaly_confidence = detect_anomaly(features)
        
        if not is_anomaly:
            ml_logger.info("Log analyzed: No anomaly detected")
            return None
        
        # Classify severity
        severity, severity_confidence = classify_severity(features)
        
        # Determine anomaly type based on features
        anomaly_type = determine_anomaly_type(log_data)
        
        # Calculate combined confidence
        combined_confidence = (anomaly_confidence + severity_confidence) / 2
        
        result = {
            "is_anomaly": True,
            "severity": severity,
            "confidence_score": round(combined_confidence, 1),
            "anomaly_type": anomaly_type,
            "features": {
                "failed_attempts": log_data.get("failed_attempts", 0),
                "bytes_transferred": log_data.get("bytes_transferred", 0),
                "request_rate": log_data.get("request_rate", 0.0),
                "unusual_time": log_data.get("unusual_time", False),
                "geo_anomaly": log_data.get("geo_anomaly", False),
            }
        }
        
        ml_logger.info(f"Anomaly detected: {result}")
        return result
        
    except Exception as e:
        ml_logger.error(f"Error analyzing log: {e}")
        raise


def determine_anomaly_type(log_data: dict) -> str:
    """
    Determine the type of anomaly based on feature patterns.
    
    Args:
        log_data: Dictionary containing log information
        
    Returns:
        Human-readable anomaly type string
    """
    failed = log_data.get("failed_attempts", 0)
    bytes_tx = log_data.get("bytes_transferred", 0)
    rate = log_data.get("request_rate", 0.0)
    unusual_time = log_data.get("unusual_time", False)
    geo_anomaly = log_data.get("geo_anomaly", False)
    
    # Determine primary anomaly type based on dominant features
    if failed > 15 and bytes_tx > 100000:
        return "Brute Force Attack with Data Exfiltration"
    elif failed > 15:
        return "Brute Force Attack"
    elif bytes_tx > 200000:
        return "Data Exfiltration"
    elif rate > 30:
        return "API Abuse / DDoS Attempt"
    elif geo_anomaly and unusual_time:
        return "Suspicious Remote Access"
    elif geo_anomaly:
        return "Geographic Anomaly"
    elif unusual_time:
        return "Off-Hours Activity"
    elif rate > 15:
        return "Elevated Request Rate"
    else:
        return "Anomalous Activity Pattern"
