"""Inference Engine for ML Inference Service.

This module provides the core inference engine with support for
multiple backends, batching, and performance optimization.
"""

import asyncio
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import queue
import uuid

import numpy as np
from structlog import get_logger

from ids_ml_plugins import (
    BaseAnomalyDetector,
    InferenceResult,
    ModelRegistry,
    ModelMetadata,
)
from ids_ml_plugins.onnx_detector import ONNXAnomalyDetector, create_onnx_detector
from ids_ml_plugins.sklearn_detector import SklearnAnomalyDetector, create_sklearn_detector

from .config import Config, InferenceBackend, ModelCacheStrategy, InferenceMode
from .utils import PerformanceMetrics, CacheManager

logger = get_logger(__name__)


@dataclass
class InferenceRequest:
    """Inference request."""
    
    request_id: str
    features: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[callable] = None
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """Validate request."""
        if self.features is None or len(self.features.shape) != 1:
            raise ValueError("Features must be 1D array")
    
    def get_feature_vector(self) -> np.ndarray:
        """Get feature vector as numpy array."""
        return self.features.copy()


@dataclass
class InferenceResponse:
    """Inference response."""
    
    request_id: str
    result: InferenceResult
    processing_time_ms: float
    engine_metadata: Dict[str, Any] = field(default_factory=dict)


