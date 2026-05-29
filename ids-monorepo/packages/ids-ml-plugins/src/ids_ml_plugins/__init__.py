"""ML Plugin Framework for Smart Home IDS.

This package provides a plugin-based architecture for ML inference
with support for multiple backends (ONNX, scikit-learn, PyTorch, TensorFlow).
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any, Tuple
import numpy as np
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

__version__ = "0.1.0"


class ModelType(Enum):
    """Supported model types."""
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    NEURAL_NETWORK = "neural_network"
    AUTOENCODER = "autoencoder"
    ISOLATION_FOREST = "isolation_forest"
    ONE_CLASS_SVM = "one_class_svm"
    UNKNOWN = "unknown"


class InferenceBackend(Enum):
    """Supported inference backends."""
    ONNX_RUNTIME = "onnx_runtime"
    SCIKIT_LEARN = "scikit_learn"
    TENSORFLOW_LITE = "tensorflow_lite"
    PYTORCH = "pytorch"
    OPENVINO = "openvino"
    CUSTOM = "custom"


@dataclass
class ModelMetadata:
    """Metadata for ML models."""
    
    model_id: str
    model_type: ModelType
    backend: InferenceBackend
    version: str = "1.0.0"
    description: Optional[str] = None
    feature_count: int = 0
    target_count: int = 1
    input_shape: Tuple[int, ...] = ()
    output_shape: Tuple[int, ...] = ()
    created_at: str = ""
    model_hash: str = ""
    
    # Performance metrics
    inference_time_ms: float = 0.0
    memory_bytes: int = 0
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    
    # Requirements
    requires_scaling: bool = True
    requires_imputation: bool = True
    supported_features: List[str] = field(default_factory=list)
    
    # Thresholds
    anomaly_threshold: float = 0.5
    confidence_threshold: float = 0.75
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["model_type"] = self.model_type.value
        data["backend"] = self.backend.value
        data["input_shape"] = list(self.input_shape)
        data["output_shape"] = list(self.output_shape)
        return data
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelMetadata":
        """Create from dictionary."""
        data = data.copy()
        data["model_type"] = ModelType(data["model_type"])
        data["backend"] = InferenceBackend(data["backend"])
        data["input_shape"] = tuple(data["input_shape"])
        data["output_shape"] = tuple(data["output_shape"])
        return cls(**data)


@dataclass
class InferenceResult:
    """Result from model inference."""
    
    model_id: str
    timestamp: str
    is_anomaly: bool
    anomaly_score: float
    confidence: float
    predicted_class: Optional[int] = None
    class_probabilities: Optional[np.ndarray] = None
    feature_importance: Optional[Dict[str, float]] = None
    inference_time_ms: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        
        # Convert numpy arrays to lists
        if self.class_probabilities is not None:
            data["class_probabilities"] = self.class_probabilities.tolist()
        
        # Remove numpy arrays
        data.pop("class_probabilities", None)
        
        # Add metadata
        if self.metadata:
            data.update(self.metadata)
        
        return data


class BaseAnomalyDetector(ABC):
    """Base class for anomaly detection plugins."""
    
    def __init__(self, model_metadata: ModelMetadata):
        """Initialize detector.
        
        Args:
            model_metadata: Model metadata
        """
        self.metadata = model_metadata
        self._loaded = False
    
    @abstractmethod
    def load_model(self, model_path: str) -> bool:
        """Load model from path.
        
        Args:
            model_path: Path to model file
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def unload_model(self) -> bool:
        """Unload model from memory.
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def predict(self, features: np.ndarray) -> InferenceResult:
        """Predict anomaly for given features.
        
        Args:
            features: Feature array of shape (n_samples, n_features)
            
        Returns:
            Inference result
        """
        pass
    
    @abstractmethod
    def predict_batch(self, features_batch: np.ndarray) -> List[InferenceResult]:
        """Predict anomalies for batch of features.
        
        Args:
            features_batch: Feature array of shape (batch_size, n_samples, n_features)
            
        Returns:
            List of inference results
        """
        pass
    
    def preprocess_features(self, features: np.ndarray) -> np.ndarray:
        """Preprocess features before prediction.
        
        Args:
            features: Raw features
            
        Returns:
            Preprocessed features
        """
        # Default implementation - override in subclasses
        if self.metadata.requires_scaling:
            # Simple min-max scaling
            features = (features - features.min()) / (features.max() - features.min() + 1e-10)
        
        if self.metadata.requires_imputation:
            # Impute missing values with feature mean
            features = np.nan_to_num(features, nan=np.nanmean(features, axis=0))
        
        return features
    
    def validate_features(self, features: np.ndarray) -> bool:
        """Validate input features.
        
        Args:
            features: Features to validate
            
        Returns:
            True if valid, False otherwise
        """
        if features is None or len(features.shape) != 2:
            return False
        
        expected_features = self.metadata.feature_count
        if expected_features > 0 and features.shape[1] != expected_features:
            return False
        
        return True
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model_id": self.metadata.model_id,
            "model_type": self.metadata.model_type.value,
            "backend": self.metadata.backend.value,
            "version": self.metadata.version,
            "loaded": self._loaded,
            "feature_count": self.metadata.feature_count,
            "input_shape": list(self.metadata.input_shape),
            "output_shape": list(self.metadata.output_shape),
        }
    
    def is_loaded(self) -> bool:
        """Check if model is loaded.
        
        Returns:
            True if model is loaded
        """
        return self._loaded


class ModelRegistry:
    """Registry for managing ML models."""
    
    def __init__(self):
        """Initialize registry."""
        self.models: Dict[str, BaseAnomalyDetector] = {}
        self.metadata_store: Dict[str, ModelMetadata] = {}
        self.active_model_id: Optional[str] = None
    
    def register_model(self, detector: BaseAnomalyDetector) -> bool:
        """Register a model detector.
        
        Args:
            detector: Anomaly detector instance
            
        Returns:
            True if successful
        """
        if not detector.is_loaded():
            return False
        
        model_id = detector.metadata.model_id
        self.models[model_id] = detector
        self.metadata_store[model_id] = detector.metadata
        
        # Set as active if no active model
        if self.active_model_id is None:
            self.active_model_id = model_id
        
        return True
    
    def unregister_model(self, model_id: str) -> bool:
        """Unregister a model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            True if successful
        """
        if model_id not in self.models:
            return False
        
        # Unload model
        detector = self.models[model_id]
        detector.unload_model()
        
        # Remove from registry
        del self.models[model_id]
        del self.metadata_store[model_id]
        
        # Update active model if needed
        if self.active_model_id == model_id:
            self.active_model_id = next(iter(self.models.keys()), None)
        
        return True
    
    def get_model(self, model_id: str) -> Optional[BaseAnomalyDetector]:
        """Get model detector.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Detector instance or None
        """
        return self.models.get(model_id)
    
    def get_active_model(self) -> Optional[BaseAnomalyDetector]:
        """Get active model detector.
        
        Returns:
            Active detector instance or None
        """
        if self.active_model_id is None:
            return None
        return self.models.get(self.active_model_id)
    
    def set_active_model(self, model_id: str) -> bool:
        """Set active model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            True if successful
        """
        if model_id not in self.models:
            return False
        
        self.active_model_id = model_id
        return True
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models.
        
        Returns:
            List of model information dictionaries
        """
        return [
            {
                "model_id": model_id,
                "active": model_id == self.active_model_id,
                "metadata": metadata.to_dict(),
            }
            for model_id, metadata in self.metadata_store.items()
        ]
    
    def predict_with_active(self, features: np.ndarray) -> Optional[InferenceResult]:
        """Predict using active model.
        
        Args:
            features: Input features
            
        Returns:
            Inference result or None
        """
        detector = self.get_active_model()
        if detector is None:
            return None
        
        if not detector.validate_features(features):
            return None
        
        return detector.predict(features)
    
    def clear(self):
        """Clear registry."""
        # Unload all models
        for detector in self.models.values():
            detector.unload_model()
        
        self.models.clear()
        self.metadata_store.clear()
        self.active_model_id = None