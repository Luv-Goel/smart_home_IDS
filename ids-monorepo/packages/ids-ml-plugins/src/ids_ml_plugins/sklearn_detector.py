"""scikit-learn detector for ML inference.

This module provides scikit-learn implementation for anomaly detection
with support for various sklearn models.
"""

import time
import joblib
import warnings
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import numpy as np
from sklearn.base import BaseEstimator
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
import psutil

from ids_ml_plugins import (
    BaseAnomalyDetector,
    ModelMetadata,
    InferenceResult,
    ModelType,
    InferenceBackend,
)


class SklearnModelType(Enum):
    """Specific sklearn model types."""
    RANDOM_FOREST = "random_forest"
    ISOLATION_FOREST = "isolation_forest"
    LOCAL_OUTLIER_FACTOR = "local_outlier_factor"
    ONE_CLASS_SVM = "one_class_svm"
    GAUSSIAN_MIXTURE = "gaussian_mixture"
    AUTOENCODER = "autoencoder"  # Custom implementation
    ENSEMBLE = "ensemble"


@dataclass
class SklearnPipelineConfig:
    """Configuration for sklearn preprocessing pipeline."""
    
    # Scaling options
    scaling_method: str = "standard"  # standard, minmax, none
    scaling_with_mean: bool = True
    scaling_with_std: bool = True
    
    # Imputation options
    imputation_method: str = "mean"  # mean, median, most_frequent, constant
    imputation_constant: float = 0.0
    imputation_add_indicator: bool = False
    
    # Feature selection
    feature_selection_enabled: bool = False
    variance_threshold: float = 0.0
    keep_features: Optional[List[str]] = None
    
    # Dimensionality reduction
    pca_enabled: bool = False
    pca_n_components: Optional[int] = None
    
    # Caching
    enable_pipeline_caching: bool = True
    memory: str = "/tmp/sklearn_cache"
    
    def create_pipeline(self, estimator: BaseEstimator) -> Pipeline:
        """Create sklearn pipeline.
        
        Args:
            estimator: sklearn estimator
            
        Returns:
            Configured pipeline
        """
        steps = []
        
        # Imputation
        if self.imputation_method != "none":
            if self.imputation_method == "constant":
                imputer = SimpleImputer(
                    strategy="constant",
                    fill_value=self.imputation_constant,
                    add_indicator=self.imputation_add_indicator,
                )
            else:
                imputer = SimpleImputer(
                    strategy=self.imputation_method,
                    add_indicator=self.imputation_add_indicator,
                )
            steps.append(("imputer", imputer))
        
        # Scaling
        if self.scaling_method == "standard":
            scaler = StandardScaler(
                with_mean=self.scaling_with_mean,
                with_std=self.scaling_with_std,
            )
            steps.append(("scaler", scaler))
        elif self.scaling_method == "minmax":
            scaler = MinMaxScaler()
            steps.append(("scaler", scaler))
        
        # Add estimator
        steps.append(("estimator", estimator))
        
        # Create pipeline
        if self.enable_pipeline_caching:
            pipeline = Pipeline(steps, memory=self.memory)
        else:
            pipeline = Pipeline(steps)
        
        return pipeline


