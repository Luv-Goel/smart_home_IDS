"""ML inference schemas for Smart Home IDS.

This module provides Pydantic models for ML inference results and model metadata.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from ids_schemas.base import IDSBasemodel


class InferenceStatus(str, Enum):
    """ML inference status."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TIMEOUT = "TIMEOUT"
    PENDING = "PENDING"
    SKIPPED = "SKIPPED"


class InferenceResult(BaseModel):
    """ML inference result."""

    model_name: str = Field(description="Name of the model used")
    model_version: str = Field(description="Version of the model")
    status: InferenceStatus = Field(description="Inference status")
    prediction: int | float | str = Field(description="Prediction result")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    prediction_time_ms: float = Field(description="Prediction time in milliseconds")
    is_anomaly: bool = Field(description="Whether this is an anomaly")
    anomaly_category: str | None = Field(default=None, description="Anomaly category if applicable")
    feature_importance: dict[str, float] | None = Field(default=None, description="Feature importance scores")
    threshold_used: float = Field(default=0.5, description="Threshold used for judgment")
    model_hash: str = Field(description="SHA256 hash of model file")


class InferenceEvent(IDSBasemodel):
    """Complete inference event for MQTT publishing."""

    event_type: Literal["inference"] = "inference"
    node_id: str = Field(description="Edge node identifier")
    flow_id: str = Field(description="Flow identifier")
    feature_vector: dict[str, float] = Field(description="Input feature vector")
    result: InferenceResult = Field(description="Inference result")
    timestamp: str = Field(description="Event timestamp")
    device_id: str | None = Field(default=None, description="Device identifier")


class ModelMetadata(BaseModel):
    """Metadata about a detection model."""

    model_id: str = Field(description="Unique model identifier")
    model_name: str = Field(description="Model display name")
    model_version: str = Field(description="Model version")
    description: str = Field(description="Model description")
    model_type: str = Field(description="Type of model (e.g., Random Forest, Autoencoder)")
    input_features: list[str] = Field(description="List of input features")
    output_type: str = Field(description="Output type (classification, regression)")
    thresholds: dict[str, float] = Field(description="Classification thresholds")
    training_data: str | None = Field(default=None, description="Training data source")
    accuracy: float | None = Field(default=None, ge=0.0, le=1.0, description="Model accuracy")
    precision: float | None = Field(default=None, ge=0.0, le=1.0, description="Model precision")
    recall: float | None = Field(default=None, ge=0.0, le=1.0, description="Model recall")
    f1_score: float | None = Field(default=None, ge=0.0, le=1.0, description="Model F1 score")
    file_path: str = Field(description="Path to model file")
    file_hash: str = Field(description="SHA256 hash of model file")
    created_at: str = Field(description="Model creation timestamp")
    last_updated: str = Field(description="Model last update timestamp")
    is_active: bool = Field(default=False, description="Whether model is currently active")


class InferenceRequest(BaseModel):
    """Request for ML inference."""

    feature_vector: dict[str, float] = Field(description="Feature vector to classify")
    model_version: str | None = Field(default=None, description="Specific model version to use")
    return_features: bool = Field(default=False, description="Whether to return feature importance")


class InferenceResponse(BaseModel):
    """Response from ML inference service."""

    inference_id: str = Field(description="Unique inference ID")
    result: InferenceResult = Field(description="Inference result")
    request_id: str | None = Field(default=None, description="Request ID if provided")