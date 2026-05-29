"""ONNX Runtime detector for ML inference.

This module provides ONNX Runtime implementation for efficient
inference on edge devices (including ARM64/Raspberry Pi).
"""

import os
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import onnxruntime as ort

from ids_ml_plugins import (
    BaseAnomalyDetector,
    ModelMetadata,
    InferenceResult,
    ModelType,
    InferenceBackend,
)


@dataclass
class ONNXRuntimeConfig:
    """Configuration for ONNX Runtime."""
    
    # Execution provider
    execution_provider: str = "cpu"  # Options: cpu, cuda, tensorrt, openvino
    use_gpu: bool = False
    gpu_device_id: int = 0
    
    # Performance options
    intra_op_num_threads: int = 0  # 0 means auto
    inter_op_num_threads: int = 0  # 0 means auto
    execution_mode: str = "sequential"  # sequential, parallel
    graph_optimization_level: int = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    
    # Memory optimization
    enable_cpu_mem_arena: bool = True
    enable_mem_pattern: bool = True
    arena_extend_strategy: str = "kSameAsRequested"  # kNextPowerOfTwo, kSameAsRequested
    
    # Cache optimization for Raspberry Pi
    enable_model_cache: bool = True
    cache_size_mb: int = 100
    
    def to_session_options(self) -> ort.SessionOptions:
        """Convert to ONNX Runtime SessionOptions.
        
        Returns:
            Configured SessionOptions
        """
        options = ort.SessionOptions()
        
        # Set optimization level
        options.graph_optimization_level = self.graph_optimization_level
        
        # Set thread configuration
        if self.intra_op_num_threads > 0:
            options.intra_op_num_threads = self.intra_op_num_threads
        if self.inter_op_num_threads > 0:
            options.inter_op_num_threads = self.inter_op_num_threads
        
        # Set execution mode
        if self.execution_mode == "parallel":
            options.execution_mode = ort.ExecutionMode.ORT_PARALLEL
        else:
            options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        
        # Set memory options
        options.enable_cpu_mem_arena = self.enable_cpu_mem_arena
        options.enable_mem_pattern = self.enable_mem_pattern
        
        # Set arena extension strategy
        if self.arena_extend_strategy == "kNextPowerOfTwo":
            options.arena_extend_strategy = ort.ArenaExtendStrategy.kNextPowerOfTwo
        else:
            options.arena_extend_strategy = ort.ArenaExtendStrategy.kSameAsRequested
        
        # Enable model caching
        if self.enable_model_cache:
            cache_dir = "/tmp/onnx_cache"
            os.makedirs(cache_dir, exist_ok=True)
            options.enable_profiling = False
            options.profile_file_prefix = os.path.join(cache_dir, "profile")
        
        return options
    
    def get_providers(self) -> List[str]:
        """Get execution providers in priority order.
        
        Returns:
            List of execution providers
        """
        providers = []
        
        if self.use_gpu:
            if ort.get_device() == "GPU":
                # Try CUDA first, then fallback to CPU
                if "CUDAExecutionProvider" in ort.get_available_providers():
                    providers.append("CUDAExecutionProvider")
                if "TensorrtExecutionProvider" in ort.get_available_providers():
                    providers.append("TensorrtExecutionProvider")
        
        # Always include CPU
        providers.append("CPUExecutionProvider")
        
        return providers


