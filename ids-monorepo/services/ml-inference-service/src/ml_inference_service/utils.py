"""Utility functions for ML Inference Service."""

import time
import json
import hashlib
import pickle
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path

import numpy as np
import redis
from structlog import get_logger

from .config import Config, ModelCacheStrategy

logger = get_logger(__name__)


class PerformanceMetricType(Enum):
    """Types of performance metrics."""
    INFERENCE_TIME = "inference_time"
    PREPROCESS_TIME = "preprocess_time"
    QUEUE_TIME = "queue_time"
    MODEL_LOAD_TIME = "model_load_time"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"


@dataclass
class PerformanceRecord:
    """Performance record."""
    
    metric_type: PerformanceMetricType
    value: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["metric_type"] = self.metric_type.value
        data["timestamp_iso"] = datetime.fromtimestamp(self.timestamp).isoformat()
        return data


class PerformanceMetrics:
    """Performance metrics collector."""
    
    def __init__(self, max_records: int = 10000):
        """Initialize metrics collector.
        
        Args:
            max_records: Maximum records to keep per metric
        """
        self.max_records = max_records
        self.metrics: Dict[PerformanceMetricType, List[PerformanceRecord]] = {}
        self.summary_stats: Dict[str, Dict[str, float]] = {}
        self._lock = threading.RLock()
        
        # Initialize metric storage
        for metric_type in PerformanceMetricType:
            self.metrics[metric_type] = []
    
    def record(self, metric_type: PerformanceMetricType, value: float, **metadata):
        """Record a performance metric.
        
        Args:
            metric_type: Type of metric
            value: Metric value
            **metadata: Additional metadata
        """
        with self._lock:
            records = self.metrics[metric_type]
            record = PerformanceRecord(
                metric_type=metric_type,
                value=value,
                metadata=metadata,
            )
            records.append(record)
            
            # Limit records size
            if len(records) > self.max_records:
                self.metrics[metric_type] = records[-self.max_records:]
    
    def record_inference(self, inference_time_ms: float, **metadata):
        """Record inference time.
        
        Args:
            inference_time_ms: Inference time in milliseconds
            **metadata: Additional metadata
        """
        self.record(
            PerformanceMetricType.INFERENCE_TIME,
            inference_time_ms,
            **metadata,
        )
    
    def record_model_load(self, model_id: str, backend: str, feature_count: int):
        """Record model load information.
        
        Args:
            model_id: Model identifier
            backend: Inference backend
            feature_count: Number of features
        """
        self.record(
            PerformanceMetricType.MODEL_LOAD_TIME,
            0.0,  # Actual time would be measured during load
            model_id=model_id,
            backend=backend,
            feature_count=feature_count,
        )
    
    def get_metric_stats(self, metric_type: PerformanceMetricType) -> Dict[str, float]:
        """Get statistics for a metric type.
        
        Args:
            metric_type: Type of metric
            
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            records = self.metrics[metric_type]
            
            if not records:
                return {
                    "count": 0,
                    "mean": 0.0,
                    "std": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "p50": 0.0,
                    "p95": 0.0,
                    "p99": 0.0,
                }
            
            values = [r.value for r in records]
            
            return {
                "count": len(values),
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "p50": float(np.percentile(values, 50)),
                "p95": float(np.percentile(values, 95)),
                "p99": float(np.percentile(values, 99)),
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics.
        
        Returns:
            Dictionary with all metrics
        """
        with self._lock:
            all_stats = {}
            
            for metric_type in PerformanceMetricType:
                key = metric_type.value
                all_stats[key] = self.get_metric_stats(metric_type)
            
            # Add summary
            total_inferences = len(self.metrics[PerformanceMetricType.INFERENCE_TIME])
            avg_inference_time = all_stats["inference_time"]["mean"]
            
            all_stats["summary"] = {
                "total_inferences": total_inferences,
                "avg_inference_time_ms": avg_inference_time,
                "inferences_per_second": (
                    1000 / avg_inference_time if avg_inference_time > 0 else 0.0
                ),
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            return all_stats
    
    def clear(self):
        """Clear all metrics."""
        with self._lock:
            for metric_type in self.metrics:
                self.metrics[metric_type].clear()


class CacheManager:
    """Cache manager for models and features."""
    
    def __init__(self, config: Config):
        """Initialize cache manager.
        
        Args:
            config: Service configuration
        """
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self.local_cache: Dict[str, Any] = {}
        self.disk_cache_dir = Path("/tmp/ml_cache")
        
        # Setup based on strategy
        self._setup_cache()
    
    def _setup_cache(self):
        """Setup cache based on configuration."""
        if self.config.cache_strategy == ModelCacheStrategy.MEMORY:
            self.local_cache = {}
            logger.info("Using memory cache")
            
        elif self.config.cache_strategy == ModelCacheStrategy.DISK:
            self.disk_cache_dir.mkdir(exist_ok=True)
            logger.info(
                "Using disk cache",
                cache_dir=str(self.disk_cache_dir),
            )
            
        elif self.config.cache_strategy == ModelCacheStrategy.NONE:
            logger.info("Cache disabled")
            
        # Setup Redis if configured
        if self.config.redis_url:
            try:
                self.redis_client = redis.from_url(
                    self.config.redis_url,
                    decode_responses=False,  # Keep binary for pickled objects
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache connected", url=self.config.redis_url)
            except Exception as e:
                logger.warning(
                    "Failed to connect to Redis, falling back to local cache",
                    error=str(e),
                    url=self.config.redis_url,
                )
                self.redis_client = None
    
    def _generate_key(self, *args) -> str:
        """Generate cache key from arguments.
        
        Args:
            *args: Arguments to include in key
            
        Returns:
            Cache key
        """
        key_string = ":".join(str(arg) for arg in args)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def get(self, key_prefix: str, key_parts: List[str]) -> Optional[Any]:
        """Get item from cache.
        
        Args:
            key_prefix: Key prefix
            key_parts: Additional key parts
            
        Returns:
            Cached item or None
        """
        cache_key = self._generate_key(key_prefix, *key_parts)
        
        # Try Redis first
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    return pickle.loads(cached_data)
            except Exception as e:
                logger.warning("Redis cache get failed", error=str(e))
                self.redis_client = None  # Disable Redis on error
        
        # Try local cache
        if self.config.cache_strategy == ModelCacheStrategy.MEMORY:
            return self.local_cache.get(cache_key)
        
        # Try disk cache
        elif self.config.cache_strategy == ModelCacheStrategy.DISK:
            cache_file = self.disk_cache_dir / f"{cache_key}.pkl"
            if cache_file.exists():
                try:
                    with open(cache_file, 'rb') as f:
                        return pickle.load(f)
                except Exception as e:
                    logger.warning("Disk cache read failed", error=str(e))
                    cache_file.unlink(missing_ok=True)
        
        return None
    
    def set(self, key_prefix: str, key_parts: List[str], value: Any, ttl: int = None):
        """Set item in cache.
        
        Args:
            key_prefix: Key prefix
            key_parts: Additional key parts
            value: Value to cache
            ttl: Time-to-live in seconds (optional)
        """
        if ttl is None:
            ttl = self.config.redis_cache_ttl
        
        cache_key = self._generate_key(key_prefix, *key_parts)
        
        # Store in Redis
        if self.redis_client:
            try:
                serialized = pickle.dumps(value)
                self.redis_client.setex(cache_key, ttl, serialized)
                return
            except Exception as e:
                logger.warning("Redis cache set failed", error=str(e))
                self.redis_client = None  # Disable Redis on error
        
        # Store in memory cache
        if self.config.cache_strategy == ModelCacheStrategy.MEMORY:
            self.local_cache[cache_key] = value
            
            # Limit cache size
            if len(self.local_cache) > 1000:  # Limit to 1000 items
                # Remove oldest items (simple FIFO)
                for old_key in list(self.local_cache.keys())[:100]:
                    del self.local_cache[old_key]
        
        # Store in disk cache
        elif self.config.cache_strategy == ModelCacheStrategy.DISK:
            cache_file = self.disk_cache_dir / f"{cache_key}.pkl"
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(value, f)
            except Exception as e:
                logger.warning("Disk cache write failed", error=str(e))
    
    def delete(self, key_prefix: str, key_parts: List[str]):
        """Delete item from cache.
        
        Args:
            key_prefix: Key prefix
            key_parts: Additional key parts
        """
        cache_key = self._generate_key(key_prefix, *key_parts)
        
        # Delete from Redis
        if self.redis_client:
            try:
                self.redis_client.delete(cache_key)
            except Exception:
                pass
        
        # Delete from local cache
        if cache_key in self.local_cache:
            del self.local_cache[cache_key]
        
        # Delete from disk cache
        cache_file = self.disk_cache_dir / f"{cache_key}.pkl"
        if cache_file.exists():
            cache_file.unlink(missing_ok=True)
    
    def clear(self):
        """Clear all cache."""
        # Clear Redis
        if self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception:
                pass
        
        # Clear local cache
        self.local_cache.clear()
        
        # Clear disk cache
        if self.disk_cache_dir.exists():
            for cache_file in self.disk_cache_dir.glob("*.pkl"):
                cache_file.unlink(missing_ok=True)


def validate_features(features: np.ndarray, expected_count: int) -> Tuple[bool, str]:
    """Validate feature array.
    
    Args:
        features: Feature array to validate
        expected_count: Expected number of features
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if features is None:
        return False, "Features is None"
    
    if not isinstance(features, np.ndarray):
        return False, f"Features must be numpy array, got {type(features)}"
    
    # Check shape
    if len(features.shape) != 1:
        return False, f"Features must be 1D array, shape is {features.shape}"
    
    # Check feature count
    if features.shape[0] != expected_count:
        return False, (
            f"Expected {expected_count} features, got {features.shape[0]}"
        )
    
    # Check for NaN/inf values
    if np.any(np.isnan(features)):
        return False, "Features contain NaN values"
    
    if np.any(np.isinf(features)):
        return False, "Features contain infinite values"
    
    return True, ""


def normalize_features(features: np.ndarray) -> np.ndarray:
    """Normalize features using min-max scaling.
    
    Args:
        features: Raw features
        
    Returns:
        Normalized features
    """
    # Handle edge cases
    if len(features) == 0:
        return features
    
    min_val = np.min(features)
    max_val = np.max(features)
    
    # Avoid division by zero
    if max_val - min_val < 1e-10:
        return np.zeros_like(features)
    
    return (features - min_val) / (max_val - min_val)


def calculate_feature_hash(features: np.ndarray) -> str:
    """Calculate hash for feature array.
    
    Args:
        features: Feature array
        
    Returns:
        SHA256 hash of features
    """
    # Convert to bytes and hash
    features_bytes = features.tobytes()
    return hashlib.sha256(features_bytes).hexdigest()


class FeatureValidator:
    """Feature validation and preprocessing."""
    
    def __init__(
        self,
        expected_feature_count: int,
        scaling_enabled: bool = True,
        imputation_enabled: bool = True,
    ):
        """Initialize feature validator.
        
        Args:
            expected_feature_count: Expected number of features
            scaling_enabled: Enable feature scaling
            imputation_enabled: Enable missing value imputation
        """
        self.expected_feature_count = expected_feature_count
        self.scaling_enabled = scaling_enabled
        self.imputation_enabled = imputation_enabled
        
        # Statistics for adaptive normalization
        self.feature_stats: Optional[Dict[str, np.ndarray]] = None
        self.stats_initialized = False
        
    def validate_and_preprocess(self, features: np.ndarray) -> Tuple[np.ndarray, List[str]]:
        """Validate features and apply preprocessing.
        
        Args:
            features: Raw features
            
        Returns:
            Tuple of (processed_features, warnings)
        """
        warnings = []
        
        # Validate
        is_valid, error_msg = validate_features(features, self.expected_feature_count)
        if not is_valid:
            raise ValueError(f"Invalid features: {error_msg}")
        
        # Create copy to avoid modifying original
        processed = features.copy()
        
        # Impute missing values
        if self.imputation_enabled:
            nan_mask = np.isnan(processed)
            if np.any(nan_mask):
                # Replace NaN with feature mean
                feature_mean = np.nanmean(processed)
                processed[nan_mask] = feature_mean
                warnings.append("NaN values imputed with feature mean")
        
        # Scale features
        if self.scaling_enabled:
            processed = normalize_features(processed)
        
        return processed, warnings
    
    def update_stats(self, features: np.ndarray):
        """Update feature statistics for adaptive normalization.
        
        Args:
            features: Feature array
        """
        if not self.stats_initialized:
            self.feature_stats = {
                "mean": features.copy(),
                "std": np.zeros_like(features),
                "min": features.copy(),
                "max": features.copy(),
                "count": 1,
            }
            self.stats_initialized = True
        else:
            # Update running statistics
            stats = self.feature_stats
            n = stats["count"]
            
            # Update mean using Welford's algorithm
            delta = features - stats["mean"]
            stats["mean"] += delta / (n + 1)
            
            # Update std (needs M2 statistic)
            # For simplicity, we'll just track min/max for now
            stats["min"] = np.minimum(stats["min"], features)
            stats["max"] = np.maximum(stats["max"], features)
            stats["count"] += 1
    
    def adaptive_normalize(self, features: np.ndarray) -> np.ndarray:
        """Normalize features using adaptive statistics.
        
        Args:
            features: Raw features
            
        Returns:
            Normalized features
        """
        if not self.stats_initialized:
            return normalize_features(features)
        
        stats = self.feature_stats
        min_vals = stats["min"]
        max_vals = stats["max"]
        
        # Avoid division by zero
        range_vals = max_vals - min_vals
        range_vals[range_vals < 1e-10] = 1.0
        
        return (features - min_vals) / range_vals


import threading  # Add missing import at the top