class SklearnAnomalyDetector(BaseAnomalyDetector):
    """Anomaly detector using scikit-learn."""
    
    def __init__(
        self,
        model_metadata: ModelMetadata,
        pipeline_config: Optional[SklearnPipelineConfig] = None,
    ):
        """Initialize sklearn detector.
        
        Args:
            model_metadata: Model metadata
            pipeline_config: Pipeline configuration
        """
        super().__init__(model_metadata)
        self.pipeline_config = pipeline_config or SklearnPipelineConfig()
        self.pipeline: Optional[Pipeline] = None
        self.estimator: Optional[BaseEstimator] = None
        self._performance_stats: Dict[str, List[float]] = {
            "inference_time": [],
            "preprocess_time": [],
            "total_time": [],
        }
        self._memory_stats: Dict[str, List[int]] = {
            "memory_mb": [],
        }
        
        # Set metadata backend
        self.metadata.backend = InferenceBackend.SCIKIT_LEARN
    
    def load_model(self, model_path: str) -> bool:
        """Load sklearn model.
        
        Args:
            model_path: Path to sklearn model file
            
        Returns:
            True if successful
        """
        try:
            print(f"Loading sklearn model from {model_path}")
            
            # Load model using joblib
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                loaded_data = joblib.load(model_path)
            
            # Handle different serialization formats
            if isinstance(loaded_data, dict):
                # Dictionary format with metadata
                self.pipeline = loaded_data.get("pipeline")
                self.estimator = loaded_data.get("estimator", self.pipeline)
                metadata_dict = loaded_data.get("metadata", {})
                
                # Update metadata from loaded file
                for key, value in metadata_dict.items():
                    if hasattr(self.metadata, key):
                        setattr(self.metadata, key, value)
                
            elif hasattr(loaded_data, "predict") or hasattr(loaded_data, "decision_function"):
                # Direct estimator
                self.estimator = loaded_data
                self.pipeline = None
                
            elif isinstance(loaded_data, Pipeline):
                # Pipeline object
                self.pipeline = loaded_data
                self.estimator = self.pipeline.steps[-1][1]
                
            else:
                raise ValueError(f"Unsupported model format: {type(loaded_data)}")
            
            # Ensure we have an estimator
            if self.estimator is None:
                raise ValueError("No estimator found in model file")
            
            # Extract model information
            self._extract_model_info()
            
            self._loaded = True
            print(f"Model loaded successfully: {self.metadata.model_id}")
            print(f"Model type: {type(self.estimator).__name__}")
            
            return True
            
        except Exception as e:
            print(f"Failed to load sklearn model: {str(e)}")
            self.pipeline = None
            self.estimator = None
            self._loaded = False
            return False
    
    def _extract_model_info(self):
        """Extract information from loaded model."""
        try:
            estimator = self.estimator
            
            # Get feature count if available
            if hasattr(estimator, "n_features_in_"):
                self.metadata.feature_count = estimator.n_features_in_
            elif hasattr(estimator, "n_features_"):
                self.metadata.feature_count = estimator.n_features_
            
            # Get input/output shapes
            if self.metadata.feature_count > 0:
                self.metadata.input_shape = (1, self.metadata.feature_count)
            
            # Determine model type
            model_name = type(estimator).__name__.lower()
            
            if "forest" in model_name:
                if "isolation" in model_name:
                    self.metadata.model_type = ModelType.ISOLATION_FOREST
                else:
                    self.metadata.model_type = ModelType.RANDOM_FOREST
            elif "svm" in model_name:
                self.metadata.model_type = ModelType.ONE_CLASS_SVM
            elif "autoencoder" in model_name or "ae" in model_name:
                self.metadata.model_type = ModelType.AUTOENCODER
            elif "ensemble" in model_name:
                self.metadata.model_type = ModelType.RANDOM_FOREST
            else:
                self.metadata.model_type = ModelType.UNKNOWN
            
            # Set default thresholds based on model type
            if self.metadata.model_type == ModelType.ISOLATION_FOREST:
                self.metadata.anomaly_threshold = -0.1  # Isolation Forest scores are negative
            elif self.metadata.model_type == ModelType.ONE_CLASS_SVM:
                self.metadata.anomaly_threshold = 0.0  # Decision function threshold
            
        except Exception as e:
            print(f"Warning: Could not extract model info: {str(e)}")
    
    def unload_model(self) -> bool:
        """Unload model.
        
        Returns:
            True if successful
        """
        try:
            # Clear references to free memory
            self.pipeline = None
            self.estimator = None
            self._loaded = False
            self._performance_stats.clear()
            self._memory_stats.clear()
            
            # Force garbage collection
            import gc
            gc.collect()
            
            return True
            
        except Exception:
            return False
    
    def preprocess_features(self, features: np.ndarray) -> np.ndarray:
        """Preprocess features for sklearn model.
        
        Args:
            features: Raw features
            
        Returns:
            Preprocessed features
        """
        start_time = time.time()
        
        # Apply base preprocessing
        features_processed = super().preprocess_features(features)
        
        # Ensure correct shape
        if len(features_processed.shape) == 1:
            features_processed = features_processed.reshape(1, -1)
        
        # Pad/truncate to expected feature count
        expected_features = self.metadata.feature_count
        if expected_features > 0 and features_processed.shape[1] != expected_features:
            actual_features = features_processed.shape[1]
            if actual_features < expected_features:
                # Pad with feature means
                padding = np.full((features_processed.shape[0], 
                                 expected_features - actual_features), 
                                np.nanmean(features_processed))
                features_processed = np.hstack([features_processed, padding])
            else:
                # Truncate
                features_processed = features_processed[:, :expected_features]
        
        preprocess_time = (time.time() - start_time) * 1000
        self._performance_stats["preprocess_time"].append(preprocess_time)
        
        return features_processed
    
    def predict(self, features: np.ndarray) -> InferenceResult:
        """Predict anomaly for single sample.
        
        Args:
            features: Feature array
            
        Returns:
            Inference result
        """
        try:
            start_time = time.time()
            memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            # Preprocess features
            features_processed = self.preprocess_features(features)
            
            # Get appropriate prediction method
            if self.pipeline is not None:
                # Use pipeline
                prediction_func = self.pipeline.predict
                score_func = getattr(self.pipeline, "decision_function", 
                                   getattr(self.pipeline, "score_samples", None))
            else:
                # Use estimator directly
                prediction_func = self.estimator.predict
                score_func = getattr(self.estimator, "decision_function", 
                                   getattr(self.estimator, "score_samples", None))
            
            # Get anomaly score
            inference_start = time.time()
            
            # Try different scoring methods
            anomaly_score = 0.0
            
            if score_func is not None:
                try:
                    score = score_func(features_processed)
                    if isinstance(score, (list, np.ndarray)):
                        anomaly_score = float(score[0])
                    else:
                        anomaly_score = float(score)
                except Exception as e:
                    print(f"Warning: Score function failed: {str(e)}")
                    anomaly_score = 0.0
            else:
                # Use predict method and convert to score
                try:
                    prediction = prediction_func(features_processed)
                    if isinstance(prediction, (list, np.ndarray)):
                        # Binary classification: 1 = anomaly, 0 = normal
                        pred_value = prediction[0]
                        if pred_value == 1:
                            anomaly_score = 0.9  # High score for anomaly
                        elif pred_value == -1:
                            anomaly_score = 0.9  # Also high score for -1 anomaly class
                        else:
                            anomaly_score = 0.1  # Low score for normal
                    else:
                        anomaly_score = 0.5  # Default
                except Exception as e:
                    print(f"Warning: Predict failed: {str(e)}")
                    anomaly_score = 0.0
            
            inference_time = (time.time() - inference_start) * 1000
            
            # Determine if anomaly
            is_anomaly = self._is_anomaly(anomaly_score)
            
            # Calculate confidence
            confidence = self._calculate_confidence(anomaly_score)
            
            # Record performance
            total_time = (time.time() - start_time) * 1000
            memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            memory_used = memory_after - memory_before
            
            self._performance_stats["inference_time"].append(inference_time)
            self._performance_stats["total_time"].append(total_time)
            self._memory_stats["memory_mb"].append(memory_used)
            
            # Keep only last 1000 measurements
            for stats_dict in [self._performance_stats, self._memory_stats]:
                for key in stats_dict:
                    if len(stats_dict[key]) > 1000:
                        stats_dict[key] = stats_dict[key][-1000:]
            
            # Create result
            result = InferenceResult(
                model_id=self.metadata.model_id,
                timestamp=datetime.utcnow().isoformat(),
                is_anomaly=is_anomaly,
                anomaly_score=anomaly_score,
                confidence=confidence,
                inference_time_ms=inference_time,
                metadata={
                    "preprocess_time_ms": self._performance_stats["preprocess_time"][-1],
                    "total_time_ms": total_time,
                    "memory_used_mb": memory_used,
                    "backend": "scikit_learn",
                    "model_type": self.metadata.model_type.value,
                    "estimator_type": type(self.estimator).__name__,
                }
            )
            
            return result
            
        except Exception as e:
            # Return error result
            return InferenceResult(
                model_id=self.metadata.model_id,
                timestamp=datetime.utcnow().isoformat(),
                is_anomaly=False,
                anomaly_score=0.0,
                confidence=0.0,
                inference_time_ms=0.0,
                metadata={
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
    
    def predict_batch(self, features_batch: np.ndarray) -> List[InferenceResult]:
        """Predict anomalies for batch of features.
        
        Args:
            features_batch: Batch of feature arrays
            
        Returns:
            List of inference results
        """
        results = []
        
        # Process in chunks to manage memory
        chunk_size = 100
        
        for i in range(0, len(features_batch), chunk_size):
            chunk = features_batch[i:i + chunk_size]
            
            for features in chunk:
                result = self.predict(features)
                results.append(result)
        
        return results
    
    def _is_anomaly(self, anomaly_score: float) -> bool:
        """Determine if score indicates anomaly.
        
        Args:
            anomaly_score: Anomaly score
            
        Returns:
            True if anomaly
        """
        # Handle different score ranges based on model type
        if self.metadata.model_type == ModelType.ISOLATION_FOREST:
            # Isolation Forest: negative scores, more negative = more anomalous
            return anomaly_score < self.metadata.anomaly_threshold
        elif self.metadata.model_type == ModelType.ONE_CLASS_SVM:
            # One-Class SVM: decision function, negative = anomaly
            return anomaly_score < self.metadata.anomaly_threshold
        else:
            # Default: higher score = more anomalous
            return anomaly_score > self.metadata.anomaly_threshold
    
    def _calculate_confidence(self, anomaly_score: float) -> float:
        """Calculate confidence from anomaly score.
        
        Args:
            anomaly_score: Anomaly score
            
        Returns:
            Confidence value between 0 and 1
        """
        # Default implementation
        if self.metadata.model_type == ModelType.ISOLATION_FOREST:
            # Isolation Forest scores are between -1 and 0
            # Convert to confidence: more negative = higher confidence in anomaly
            confidence = abs(anomaly_score)  # 0 to 1
        elif self.metadata.model_type == ModelType.ONE_CLASS_SVM:
            # SVM decision function values
            # Normalize to 0-1 range
            confidence = min(max(0.0, (anomaly_score + 1.0) / 2.0), 1.0)
        else:
            # Assume score is already between 0 and 1
            confidence = min(max(0.0, anomaly_score), 1.0)
        
        return confidence
    
    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        stats = {}
        
        # Performance timing stats
        for key, values in self._performance_stats.items():
            if values:
                stats[key] = {
                    "count": len(values),
                    "mean_ms": np.mean(values),
                    "std_ms": np.std(values),
                    "min_ms": np.min(values),
                    "max_ms": np.max(values),
                    "p50_ms": np.percentile(values, 50),
                    "p95_ms": np.percentile(values, 95),
                    "p99_ms": np.percentile(values, 99),
                }
            else:
                stats[key] = {
                    "count": 0,
                    "mean_ms": 0.0,
                    "std_ms": 0.0,
                    "min_ms": 0.0,
                    "max_ms": 0.0,
                    "p50_ms": 0.0,
                    "p95_ms": 0.0,
                    "p99_ms": 0.0,
                }
        
        # Memory stats
        for key, values in self._memory_stats.items():
            if values:
                stats[key] = {
                    "count": len(values),
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values),
                    "p50": np.percentile(values, 50),
                    "p95": np.percentile(values, 95),
                    "p99": np.percentile(values, 99),
                }
        
        return stats
    
    def optimize_for_edge(self) -> SklearnPipelineConfig:
        """Get optimization config for edge devices.
        
        Returns:
            Optimized pipeline configuration
        """
        return SklearnPipelineConfig(
            scaling_method="minmax",  # Simpler than standard scaling
            scaling_with_mean=True,
            scaling_with_std=True,
            imputation_method="mean",
            imputation_constant=0.0,
            imputation_add_indicator=False,
            feature_selection_enabled=False,
            variance_threshold=0.0,
            pca_enabled=False,
            enable_pipeline_caching=False,  # Disable caching to save memory on edge
        )


def create_sklearn_detector(
    model_path: str,
    model_id: str = None,
    optimize_for_edge: bool = False,
) -> Optional[SklearnAnomalyDetector]:
    """Factory function to create sklearn detector.
    
    Args:
        model_path: Path to sklearn model file
        model_id: Model identifier (generated if None)
        optimize_for_edge: Optimize for edge devices
        
    Returns:
        sklearn detector instance or None
    """
    import os
    import uuid
    
    if not os.path.exists(model_path):
        print(f"Model file not found: {model_path}")
        return None
    
    # Generate model ID if not provided
    if model_id is None:
        model_id = f"sklearn_{os.path.basename(model_path)}_{uuid.uuid4().hex[:8]}"
    
    # Create metadata
    metadata = ModelMetadata(
        model_id=model_id,
        model_type=ModelType.UNKNOWN,  # Will be detected during load
        backend=InferenceBackend.SCIKIT_LEARN,
        version="1.0.0",
        description=f"scikit-learn model: {os.path.basename(model_path)}",
        created_at=datetime.utcnow().isoformat(),
        model_hash="",  # Could compute file hash here
        anomaly_threshold=0.75,
        confidence_threshold=0.8,
    )
    
    # Create pipeline config
    if optimize_for_edge:
        pipeline_config = SklearnPipelineConfig()
        # Will be optimized by detector
    else:
        pipeline_config = SklearnPipelineConfig()
    
    # Create detector
    detector = SklearnAnomalyDetector(metadata, pipeline_config)
    
    # Load model
    if detector.load_model(model_path):
        return detector
    else:
        return None