class InferenceEngine:
    """Main inference engine with support for multiple backends and batching."""
    
    def __init__(self, config: Config):
        """Initialize inference engine.
        
        Args:
            config: Service configuration
        """
        self.config = config
        self.logger = get_logger(f"inference.{config.node_id}")
        
        # Core components
        self.model_registry = ModelRegistry()
        self.cache_manager = CacheManager(config)
        self.performance_metrics = PerformanceMetrics()
        
        # Model state
        self.active_detector: Optional[BaseAnomalyDetector] = None
        self.model_loaded = False
        self.model_loading = False
        
        # Queues and workers
        self.request_queue = queue.Queue(maxsize=config.max_queue_size)
        self.response_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._workers: List[threading.Thread] = []
        
        # Performance tracking
        self.total_requests = 0
        self.failed_requests = 0
        self.avg_inference_time = 0.0
        
        # Initialize
        self._setup_workers()
        
        self.logger.info(
            "Inference engine initialized",
            node_id=config.node_id,
            backend=config.inference_backend.value,
            mode=config.inference_mode.value,
            batch_size=config.batch_size,
        )
    
    def _setup_workers(self):
        """Setup worker threads based on configuration."""
        # Inference workers
        for i in range(self.config.inference_threads):
            worker = threading.Thread(
                target=self._inference_worker,
                name=f"inference-worker-{i}",
                daemon=True,
            )
            self._workers.append(worker)
            worker.start()
            self.logger.debug("Started inference worker", worker_id=i)
        
        # Preprocessing workers
        for i in range(self.config.preprocessing_threads):
            worker = threading.Thread(
                target=self._preprocessing_worker,
                name=f"preprocessing-worker-{i}",
                daemon=True,
            )
            self._workers.append(worker)
            worker.start()
            self.logger.debug("Started preprocessing worker", worker_id=i)
    
    async def startup(self):
        """Startup inference engine."""
        self.logger.info("Starting inference engine")
        
        # Load default model
        await self.load_model(self.config.model_path)
        
        # Start workers if not already running
        if not self._workers:
            self._setup_workers()
        
        # Warmup model if configured
        if self.active_detector:
            await self._warmup_model()
        
        self.logger.info("Inference engine started")
    
    async def shutdown(self):
        """Shutdown inference engine."""
        self.logger.info("Shutting down inference engine")
        
        # Signal workers to stop
        self._stop_event.set()
        
        # Clear queues
        while not self.request_queue.empty():
            try:
                self.request_queue.get_nowait()
            except queue.Empty:
                break
        
        # Wait for workers to finish
        for worker in self._workers:
            worker.join(timeout=5.0)
        
        # Unload model
        if self.active_detector:
            self.active_detector.unload_model()
        
        # Clear registry
        self.model_registry.clear()
        
        self.logger.info("Inference engine shutdown complete")
    
    async def load_model(self, model_path: str, model_id: Optional[str] = None) -> bool:
        """Load ML model.
        
        Args:
            model_path: Path to model file
            model_id: Optional model identifier
            
        Returns:
            True if successful
        """
        if self.model_loading:
            self.logger.warning("Model loading already in progress")
            return False
        
        self.model_loading = True
        
        try:
            self.logger.info("Loading model", model_path=model_path)
            
            # Determine backend
            backend = self._detect_backend(model_path)
            
            # Create detector based on backend
            detector = self._create_detector(model_path, backend, model_id)
            
            if not detector:
                self.logger.error("Failed to create detector", backend=backend.value)
                return False
            
            # Register model
            if not self.model_registry.register_model(detector):
                self.logger.error("Failed to register model")
                return False
            
            # Set as active
            self.active_detector = detector
            self.model_loaded = True
            
            # Update performance metrics
            self.performance_metrics.record_model_load(
                model_id=detector.metadata.model_id,
                backend=backend.value,
                feature_count=detector.metadata.feature_count,
            )
            
            self.logger.info(
                "Model loaded successfully",
                model_id=detector.metadata.model_id,
                backend=backend.value,
                feature_count=detector.metadata.feature_count,
                input_shape=list(detector.metadata.input_shape),
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to load model",
                error=str(e),
                model_path=model_path,
            )
            return False
            
        finally:
            self.model_loading = False
    
    def _detect_backend(self, model_path: str) -> InferenceBackend:
        """Detect model backend from file extension.
        
        Args:
            model_path: Path to model file
            
        Returns:
            Detected backend
        """
        if self.config.inference_backend != InferenceBackend.AUTO:
            return self.config.inference_backend
        
        # Detect from file extension
        model_path_lower = model_path.lower()
        
        if model_path_lower.endswith('.onnx'):
            return InferenceBackend.ONNX
        elif model_path_lower.endswith('.pkl') or model_path_lower.endswith('.joblib'):
            return InferenceBackend.SCIKIT_LEARN
        elif model_path_lower.endswith('.h5') or model_path_lower.endswith('.keras'):
            # TensorFlow/Keras models could be supported in future
            return InferenceBackend.SCIKIT_LEARN
        else:
            # Default to scikit-learn
            self.logger.warning(
                "Unknown model format, defaulting to scikit-learn",
                model_path=model_path,
            )
            return InferenceBackend.SCIKIT_LEARN
    
    def _create_detector(
        self,
        model_path: str,
        backend: InferenceBackend,
        model_id: Optional[str] = None,
    ) -> Optional[BaseAnomalyDetector]:
        """Create detector instance.
        
        Args:
            model_path: Path to model file
            backend: Model backend
            model_id: Optional model identifier
            
        Returns:
            Detector instance or None
        """
        try:
            if backend == InferenceBackend.ONNX:
                detector = create_onnx_detector(
                    model_path=model_path,
                    model_id=model_id,
                    optimize_for_edge=self.config.optimize_for_edge,
                )
            elif backend == InferenceBackend.SCIKIT_LEARN:
                detector = create_sklearn_detector(
                    model_path=model_path,
                    model_id=model_id,
                    optimize_for_edge=self.config.optimize_for_edge,
                )
            else:
                self.logger.error("Unsupported backend", backend=backend.value)
                return None
            
            return detector
            
        except Exception as e:
            self.logger.error(
                "Failed to create detector",
                error=str(e),
                backend=backend.value,
                model_path=model_path,
            )
            return None
    
    async def _warmup_model(self):
        """Warmup model with sample data."""
        if not self.active_detector:
            return
        
        warmup_samples = 100  # Default warmup
        
        self.logger.info("Warming up model", samples=warmup_samples)
        
        # Create random features for warmup
        feature_count = self.active_detector.metadata.feature_count
        if feature_count == 0:
            feature_count = 10  # Default
        
        for i in range(warmup_samples):
            features = np.random.randn(feature_count).astype(np.float32)
            
            try:
                _ = self.active_detector.predict(features)
            except Exception as e:
                self.logger.warning(
                    "Warmup inference failed",
                    sample=i,
                    error=str(e),
                )
        
        self.logger.info("Model warmup completed")
    
    async def predict(self, features: np.ndarray, metadata: Optional[Dict] = None) -> InferenceResponse:
        """Predict anomaly for features.
        
        Args:
            features: Feature array
            metadata: Optional request metadata
            
        Returns:
            Inference response
        """
        if not self.model_loaded:
            raise RuntimeError("No model loaded")
        
        request_id = str(uuid.uuid4())
        metadata = metadata or {}
        
        # Create request
        request = InferenceRequest(
            request_id=request_id,
            features=features,
            metadata=metadata,
        )
        
        # Submit to queue
        try:
            self.request_queue.put(request, timeout=1.0)
        except queue.Full:
            raise RuntimeError("Request queue is full")
        
        # Wait for response
        # Note: In production, you'd use callbacks or async await
        start_time = time.time()
        timeout = 10.0  # seconds
        
        while time.time() - start_time < timeout:
            try:
                response = self.response_queue.get_nowait()
                if response.request_id == request_id:
                    return response
            except queue.Empty:
                await asyncio.sleep(0.001)
        
        raise TimeoutError("Inference timeout")
    
    async def predict_batch(
        self,
        features_batch: List[np.ndarray],
        metadata: Optional[List[Dict]] = None,
    ) -> List[InferenceResponse]:
        """Predict anomalies for batch of features.
        
        Args:
            features_batch: List of feature arrays
            metadata: Optional list of metadata dictionaries
            
        Returns:
            List of inference responses
        """
        if not self.model_loaded:
            raise RuntimeError("No model loaded")
        
        if metadata is None:
            metadata = [{} for _ in range(len(features_batch))]
        
        # Submit batch requests
        requests = []
        for i, (features, meta) in enumerate(zip(features_batch, metadata)):
            request_id = str(uuid.uuid4())
            request = InferenceRequest(
                request_id=request_id,
                features=features,
                metadata={**meta, "batch_index": i},
            )
            requests.append(request)
            
            try:
                self.request_queue.put(request, timeout=1.0)
            except queue.Full:
                raise RuntimeError("Request queue is full")
        
        # Collect responses
        responses = []
        start_time = time.time()
        timeout = 30.0  # Longer timeout for batch
        
        while len(responses) < len(requests) and time.time() - start_time < timeout:
            try:
                response = self.response_queue.get_nowait()
                responses.append(response)
            except queue.Empty:
                await asyncio.sleep(0.001)
        
        # Check for timeout
        if len(responses) < len(requests):
            self.logger.warning(
                "Batch inference incomplete",
                expected=len(requests),
                received=len(responses),
                timed_out=len(requests) - len(responses),
            )
        
        # Sort by request order
        request_order = {r.request_id: i for i, r in enumerate(requests)}
        responses.sort(key=lambda r: request_order.get(r.request_id, -1))
        
        return responses
    
    def _inference_worker(self):
        """Worker thread for inference."""
        worker_id = threading.current_thread().name
        
        self.logger.debug("Starting inference worker", worker_id=worker_id)
        
        while not self._stop_event.is_set():
            try:
                # Get request from queue
                request = self.request_queue.get(timeout=0.1)
                
                start_time = time.time()
                
                try:
                    # Perform inference
                    if self.active_detector:
                        result = self.active_detector.predict(request.features)
                        
                        # Create response
                        processing_time = (time.time() - start_time) * 1000
                        response = InferenceResponse(
                            request_id=request.request_id,
                            result=result,
                            processing_time_ms=processing_time,
                            engine_metadata={
                                "worker_id": worker_id,
                                "queue_time_ms": (start_time - request.timestamp) * 1000,
                            }
                        )
                        
                        # Update metrics
                        self.total_requests += 1
                        self.avg_inference_time = (
                            (self.avg_inference_time * (self.total_requests - 1) + processing_time)
                            / self.total_requests
                        )
                        
                        # Put response in queue
                        self.response_queue.put(response, timeout=0.1)
                        
                        # Call callback if provided
                        if request.callback:
                            try:
                                request.callback(response)
                            except Exception as e:
                                self.logger.error(
                                    "Callback failed",
                                    error=str(e),
                                    request_id=request.request_id,
                                )
                    
                except Exception as e:
                    self.logger.error(
                        "Inference failed",
                        error=str(e),
                        request_id=request.request_id,
                        worker_id=worker_id,
                    )
                    self.failed_requests += 1
                
                finally:
                    self.request_queue.task_done()
                    
            except queue.Empty:
                # No requests, continue
                continue
            except Exception as e:
                self.logger.error(
                    "Worker error",
                    error=str(e),
                    worker_id=worker_id,
                )
        
        self.logger.debug("Stopping inference worker", worker_id=worker_id)
    
    def _preprocessing_worker(self):
        """Worker thread for preprocessing."""
        worker_id = threading.current_thread().name
        
        self.logger.debug("Starting preprocessing worker", worker_id=worker_id)
        
        while not self._stop_event.is_set():
            try:
                # In future, this worker could handle complex preprocessing
                # For now, preprocessing is done in the detector
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(
                    "Preprocessing worker error",
                    error=str(e),
                    worker_id=worker_id,
                )
                time.sleep(1.0)  # Avoid tight error loops
        
        self.logger.debug("Stopping preprocessing worker", worker_id=worker_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics.
        
        Returns:
            Dictionary with engine statistics
        """
        if self.active_detector:
            model_stats = self.active_detector.get_performance_stats()
        else:
            model_stats = {}
        
        return {
            "engine": {
                "node_id": self.config.node_id,
                "model_loaded": self.model_loaded,
                "active_model": self.model_registry.active_model_id,
                "total_requests": self.total_requests,
                "failed_requests": self.failed_requests,
                "success_rate": (
                    (self.total_requests - self.failed_requests) / self.total_requests
                    if self.total_requests > 0 else 1.0
                ),
                "avg_inference_time_ms": self.avg_inference_time,
                "queue_size": self.request_queue.qsize(),
                "workers": len(self._workers),
            },
            "performance": self.performance_metrics.get_all_metrics(),
            "model": model_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check.
        
        Returns:
            Health status dictionary
        """
        health = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
        }
        
        # Check model loaded
        if not self.model_loaded:
            health["status"] = "unhealthy"
            health["checks"]["model_loaded"] = {
                "status": "failed",
                "message": "No model loaded",
            }
        else:
            health["checks"]["model_loaded"] = {
                "status": "ok",
                "message": f"Model loaded: {self.model_registry.active_model_id}",
            }
        
        # Check queue health
        queue_size = self.request_queue.qsize()
        queue_capacity = self.request_queue.maxsize
        queue_utilization = queue_size / queue_capacity if queue_capacity > 0 else 0
        
        health["checks"]["queue_health"] = {
            "status": "ok" if queue_utilization < 0.9 else "warning",
            "message": f"Queue utilization: {queue_utilization:.1%}",
            "queue_size": queue_size,
            "queue_capacity": queue_capacity,
            "queue_utilization": queue_utilization,
        }
        
        # Check workers
        active_workers = sum(1 for w in self._workers if w.is_alive())
        total_workers = len(self._workers)
        
        health["checks"]["workers"] = {
            "status": "ok" if active_workers == total_workers else "warning",
            "message": f"{active_workers}/{total_workers} workers active",
            "active_workers": active_workers,
            "total_workers": total_workers,
        }
        
        return health