class ONNXAnomalyDetector(BaseAnomalyDetector):
    """Anomaly detector using ONNX Runtime."""
    
    def __init__(
        self,
        model_metadata: ModelMetadata,
        runtime_config: Optional[ONNXRuntimeConfig] = None,
    ):
        """Initialize ONNX detector.
        
        Args:
            model_metadata: Model metadata
            runtime_config: ONNX Runtime configuration
        """
        super().__init__(model_metadata)
        self.runtime_config = runtime_config or ONNXRuntimeConfig()
        self.session: Optional[ort.InferenceSession] = None
        self.input_name: Optional[str] = None
        self.output_names: Optional[List[str]] = None
        self._batch_size = 32
        self._performance_stats: Dict[str, List[float]] = {
            "inference_time": [],
            "preprocess_time": [],
            "total_time": [],
        }
    
    def load_model(self, model_path: str) -> bool:
        """Load ONNX model.
        
        Args:
            model_path: Path to ONNX model file
            
        Returns:
            True if successful
        """
        try:
            # Create session options
            session_options = self.runtime_config.to_session_options()
            
            # Get execution providers
            providers = self.runtime_config.get_providers()
            
            # Load model
            print(f"Loading ONNX model from {model_path}")
            print(f"Using providers: {providers}")
            
            self.session = ort.InferenceSession(
                model_path,
                sess_options=session_options,
                providers=providers,
            )
            
            # Get input/output information
            model_inputs = self.session.get_inputs()
            model_outputs = self.session.get_outputs()
            
            if not model_inputs:
                raise ValueError("Model has no inputs")
            
            self.input_name = model_inputs[0].name
            
            if model_outputs:
                self.output_names = [output.name for output in model_outputs]
            else:
                raise ValueError("Model has no outputs")
            
            # Update metadata with model information
            self.metadata.input_shape = model_inputs[0].shape
            self.metadata.output_shape = model_outputs[0].shape if model_outputs else ()
            
            if len(model_inputs[0].shape) >= 2:
                self.metadata.feature_count = model_inputs[0].shape[-1]
            
            self._loaded = True
            print(f"Model loaded successfully: {self.metadata.model_id}")
            print(f"Input shape: {self.metadata.input_shape}")
            print(f"Output shape: {self.metadata.output_shape}")
            
            return True
            
        except Exception as e:
            print(f"Failed to load ONNX model: {str(e)}")
            self.session = None
            self._loaded = False
            return False
    
    def unload_model(self) -> bool:
        """Unload model.
        
        Returns:
            True if successful
        """
        try:
            if self.session:
                # ONNX Runtime doesn't have explicit unload, but we can
                # delete the session to free memory
                del self.session
                self.session = None
            
            self.input_name = None
            self.output_names = None
            self._loaded = False
            self._performance_stats.clear()
            
            return True
            
        except Exception:
            return False
    
    def preprocess_features(self, features: np.ndarray) -> np.ndarray:
        """Preprocess features for ONNX model.
        
        Args:
            features: Raw features
            
        Returns:
            Preprocessed features
        """
        start_time = time.time()
        
        # Apply base preprocessing
        features_processed = super().preprocess_features(features)
        
        # Ensure correct dtype (ONNX models typically expect float32)
        if features_processed.dtype != np.float32:
            features_processed = features_processed.astype(np.float32)
        
        # Ensure correct shape for batch inference
        if len(features_processed.shape) == 1:
            features_processed = features_processed.reshape(1, -1)
        
        # Pad features if needed
        expected_features = self.metadata.feature_count
        if expected_features > 0 and features_processed.shape[1] != expected_features:
            # Pad or truncate features
            actual_features = features_processed.shape[1]
            if actual_features < expected_features:
                # Pad with zeros
                padding = np.zeros((features_processed.shape[0], 
                                  expected_features - actual_features), 
                                 dtype=np.float32)
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
            
            # Preprocess features
            features_processed = self.preprocess_features(features)
            
            # Prepare input
            input_data = {self.input_name: features_processed}
            
            # Run inference
            inference_start = time.time()
            outputs = self.session.run(self.output_names, input_data)
            inference_time = (time.time() - inference_start) * 1000
            
            # Parse outputs
            anomaly_score, confidence, is_anomaly = self._parse_outputs(outputs, features_processed)
            
            # Record performance
            total_time = (time.time() - start_time) * 1000
            self._performance_stats["inference_time"].append(inference_time)
            self._performance_stats["total_time"].append(total_time)
            
            # Keep only last 1000 measurements
            for key in self._performance_stats:
                if len(self._performance_stats[key]) > 1000:
                    self._performance_stats[key] = self._performance_stats[key][-1000:]
            
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
                    "input_shape": list(features_processed.shape),
                    "backend": "onnx_runtime",
                    "execution_provider": self.runtime_config.execution_provider,
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
        batch_size = min(self._batch_size, len(features_batch))
        
        for i in range(0, len(features_batch), batch_size):
            batch = features_batch[i:i + batch_size]
            
            for features in batch:
                result = self.predict(features)
                results.append(result)
        
        return results
    
    def _parse_outputs(self, outputs: List[np.ndarray], features: np.ndarray) -> Tuple[float, float, bool]:
        """Parse ONNX model outputs.
        
        Args:
            outputs: Model outputs
            features: Input features
            
        Returns:
            Tuple of (anomaly_score, confidence, is_anomaly)
        """
        # Default implementation - adapt based on your model architecture
        
        if len(outputs) == 1:
            # Single output - treat as probability
            output = outputs[0]
            
            if output.shape[-1] == 1:
                # Binary classification
                anomaly_score = float(output.ravel()[0])
            elif output.shape[-1] == 2:
                # Two-class classification (normal vs anomaly)
                anomaly_score = float(output[0, 1])  # Assume anomaly is class 1
            else:
                # Multi-class - use maximum probability
                anomaly_score = float(np.max(output))
            
            # Determine anomaly based on threshold
            is_anomaly = anomaly_score > self.metadata.anomaly_threshold
            
            # Confidence is similar to score for now
            confidence = anomaly_score
            
        elif len(outputs) >= 2:
            # Multiple outputs - assume first is score, second is confidence
            anomaly_score = float(outputs[0].ravel()[0])
            confidence = float(outputs[1].ravel()[0])
            is_anomaly = anomaly_score > self.metadata.anomaly_threshold
            
        else:
            # No outputs - default values
            anomaly_score = 0.0
            confidence = 0.0
            is_anomaly = False
        
        return anomaly_score, confidence, is_anomaly
    
    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        stats = {}
        
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
        
        return stats
    
    def optimize_for_edge(self) -> ONNXRuntimeConfig:
        """Get optimization config for edge devices (Raspberry Pi).
        
        Returns:
            Optimized runtime configuration
        """
        return ONNXRuntimeConfig(
            execution_provider="cpu",
            use_gpu=False,
            intra_op_num_threads=1,  # Single thread for Raspberry Pi
            inter_op_num_threads=1,
            execution_mode="sequential",
            graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED,
            enable_cpu_mem_arena=True,
            enable_mem_pattern=True,
            arena_extend_strategy="kSameAsRequested",
            enable_model_cache=True,
            cache_size_mb=50,  # Smaller cache for Raspberry Pi
        )


