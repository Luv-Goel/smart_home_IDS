"""Configuration for ML Inference Service."""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class InferenceBackend(Enum):
    """Supported inference backends."""
    ONNX = "onnx"
    SCIKIT_LEARN = "scikit-learn"
    AUTO = "auto"


class ModelCacheStrategy(Enum):
    """Model caching strategies."""
    MEMORY = "memory"
    DISK = "disk"
    NONE = "none"


class InferenceMode(Enum):
    """Inference modes."""
    REALTIME = "realtime"
    BATCH = "batch"
    HYBRID = "hybrid"


class Config(BaseSettings):
    """Configuration for ML Inference Service."""
    
    # Service settings
    service_name: str = "ml-inference-service"
    node_id: str = Field(default_factory=lambda: os.getenv("HOSTNAME", f"node-{os.getpid()}"))
    environment: str = "development"
    debug: bool = False
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Model settings
    model_dir: str = "/var/models"
    default_model: str = "random_forest.onnx"
    inference_backend: InferenceBackend = InferenceBackend.AUTO
    cache_strategy: ModelCacheStrategy = ModelCacheStrategy.MEMORY
    inference_mode: InferenceMode = InferenceMode.REALTIME
    
    # Performance settings
    batch_size: int = 32
    max_queue_size: int = 1000
    inference_threads: int = 2
    preprocessing_threads: int = 2
    
    # ONNX specific
    onnx_execution_provider: str = "cpu"
    onnx_inter_op_threads: int = 1
    onnx_intra_op_threads: int = 1
    
    # scikit-learn specific
    sklearn_enable_caching: bool = True
    sklearn_cache_dir: str = "/tmp/sklearn_cache"
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8002
    api_workers: int = 2
    
    # MQTT settings
    mqtt_broker_url: str = "mqtt://localhost:1883"
    mqtt_client_id: str = Field(default_factory=lambda: f"ml-inference-{os.getpid()}")
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_qos: int = 1
    
    # Redis settings (for model cache)
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600  # 1 hour
    
    # Health check
    health_check_interval: int = 30  # seconds
    metrics_collection_interval: int = 60  # seconds
    
    # Thresholds
    anomaly_threshold: float = 0.75
    confidence_threshold: float = 0.8
    min_inference_confidence: float = 0.5
    
    # Edge optimization (for Raspberry Pi)
    optimize_for_edge: bool = False
    max_memory_mb: int = 512
    cpu_affinity: Optional[List[int]] = None
    
    # Topics
    mqtt_input_topic: str = "ids/edge/+/features"
    mqtt_output_topic: str = "ids/edge/+/inferences"
    mqtt_status_topic: str = "ids/edge/+/ml/status"
    mqtt_command_topic: str = "ids/cloud/command/ml"
    
    class Config:
        env_file = ".env"
        env_prefix = "ML_INFERENCE_"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        """Initialize config with environment-specific defaults."""
        super().__init__(**kwargs)
        
        # Apply edge optimization
        if self.optimize_for_edge:
            self._apply_edge_optimization()
    
    def _apply_edge_optimization(self):
        """Apply optimizations for edge devices."""
        self.batch_size = 16
        self.max_queue_size = 500
        self.inference_threads = 1
        self.preprocessing_threads = 1
        self.onnx_inter_op_threads = 1
        self.onnx_intra_op_threads = 1
        self.cache_strategy = ModelCacheStrategy.DISK
        self.sklearn_enable_caching = False
        self.api_workers = 1
    
    @property
    def model_path(self) -> str:
        """Get full model path."""
        return str(Path(self.model_dir) / self.default_model)
    
    @property
    def is_development(self) -> bool:
        """Check if in development environment."""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if in production environment."""
        return self.environment.lower() == "production"
    
    def get_mqtt_config(self) -> Dict[str, Any]:
        """Get MQTT configuration."""
        config = {
            "broker_url": self.mqtt_broker_url,
            "client_id": self.mqtt_client_id,
            "qos": self.mqtt_qos,
        }
        
        if self.mqtt_username and self.mqtt_password:
            config["username"] = self.mqtt_username
            config["password"] = self.mqtt_password
        
        return config
    
    def get_onnx_config(self) -> Dict[str, Any]:
        """Get ONNX Runtime configuration."""
        return {
            "execution_provider": self.onnx_execution_provider,
            "inter_op_num_threads": self.onnx_inter_op_threads,
            "intra_op_num_threads": self.onnx_intra_op_threads,
        }
    
    def get_sklearn_config(self) -> Dict[str, Any]:
        """Get scikit-learn configuration."""
        return {
            "enable_caching": self.sklearn_enable_caching,
            "cache_dir": self.sklearn_cache_dir,
        }


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    
    model_id: str
    model_path: str
    backend: InferenceBackend
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Inference parameters
    batch_size: int = 32
    preprocessing_enabled: bool = True
    feature_scaling: bool = True
    imputation_strategy: str = "mean"
    
    # Thresholds
    anomaly_threshold: float = 0.75
    confidence_threshold: float = 0.8
    
    # Performance
    warmup_samples: int = 100
    enable_profiling: bool = False
    
    def __post_init__(self):
        """Validate configuration."""
        if not Path(self.model_path).exists():
            raise ValueError(f"Model file not found: {self.model_path}")
        
        if self.anomaly_threshold < 0 or self.anomaly_threshold > 1:
            raise ValueError("Anomaly threshold must be between 0 and 1")
        
        if self.confidence_threshold < 0 or self.confidence_threshold > 1:
            raise ValueError("Confidence threshold must be between 0 and 1")


# Create global config instance
config = Config()