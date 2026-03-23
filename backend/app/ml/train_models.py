"""
ML Model Training for Cloud Security Platform.

This module trains two models:
1. Isolation Forest - For anomaly detection
2. Random Forest Classifier - For severity classification

Uses synthetic training data that simulates real security log patterns.
"""
import os
import pickle
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# Path to save models
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")


def generate_synthetic_data(n_normal=1000, n_anomaly=200):
    """
    Generate synthetic security log data for training.
    
    Features:
    - failed_attempts: Number of failed login attempts (0-100)
    - bytes_transferred: Data transfer volume (bytes)
    - request_rate: Requests per second
    - unusual_time: Binary flag for off-hours activity
    - geo_anomaly: Binary flag for geographic anomaly
    
    Returns:
        X_normal: Normal behavior samples
        X_anomaly: Anomalous behavior samples
        severity_labels: Severity labels for anomalies
    """
    np.random.seed(42)
    
    # Normal behavior patterns
    X_normal = np.column_stack([
        np.random.poisson(1, n_normal),              # failed_attempts: mostly 0-3
        np.random.exponential(5000, n_normal),       # bytes_transferred: small transfers
        np.random.exponential(2, n_normal),          # request_rate: low rate
        np.random.binomial(1, 0.05, n_normal),       # unusual_time: rarely off-hours
        np.random.binomial(1, 0.02, n_normal),       # geo_anomaly: very rare
    ])
    
    # Anomalous behavior patterns (various attack types)
    anomaly_types = []
    X_anomaly_list = []
    severity_list = []
    
    # Critical: Brute force + data exfiltration
    n_critical = n_anomaly // 4
    X_critical = np.column_stack([
        np.random.randint(20, 100, n_critical),      # Many failed attempts
        np.random.exponential(500000, n_critical),   # Large data transfer
        np.random.exponential(50, n_critical),       # High request rate
        np.random.binomial(1, 0.7, n_critical),      # Often off-hours
        np.random.binomial(1, 0.8, n_critical),      # Geographic anomaly
    ])
    X_anomaly_list.append(X_critical)
    severity_list.extend([3] * n_critical)  # 3 = Critical
    
    # High: Suspicious data transfer
    n_high = n_anomaly // 4
    X_high = np.column_stack([
        np.random.randint(5, 20, n_high),            # Some failed attempts
        np.random.exponential(200000, n_high),       # Large data transfer
        np.random.exponential(30, n_high),           # Elevated request rate
        np.random.binomial(1, 0.5, n_high),          # Sometimes off-hours
        np.random.binomial(1, 0.4, n_high),          # Sometimes geo anomaly
    ])
    X_anomaly_list.append(X_high)
    severity_list.extend([2] * n_high)  # 2 = High
    
    # Medium: Unusual access patterns
    n_medium = n_anomaly // 4
    X_medium = np.column_stack([
        np.random.randint(3, 10, n_medium),          # Few failed attempts
        np.random.exponential(50000, n_medium),      # Moderate data transfer
        np.random.exponential(15, n_medium),         # Somewhat elevated rate
        np.random.binomial(1, 0.3, n_medium),        # Sometimes off-hours
        np.random.binomial(1, 0.2, n_medium),        # Rarely geo anomaly
    ])
    X_anomaly_list.append(X_medium)
    severity_list.extend([1] * n_medium)  # 1 = Medium
    
    # Low: Minor anomalies
    n_low = n_anomaly - n_critical - n_high - n_medium
    X_low = np.column_stack([
        np.random.randint(2, 5, n_low),              # Slightly elevated fails
        np.random.exponential(20000, n_low),         # Slightly elevated transfer
        np.random.exponential(8, n_low),             # Slightly elevated rate
        np.random.binomial(1, 0.15, n_low),          # Rarely off-hours
        np.random.binomial(1, 0.1, n_low),           # Very rarely geo anomaly
    ])
    X_anomaly_list.append(X_low)
    severity_list.extend([0] * n_low)  # 0 = Low
    
    X_anomaly = np.vstack(X_anomaly_list)
    severity_labels = np.array(severity_list)
    
    return X_normal, X_anomaly, severity_labels