def create_onnx_detector(
    model_path: str,
    model_id: str = None,
    model_type: ModelType = ModelType.RANDOM_FOREST,
    optimize_for_edge: bool = False,
) -> Optional[ONNXAnomalyDetector]:
    """Factory function to create ONNX detector.
    
    Args:
        model_path: Path to ONNX model
        model_id: Model identifier (generated if None)
        model_type: Type of model
        optimize_for_edge: Optimize for edge devices
        
    Returns:
        ONNX detector instance or None
    """
    if not os.path.exists(model_path):
        print(f"Model file not found: {model_path}")
        return None
    
    # Generate model ID if not provided
    if model_id is None:
        model_id = f"onnx_{os.path.basename(model_path)}_{uuid.uuid4().hex[:8]}"
    
    # Create metadata
    metadata = ModelMetadata(
        model_id=model_id,
        model_type=model_type,
        backend=InferenceBackend.ONNX_RUNTIME,
        version="1.0.0",
        description=f"ONNX model: {os.path.basename(model_path)}",
        created_at=datetime.utcnow().isoformat(),
        model_hash="",  # Could compute file hash here
        anomaly_threshold=0.75,
        confidence_threshold=0.8,
    )
    
    # Create runtime config
    if optimize_for_edge:
        # Default config will be optimized by detector
        runtime_config = ONNXRuntimeConfig()
    else:
        runtime_config = ONNXRuntimeConfig()
    
    # Create detector
    detector = ONNXAnomalyDetector(metadata, runtime_config)
    
    # Load model
    if detector.load_model(model_path):
        return detector
    else:
        return None