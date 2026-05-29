"""Configuration for Fusion Engine Service."""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class FusionMethod(Enum):
    """Fusion methods for combining anomaly scores."""
    LINEAR_FUSION = "linear_fusion"  # From research paper: σ(β₀ + β₁s_dev + β₂s_flow + β₃s_devs_flow)
    WEIGHTED_AVERAGE = "weighted_average"
    MAX_POOLING = "max_pooling"
    MIN_POOLING = "min_pooling"
    PRODUCT = "product"
    VOTING = "voting"


class ThresholdOptimizationMethod(Enum):
    """Threshold optimization methods."""
    COST_AWARE = "cost_aware"  # J(τ) = C_FN * P_FN(τ) + C_FP * P_FP(τ)
    ROC_CURVE = "roc_curve"
    PRECISION_RECALL = "precision_recall"
    MANUAL = "manual"


class ConfidenceMethod(Enum):
    """Confidence calculation methods."""
    SIGMOID = "sigmoid"
    SOFTMAX = "softmax"
    PLAIN = "plain"


class Config(BaseSettings):
    """Configuration for Fusion Engine Service."""
    
    # Service settings
    service_name: str = "fusion-engine-service"
    node_id: str = Field(default_factory=lambda: f"fusion-node-{os.getpid()}")
    environment: str = "development"
    debug: bool = False
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Fusion configuration
    fusion_method: FusionMethod = FusionMethod.LINEAR_FUSION
    threshold_optimization: ThresholdOptimizationMethod = ThresholdOptimizationMethod.COST_AWARE
    confidence_method: ConfidenceMethod = ConfidenceMethod.SIGMOID
    
    # Linear fusion coefficients (from research paper)
    beta_0: float = -2.0  # Bias term
    beta_1: float = 1.5   # Device anomaly coefficient
    beta_2: float = 1.2   # Flow anomaly coefficient
    beta_3: float = 0.3   # Interaction term coefficient
    
    # Cost parameters for threshold optimization
    cost_false_negative: float = 10.0  # C_FN: Cost of missing an attack
    cost_false_positive: float = 1.0   # C_FP: Cost of false alarm
    learning_rate: float = 0.01         # Learning rate for threshold optimization
    optimization_steps: int = 1000      # Steps for threshold optimization
    
    # Threshold values
    device_anomaly_threshold: float = 0.75
    flow_anomaly_threshold: float = 0.7
    fused_anomaly_threshold: float = 0.8
    min_confidence: float = 0.6
    
    # Performance settings
    max_queue_size: int = 1000
    processing_batch_size: int = 32
    fusion_window_size: int = 100       # Samples for adaptive threshold adjustment
    cache_window: int = 1000            # Samples to keep for threshold optimization
    
    # Alert severity configuration
    severity_thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "low": 0.6,
        "medium": 0.75,
        "high": 0.85,
        "critical": 0.95,
    })
    
    # Alert persistence
    alert_retention_days: int = 30
    alert_aggregation_window: int = 300  # seconds (5 minutes)
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8003
    api_workers: int = 2
    
    # MQTT settings
    mqtt_broker_url: str = "mqtt://localhost:1883"
    mqtt_client_id: str = Field(default_factory=lambda: f"fusion-engine-{os.getpid()}")
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_qos: int = 1
    
    # Input topics
    mqtt_device_anomaly_topic: str = "ids/edge/+/device/anomaly"
    mqtt_flow_anomaly_topic: str = "ids/edge/+/flow/anomaly"
    mqtt_ml_anomaly_topic: str = "ids/edge/+/ml/inferences"
    
    # Output topics
    mqtt_alert_topic: str = "ids/edge/+/alerts"
    mqtt_status_topic: str = "ids/edge/+/fusion/status"
    mqtt_command_topic: str = "ids/cloud/command/fusion"
    
    # Database settings
    database_url: str = "sqlite:///fusion_engine.db"  # Simple SQLite for edge
    redis_url: Optional[str] = None  # Optional for caching
    
    # Edge optimization
    optimize_for_edge: bool = False
    memory_limit_mb: int = 256
    cpu_limit: int = 1
    
    class Config:
        env_file = ".env"
        env_prefix = "FUSION_ENGINE_"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        """Initialize config with environment-specific defaults."""
        super().__init__(**kwargs)
        
        # Apply edge optimization
        if self.optimize_for_edge:
            self._apply_edge_optimization()
    
    def _apply_edge_optimization(self):
        """Apply optimizations for edge devices."""
        self.max_queue_size = 500
        self.processing_batch_size = 16
        self.fusion_window_size = 50
        self.cache_window = 500
        self.learning_rate = 0.1  # Faster convergence on edge
        self.api_workers = 1
    
    @property
    def fusion_coefficients(self) -> Dict[str, float]:
        """Get fusion coefficients for linear fusion.
        
        Returns:
            Dictionary of fusion coefficients
        """
        return {
            "beta_0": self.beta_0,
            "beta_1": self.beta_1,
            "beta_2": self.beta_2,
            "beta_3": self.beta_3,
        }
    
    @property
    def cost_matrix(self) -> Dict[str, float]:
        """Get cost matrix for threshold optimization.
        
        Returns:
            Dictionary of costs
        """
        return {
            "C_FN": self.cost_false_negative,
            "C_FP": self.cost_false_positive,
        }


import os  # Required for default_factory lambda