"""SQLAlchemy models for Smart Home IDS.

This module defines all database models using SQLAlchemy 2.x.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Text,
    Index,
    BigInteger,
    Enum as SQLEnum,
)
from sqlalchemy.orm import (
    relationship,
    DeclarativeBase,
    Mapped,
    mapped_column,
)

from ids_core.config import Settings


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Device(Base):
    """Device model for tracking IoT devices."""

    __tablename__ = "devices"

    id = mapped_column(String, primary_key=True, index=True)
    mac_address = mapped_column(String, nullable=False, unique=True, index=True)
    ip_address = mapped_column(String, nullable=True, index=True)
    hostname = mapped_column(String, nullable=True)
    device_type = mapped_column(String, nullable=True, index=True)
    vendor = mapped_column(String, nullable=True)
    first_seen = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen_port = mapped_column(Integer, nullable=True)
    connection_count = mapped_column(Integer, default=0)
    total_bytes_up = mapped_column(BigInteger, default=0)
    total_bytes_down = mapped_column(BigInteger, default=0)
    is_trusted = mapped_column(Boolean, default=False, index=True)
    is_blocked = mapped_column(Boolean, default=False, index=True)
    operating_system = mapped_column(String, nullable=True)
    protocols = mapped_column(JSON, default=list)
    confidence_score = mapped_column(Float, default=0.0)
    notes = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    updated_at = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    alerts = relationship("Alert", back_populates="device", cascade="all, delete-orphan")


class FlowRecord(Base):
    """Flow record model for network flows."""

    __tablename__ = "flow_records"

    id = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    flow_id = mapped_column(String, nullable=False, index=True)
    device_id = mapped_column(String, ForeignKey("devices.id"), nullable=False, index=True)
    source_ip = mapped_column(String, nullable=False, index=True)
    destination_ip = mapped_column(String, nullable=False, index=True)
    source_mac = mapped_column(String, nullable=False)
    destination_mac = mapped_column(String, nullable=False)
    source_port = mapped_column(Integer, nullable=False)
    destination_port = mapped_column(Integer, nullable=False)
    protocol = mapped_column(String, nullable=False, index=True)
    start_time = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    end_time = mapped_column(DateTime, nullable=True)
    total_packets = mapped_column(Integer, default=0)
    total_bytes_up = mapped_column(BigInteger, default=0)
    total_bytes_down = mapped_column(BigInteger, default=0)
    flow_duration_ms = mapped_column(Float, default=0.0)
    packets_per_second = mapped_column(Float, default=0.0)
    features = mapped_column(JSON, nullable=True)
    direction = mapped_column(String, nullable=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)

    device = relationship("Device", back_populates="flow_records")


Device.flow_records = relationship("FlowRecord", back_populates="device")


class Alert(Base):
    """Alert model for detected threats."""

    __tablename__ = "alerts"

    class Severity(str, Enum):
        INFO = "INFO"
        LOW = "LOW"
        MEDIUM = "MEDIUM"
        HIGH = "HIGH"
        CRITICAL = "CRITICAL"

    class Category(str, Enum):
        NETWORK_ANOMALY = "NETWORK_ANOMALY"
        DDOS_ATTEMPT = "DDoS_ATTEMPT"
        PORT_SCAN = "PORT_SCAN"
        ARP_SPOOFING = "ARP_SPOOFING"
        MALWARE_COMMUNICATION = "MALWARE_COMMUNICATION"
        BRUTE_FORCE = "BRUTE_FORCE"
        DATA_EXFILTRATION = "DATA_EXFILTRATION"
        SUSPICIOUS_TRAFFIC = "SUSPICIOUS_TRAFFIC"
        CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
        SYSTEM_ANOMALY = "SYSTEM_ANOMALY"

    id = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    edge_node_id = mapped_column(String, nullable=False, index=True)
    device_id = mapped_column(String, ForeignKey("devices.id"), nullable=False, index=True)
    alert_type = mapped_column(String, nullable=False)
    category = mapped_column(SQLEnum(Category), nullable=False, index=True)
    severity = mapped_column(SQLEnum(Severity), nullable=False, index=True)
    confidence = mapped_column(Float, nullable=False)
    description = mapped_column(Text, nullable=True)
    payload = mapped_column(JSON, nullable=True)
    source_ip = mapped_column(String, nullable=True, index=True)
    destination_ip = mapped_column(String, nullable=True, index=True)
    source_mac = mapped_column(String, nullable=True)
    destination_mac = mapped_column(String, nullable=True)
    source_port = mapped_column(Integer, nullable=True)
    destination_port = mapped_column(Integer, nullable=True)
    protocol = mapped_column(String, nullable=True)
    timestamp = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_false_positive = mapped_column(Boolean, default=False)
    is_resolved = mapped_column(Boolean, default=False, index=True)
    resolved_at = mapped_column(DateTime, nullable=True)
    resolved_by = mapped_column(String, nullable=True)
    notes = mapped_column(Text, nullable=True)
    ml_metadata = mapped_column(JSON, nullable=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    updated_at = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    device = relationship("Device", back_populates="alerts")


class Anomaly(Base):
    """Anomaly model for tracking anomalies."""

    __tablename__ = "anomalies"

    class Type(str, Enum):
        DEVICE = "DEVICE"
        FLOW = "FLOW"
        NETWORK = "NETWORK"

    id = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    anomaly_type = mapped_column(SQLEnum(Type), nullable=False, index=True)
    entity_id = mapped_column(String, nullable=False, index=True)
    severity = mapped_column(String, nullable=False, index=True)
    score = mapped_column(Float, nullable=False)
    details = mapped_column(JSON, nullable=True)
    is_escalated = mapped_column(Boolean, default=False)
    is_resolved = mapped_column(Boolean, default=False, index=True)
    resolved_at = mapped_column(DateTime, nullable=True)
    timestamp = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    class Role(str, Enum):
        ADMIN = "ADMIN"
        ANALYST = "ANALYST"
        READONLY = "READONLY"
        EDGE_NODE = "EDGE_NODE"

    id = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    username = mapped_column(String, nullable=False, unique=True, index=True)
    email = mapped_column(String, nullable=False, unique=True, index=True)
    hashed_password = mapped_column(String, nullable=False)
    role = mapped_column(SQLEnum(Role), default=Role.ANALYST, nullable=False, index=True)
    is_active = mapped_column(Boolean, default=True)
    is_verified = mapped_column(Boolean, default=False)
    last_login = mapped_column(DateTime, nullable=True)
    failed_login_attempts = mapped_column(Integer, default=0)
    locked_until = mapped_column(DateTime, nullable=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    updated_at = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    audit_logs = relationship("AuditLog", back_populates="user")


class Threshold(Base):
    """Threshold model for detection configuration."""

    __tablename__ = "thresholds"

    id = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name = mapped_column(String, nullable=False, unique=True, index=True)
    description = mapped_column(Text, nullable=True)
    value = mapped_column(Float, nullable=False)
    category = mapped_column(String, nullable=False, index=True)
    is_active = mapped_column(Boolean, default=True, index=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    updated_at = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ModelMetadata(Base):
    """Model metadata for ML model tracking."""

    __tablename__ = "model_metadata"

    id = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    model_id = mapped_column(String, nullable=False, unique=True, index=True)
    model_name = mapped_column(String, nullable=False)
    model_version = mapped_column(String, nullable=False)
    description = mapped_column(Text, nullable=True)
    model_type = mapped_column(String, nullable=False)
    input_features = mapped_column(JSON, nullable=False)
    output_type = mapped_column(String, nullable=False)
    thresholds = mapped_column(JSON, nullable=True)
    training_data = mapped_column(String, nullable=True)
    accuracy = mapped_column(Float, nullable=True)
    precision = mapped_column(Float, nullable=True)
    recall = mapped_column(Float, nullable=True)
    f1_score = mapped_column(Float, nullable=True)
    file_path = mapped_column(String, nullable=False)
    file_hash = mapped_column(String, nullable=False)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    last_updated = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = mapped_column(Boolean, default=False, index=True)


class AuditLog(Base):
    """Audit log model for tracking actions."""

    __tablename__ = "audit_logs"

    id = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = mapped_column(String, nullable=False, index=True)
    entity_type = mapped_column(String, nullable=False, index=True)
    entity_id = mapped_column(String, nullable=True, index=True)
    details = mapped_column(JSON, nullable=True)
    ip_address = mapped_column(String, nullable=True)
    user_agent = mapped_column(String, nullable=True)
    timestamp = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")