def train_anomaly_detector(X_normal, X_anomaly):
    """
    Train Isolation Forest for anomaly detection.
    
    Args:
        X_normal: Normal behavior samples
        X_anomaly: Anomalous behavior samples (for validation)
    
    Returns:
        model: Trained Isolation Forest model
        scaler: Fitted StandardScaler
    """
    print("Training Isolation Forest for anomaly detection...")
    
    # Fit scaler on normal data
    scaler = StandardScaler()
    X_normal_scaled = scaler.fit_transform(X_normal)
    
    # Train Isolation Forest
    # contamination is set low since we train primarily on normal data
    model = IsolationForest(
        n_estimators=100,
        contamination=0.1,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_normal_scaled)
    
    # Validate on both normal and anomaly data
    X_anomaly_scaled = scaler.transform(X_anomaly)
    
    normal_pred = model.predict(X_normal_scaled)
    anomaly_pred = model.predict(X_anomaly_scaled)
    
    # Calculate detection rates
    normal_accuracy = np.mean(normal_pred == 1)  # 1 = normal
    anomaly_detection = np.mean(anomaly_pred == -1)  # -1 = anomaly
    
    print(f"  Normal samples correctly identified: {normal_accuracy:.2%}")
    print(f"  Anomalies correctly detected: {anomaly_detection:.2%}")
    
    return model, scaler


def train_severity_classifier(X_anomaly, severity_labels):
    """
    Train Random Forest for severity classification.
    
    Args:
        X_anomaly: Anomalous behavior samples
        severity_labels: Severity labels (0=Low, 1=Medium, 2=High, 3=Critical)
    
    Returns:
        model: Trained Random Forest classifier
        scaler: Fitted StandardScaler
    """
    print("Training Random Forest for severity classification...")
    
    # Fit scaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_anomaly)
    
    # Train Random Forest
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_scaled, severity_labels)
    
    # Calculate training accuracy
    predictions = model.predict(X_scaled)
    accuracy = np.mean(predictions == severity_labels)
    print(f"  Training accuracy: {accuracy:.2%}")
    
    # Print feature importances
    feature_names = ["failed_attempts", "bytes_transferred", "request_rate", 
                     "unusual_time", "geo_anomaly"]
    importances = model.feature_importances_
    print("  Feature importances:")
    for name, importance in sorted(zip(feature_names, importances), 
                                   key=lambda x: x[1], reverse=True):
        print(f"    {name}: {importance:.3f}")
    
    return model, scaler


def save_models(anomaly_model, anomaly_scaler, 
                severity_model, severity_scaler):
    """Save trained models to disk."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    with open(os.path.join(MODELS_DIR, "isolation_forest.pkl"), "wb") as f:
        pickle.dump(anomaly_model, f)
    
    with open(os.path.join(MODELS_DIR, "anomaly_scaler.pkl"), "wb") as f:
        pickle.dump(anomaly_scaler, f)
    
    with open(os.path.join(MODELS_DIR, "random_forest.pkl"), "wb") as f:
        pickle.dump(severity_model, f)
    
    with open(os.path.join(MODELS_DIR, "severity_scaler.pkl"), "wb") as f:
        pickle.dump(severity_scaler, f)
    
    print(f"\nModels saved to {MODELS_DIR}")


def train_all_models():
    """Train and save all ML models."""
    print("=" * 50)
    print("Cloud Security Platform - ML Model Training")
    print("=" * 50)
    print()
    
    # Generate synthetic training data
    print("Generating synthetic training data...")
    X_normal, X_anomaly, severity_labels = generate_synthetic_data()
    print(f"  Normal samples: {len(X_normal)}")
    print(f"  Anomaly samples: {len(X_anomaly)}")
    print()
    
    # Train anomaly detector
    anomaly_model, anomaly_scaler = train_anomaly_detector(X_normal, X_anomaly)
    print()
    
    # Train severity classifier
    severity_model, severity_scaler = train_severity_classifier(X_anomaly, severity_labels)
    print()
    
    # Save models
    save_models(anomaly_model, anomaly_scaler, severity_model, severity_scaler)
    
    print()
    print("Training complete!")
    print("=" * 50)


if __name__ == "__main__":
    train_all_models()
