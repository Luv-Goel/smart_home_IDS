"""Fusion Engine implementation for Smart Home IDS.

Implements the fusion equation from the research paper:
\hat{p}_t = σ(β₀ + β₁s_t^{dev} + β₂s_t^{flow} + β₃s_t^{dev}s_t^{flow})

And threshold optimization using:
J(τ) = C_FN * P_FN(τ) + C_FP * P_FP(τ)
"""

import asyncio
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import queue
import uuid

import numpy as np
from scipy.special import expit  # Sigmoid function
from structlog import get_logger

from ids_core.logger_enhanced import get_enhanced_logger, PerformanceTimer

from .config import Config, FusionMethod, ThresholdOptimizationMethod, ConfidenceMethod


@dataclass
class AnomalyScore:
    """Anomaly score from a source."""
    
    source_type: str  # "device", "flow", "ml"
    score: float
    confidence: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate score."""
        if not 0 <= self.score <= 1:
            raise ValueError(f"Score must be between 0 and 1, got {self.score}")
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")


@dataclass
class FusedResult:
    """Result of fusion process."""
    
    fused_id: str
    timestamp: float
    fused_score: float  # \hat{p}_t
    fused_confidence: float
    is_anomaly: bool
    severity: str  # "low", "medium", "high", "critical"
    threshold_used: float
    individual_scores: Dict[str, AnomalyScore] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "fused_id": self.fused_id,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "fused_score": self.fused_score,
            "fused_confidence": self.fused_confidence,
            "is_anomaly": self.is_anomaly,
            "severity": self.severity,
            "threshold_used": self.threshold_used,
            "individual_scores": {
                source: {
                    "score": score.score,
                    "confidence": score.confidence,
                }
                for source, score in self.individual_scores.items()
            },
            "metadata": self.metadata,
        }


@dataclass
class ThresholdStatistics:
    """Statistics for threshold optimization."""
    
    threshold: float
    false_positive_rate: float
    false_negative_rate: float
    total_cost: float
    optimal: bool = False
    samples_used: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "threshold": self.threshold,
            "false_positive_rate": self.false_positive_rate,
            "false_negative_rate": self.false_negative_rate,
            "total_cost": self.total_cost,
            "optimal": self.optimal,
            "samples_used": self.samples_used,
        }


class FusionEngine:
    """Core fusion engine implementing research paper equations."""
    
    def __init__(self, config: Config):
        """Initialize fusion engine.
        
        Args:
            config: Service configuration
        """
        self.config = config
        self.logger = get_enhanced_logger(
            name="fusion_engine",
            service_name=config.service_name,
            node_id=config.node_id,
        )
        
        # Queues and workers
        self.input_queue = queue.Queue(maxsize=config.max_queue_size)
        self.output_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._workers: List[threading.Thread] = []
        
        # Score buffers for windowed operations
        self.score_buffer: deque = deque(maxlen=config.cache_window)
        self.label_buffer: deque = deque(maxlen=config.cache_window)  # Ground truth labels
        
        # Current fused threshold (learned from data)
        self.current_threshold = config.fused_anomaly_threshold
        self.threshold_history: List[ThresholdStatistics] = []
        
        # Performance metrics
        self.total_fusions = 0
        self.false_positives = 0
        self.false_negatives = 0
        self.true_positives = 0
        self.true_negatives = 0
        
        # Initialize workers
        self._setup_workers()
        
        self.logger.info(
            "Fusion engine initialized",
            method=config.fusion_method.value,
            threshold_method=config.threshold_optimization.value,
            fusion_coefficients=config.fusion_coefficients,
            cost_matrix=config.cost_matrix,
        )
    
    def _setup_workers(self):
        """Setup worker threads."""
        # Fusion worker
        worker = threading.Thread(
            target=self._fusion_worker,
            name="fusion-worker",
            daemon=True,
        )
        self._workers.append(worker)
        worker.start()
        
        # Threshold optimization worker
        if self.config.threshold_optimization != ThresholdOptimizationMethod.MANUAL:
            worker = threading.Thread(
                target=self._threshold_optimization_worker,
                name="threshold-optimizer",
                daemon=True,
            )
            self._workers.append(worker)
            worker.start()
        
        self.logger.info("Workers started", count=len(self._workers))
    
    async def startup(self):
        """Startup fusion engine."""
        self.logger.info("Starting fusion engine")
        
        # Warmup if needed
        if self.config.optimization_steps > 0:
            await self._initialize_threshold()
        
        self.logger.info("Fusion engine started")
    
    async def shutdown(self):
        """Shutdown fusion engine."""
        self.logger.info("Shutting down fusion engine")
        
        # Signal workers to stop
        self._stop_event.set()
        
        # Clear queues
        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except queue.Empty:
                break
        
        # Wait for workers
        for worker in self._workers:
            worker.join(timeout=5.0)
        
        # Save threshold statistics
        await self._save_threshold_statistics()
        
        self.logger.info("Fusion engine shutdown complete")
    
    async def _initialize_threshold(self):
        """Initialize threshold with warmup data."""
        self.logger.info("Initializing threshold with warmup data")
        
        # Create synthetic warmup data
        warmup_samples = min(100, self.config.optimization_steps)
        
        for _ in range(warmup_samples):
            # Generate synthetic scores (mostly normal traffic)
            device_score = np.random.beta(1, 10)  # Mostly low scores
            flow_score = np.random.beta(1, 10)
            
            scores = {
                "device": AnomalyScore(
                    source_type="device",
                    score=device_score,
                    confidence=0.8,
                ),
                "flow": AnomalyScore(
                    source_type="flow", 
                    score=flow_score,
                    confidence=0.8,
                ),
            }
            
            # 5% anomalies for warmup
            if np.random.random() < 0.05:
                scores["device"].score = np.random.beta(10, 1)
                scores["flow"].score = np.random.beta(10, 1)
            
            # Add to buffer (without labels for now)
            self.score_buffer.append(scores)
        
        # Run initial threshold optimization
        self._optimize_threshold()
        
        self.logger.info(
            "Threshold initialized",
            threshold=self.current_threshold,
            samples=len(self.score_buffer),
        )
    
    def fuse_scores(self, scores: Dict[str, AnomalyScore]) -> Tuple[float, float]:
        """Fuse anomaly scores using the selected method.
        
        Args:
            scores: Dictionary of anomaly scores from different sources
            
        Returns:
            Tuple of (fused_score, fused_confidence)
            
        Raises:
            ValueError: If no valid scores provided
        """
        if not scores:
            raise ValueError("No scores to fuse")
        
        # Filter valid scores
        valid_scores = {
            source: score 
            for source, score in scores.items() 
            if score.confidence >= self.config.min_confidence
        }
        
        if not valid_scores:
            self.logger.warning("No valid scores with sufficient confidence")
            return 0.0, 0.0
        
        # Apply selected fusion method
        method = self.config.fusion_method
        
        if method == FusionMethod.LINEAR_FUSION:
            fused_score, fused_confidence = self._linear_fusion(valid_scores)
        elif method == FusionMethod.WEIGHTED_AVERAGE:
            fused_score, fused_confidence = self._weighted_average(valid_scores)
        elif method == FusionMethod.MAX_POOLING:
            fused_score, fused_confidence = self._max_pooling(valid_scores)
        elif method == FusionMethod.MIN_POOLING:
            fused_score, fused_confidence = self._min_pooling(valid_scores)
        elif method == FusionMethod.PRODUCT:
            fused_score, fused_confidence = self._product_fusion(valid_scores)
        elif method == FusionMethod.VOTING:
            fused_score, fused_confidence = self._voting_fusion(valid_scores)
        else:
            # Default to weighted average
            fused_score, fused_confidence = self._weighted_average(valid_scores)
        
        return fused_score, fused_confidence
    
    def _linear_fusion(self, scores: Dict[str, AnomalyScore]) -> Tuple[float, float]:
        """Linear fusion from research paper.
        
        \hat{p}_t = σ(β₀ + β₁s_t^{dev} + β₂s_t^{flow} + β₃s_t^{dev}s_t^{flow})
        
        Args:
            scores: Dictionary of anomaly scores
            
        Returns:
            Tuple of (fused_score, fused_confidence)
        """
        # Extract device and flow scores
        device_score = scores.get("device", AnomalyScore("device", 0.0, 0.0))
        flow_score = scores.get("flow", AnomalyScore("flow", 0.0, 0.0))
        
        # Get coefficients
        beta_0 = self.config.beta_0
        beta_1 = self.config.beta_1
        beta_2 = self.config.beta_2
        beta_3 = self.config.beta_3
        
        # Apply linear combination
        linear_term = (
            beta_0 +
            beta_1 * device_score.score +
            beta_2 * flow_score.score +
            beta_3 * device_score.score * flow_score.score
        )
        
        # Apply sigmoid activation
        fused_score = expit(linear_term)  # σ(x) = 1 / (1 + exp(-x))
        
        # Calculate confidence from individual confidences
        confidences = [s.confidence for s in scores.values()]
        fused_confidence = np.mean(confidences) if confidences else 0.0
        
        return fused_score, fused_confidence
    
    def _weighted_average(self, scores: Dict[str, AnomalyScore]) -> Tuple[float, float]:
        """Weighted average fusion.
        
        Args:
            scores: Dictionary of anomaly scores
            
        Returns:
            Tuple of (fused_score, fused_confidence)
        """
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for score in scores.values():
            weight = score.confidence
            weighted_sum += score.score * weight
            weight_sum += weight
        
        if weight_sum == 0:
            return 0.0, 0.0
        
        fused_score = weighted_sum / weight_sum
        fused_confidence = weight_sum / len(scores)  # Average confidence
        
        return fused_score, fused_confidence
    
    def _max_pooling(self, scores: Dict[str, AnomalyScore]) -> Tuple[float, float]:
        """Max pooling fusion (worst-case).
        
        Args:
            scores: Dictionary of anomaly scores
            
        Returns:
            Tuple of (fused_score, fused_confidence)
        """
        max_score = max(s.score for s in scores.values())
        max_confidence = max(s.confidence for s in scores.values())
        
        return max_score, max_confidence
    
    def _min_pooling(self, scores: Dict[str, AnomalyScore]) -> Tuple[float, float]:
        """Min pooling fusion (best-case).
        
        Args:
            scores: Dictionary of anomaly scores
            
        Returns:
            Tuple of (fused_score, fused_confidence)
        """
        min_score = min(s.score for s in scores.values())
        min_confidence = min(s.confidence for s in scores.values())
        
        return min_score, min_confidence
    
    def _product_fusion(self, scores: Dict[str, AnomalyScore]) -> Tuple[float, float]:
        """Product fusion.
        
        Args:
            scores: Dictionary of anomaly scores
            
        Returns:
            Tuple of (fused_score, fused_confidence)
        """
        fused_score = 1.0
        confidences = []
        
        for score in scores.values():
            fused_score *= score.score
            confidences.append(score.confidence)
        
        fused_confidence = np.mean(confidences) if confidences else 0.0
        
        return fused_score, fused_confidence
    
    def _voting_fusion(self, scores: Dict[str, AnomalyScore]) -> Tuple[float, float]:
        """Voting fusion.
        
        Args:
            scores: Dictionary of anomaly scores
            
        Returns:
            Tuple of (fused_score, fused_confidence)
        """
        # Threshold individual scores
        device_threshold = self.config.device_anomaly_threshold
        flow_threshold = self.config.flow_anomaly_threshold
        
        votes = []
        confidences = []
        
        for source, score in scores.items():
            if source == "device":
                threshold = device_threshold
            elif source == "flow":
                threshold = flow_threshold
            else:
                threshold = 0.5  # Default
            
            vote = 1 if score.score > threshold else 0
            votes.append(vote)
            confidences.append(score.confidence)
        
        # Majority vote
        fused_score = 1.0 if sum(votes) > len(votes) / 2 else 0.0
        fused_confidence = np.mean(confidences) if confidences else 0.0
        
        return fused_score, fused_confidence
    
    def determine_anomaly(self, fused_score: float, confidence: float) -> Tuple[bool, str, float]:
        """Determine if fused score indicates anomaly and its severity.
        
        Args:
            fused_score: Fused anomaly score
            confidence: Fusion confidence
            
        Returns:
            Tuple of (is_anomaly, severity, threshold_used)
        """
        # Apply confidence adjustment to threshold
        # Lower confidence -> higher threshold (more conservative)
        confidence_factor = 1.0 / max(0.1, confidence)
        adjusted_threshold = min(
            self.current_threshold * confidence_factor,
            0.95  # Cap at 0.95
        )
        
        is_anomaly = fused_score > adjusted_threshold
        
        # Determine severity
        severity = "low"
        for level, threshold in self.config.severity_thresholds.items():
            if fused_score > threshold:
                severity = level
            else:
                break
        
        return is_anomaly, severity, adjusted_threshold
    
    def _optimize_threshold(self):
        """Optimize threshold using cost-aware optimization.
        
        J(τ) = C_FN * P_FN(τ) + C_FP * P_FP(τ)
        """
        if len(self.score_buffer) < self.config.fusion_window_size:
            # Not enough data for optimization
            return
        
        self.logger.debug(
            "Optimizing threshold",
            samples=len(self.score_buffer),
            window_size=self.config.fusion_window_size,
        )
        
        # Extract fused scores from buffer
        fused_scores = []
        labels = []  # Ground truth labels
        
        for scores in self.score_buffer:
            # Fuse scores
            try:
                fused_score, _ = self.fuse_scores(scores)
                fused_scores.append(fused_score)
                
                # TODO: Get ground truth labels when available
                # For now, use threshold-based pseudo-labels
                label = 1 if fused_score > 0.8 else 0
                labels.append(label)
            except Exception as e:
                self.logger.warning("Failed to fuse score for optimization", error=str(e))
                continue
        
        if not fused_scores:
            return
        
        # Calculate costs for different thresholds
        thresholds = np.linspace(0.1, 0.9, 50)
        best_cost = float('inf')
        best_threshold = self.current_threshold
        
        for threshold in thresholds:
            fp_rate, fn_rate = self._calculate_error_rates(fused_scores, labels, threshold)
            
            # Calculate total cost
            total_cost = (
                self.config.cost_false_positive * fp_rate +
                self.config.cost_false_negative * fn_rate
            )
            
            # Update statistics
            stats = ThresholdStatistics(
                threshold=threshold,
                false_positive_rate=fp_rate,
                false_negative_rate=fn_rate,
                total_cost=total_cost,
                samples_used=len(fused_scores),
            )
            
            self.threshold_history.append(stats)
            
            # Update best threshold
            if total_cost < best_cost:
                best_cost = total_cost
                best_threshold = threshold
        
        # Update current threshold with momentum
        old_threshold = self.current_threshold
        self.current_threshold = (
            old_threshold * 0.7 +  # Keep some history
            best_threshold * 0.3   # Incorporate new optimal
        )
        
        self.logger.info(
            "Threshold optimized",
            old_threshold=old_threshold,
            new_threshold=best_threshold,
            current_threshold=self.current_threshold,
            best_cost=best_cost,
            samples=len(fused_scores),
        )
    
    def _calculate_error_rates(
        self,
        scores: List[float],
        labels: List[int],
        threshold: float,
    ) -> Tuple[float, float]:
        """Calculate false positive and false negative rates.
        
        Args:
            scores: Anomaly scores
            labels: Ground truth labels (0 = normal, 1 = anomaly)
            threshold: Decision threshold
            
        Returns:
            Tuple of (false_positive_rate, false_negative_rate)
        """
        if not scores or not labels:
            return 0.0, 0.0
        
        # Convert to numpy arrays
        scores_np = np.array(scores)
        labels_np = np.array(labels)
        
        # Predictions
        predictions = (scores_np > threshold).astype(int)
        
        # Calculate confusion matrix
        true_positives = np.sum((predictions == 1) & (labels_np == 1))
        false_positives = np.sum((predictions == 1) & (labels_np == 0))
        false_negatives = np.sum((predictions == 0) & (labels_np == 1))
        
        # Calculate rates
        fp_rate = false_positives / max(np.sum(labels_np == 0), 1)
        fn_rate = false_negatives / max(np.sum(labels_np == 1), 1)
        
        return fp_rate, fn_rate
    
    async def process_scores(self, scores: Dict[str, AnomalyScore]) -> FusedResult:
        """Process and fuse anomaly scores.
        
        Args:
            scores: Dictionary of anomaly scores
            
        Returns:
            Fused result
        """
        request_id = str(uuid.uuid4())
        
        # Add to input queue for processing
        request = {
            "request_id": request_id,
            "scores": scores,
            "timestamp": time.time(),
        }
        
        try:
            self.input_queue.put(request, timeout=1.0)
        except queue.Full:
            raise RuntimeError("Fusion engine queue is full")
        
        # Wait for result (simplified - in production use callbacks)
        start_time = time.time()
        timeout = 5.0
        
        while time.time() - start_time < timeout:
            try:
                result = self.output_queue.get_nowait()
                if result["request_id"] == request_id:
                    return result["result"]
            except queue.Empty:
                await asyncio.sleep(0.001)
        
        raise TimeoutError("Fusion processing timeout")
    
    def _fusion_worker(self):
        """Worker thread for fusion processing."""
        worker_id = threading.current_thread().name
        
        self.logger.debug("Starting fusion worker", worker_id=worker_id)
        
        while not self._stop_event.is_set():
            try:
                # Get request from queue
                request = self.input_queue.get(timeout=0.1)
                
                start_time = time.time()
                request_id = request["request_id"]
                scores = request["scores"]
                
                try:
                    # Fuse scores
                    fused_score, fused_confidence = self.fuse_scores(scores)
                    
                    # Determine anomaly
                    is_anomaly, severity, threshold_used = self.determine_anomaly(
                        fused_score, fused_confidence
                    )
                    
                    # Create result
                    result = FusedResult(
                        fused_id=request_id,
                        timestamp=time.time(),
                        fused_score=fused_score,
                        fused_confidence=fused_confidence,
                        is_anomaly=is_anomaly,
                        severity=severity,
                        threshold_used=threshold_used,
                        individual_scores=scores,
                        metadata={
                            "worker_id": worker_id,
                            "processing_time_ms": (time.time() - start_time) * 1000,
                        }
                    )
                    
                    # Update statistics
                    self.total_fusions += 1
                    if is_anomaly:
                        # TODO: Update confusion matrix with ground truth
                        pass
                    
                    # Put result in output queue
                    self.output_queue.put({
                        "request_id": request_id,
                        "result": result,
                    })
                    
                    # Add to buffer for threshold optimization
                    self.score_buffer.append(scores)
                    
                    self.logger.debug(
                        "Fusion completed",
                        request_id=request_id,
                        fused_score=fused_score,
                        is_anomaly=is_anomaly,
                        severity=severity,
                        processing_time_ms=(time.time() - start_time) * 1000,
                    )
                    
                except Exception as e:
                    self.logger.error(
                        "Fusion failed",
                        error=str(e),
                        request_id=request_id,
                        exc_info=True,
                    )
                    
                finally:
                    self.input_queue.task_done()
                    
            except queue.Empty:
                # No requests, continue
                continue
            except Exception as e:
                self.logger.error(
                    "Fusion worker error",
                    error=str(e),
                    worker_id=worker_id,
                    exc_info=True,
                )
                time.sleep(1.0)  # Avoid tight error loops
        
        self.logger.debug("Stopping fusion worker", worker_id=worker_id)
    
    def _threshold_optimization_worker(self):
        """Worker thread for threshold optimization."""
        worker_id = threading.current_thread().name
        
        self.logger.debug("Starting threshold optimization worker", worker_id=worker_id)
        
        optimization_interval = 300  # 5 minutes
        
        while not self._stop_event.is_set():
            try:
                # Wait for optimization interval
                self._stop_event.wait(optimization_interval)
                
                if self._stop_event.is_set():
                    break
                
                # Check if we have enough data
                if len(self.score_buffer) >= self.config.fusion_window_size:
                    self._optimize_threshold()
                
            except Exception as e:
                self.logger.error(
                    "Threshold optimization worker error",
                    error=str(e),
                    worker_id=worker_id,
                    exc_info=True,
                )
        
        self.logger.debug("Stopping threshold optimization worker", worker_id=worker_id)
    
    async def _save_threshold_statistics(self):
        """Save threshold statistics (to be implemented)."""
        # TODO: Save to database/file
        self.logger.info(
            "Threshold statistics",
            history_length=len(self.threshold_history),
            current_threshold=self.current_threshold,
            total_fusions=self.total_fusions,
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics.
        
        Returns:
            Dictionary with engine statistics
        """
        return {
            "engine": {
                "node_id": self.config.node_id,
                "total_fusions": self.total_fusions,
                "false_positives": self.false_positives,
                "false_negatives": self. false_negatives,
                "true_positives": self.true_positives,
                "true_negatives": self.true_negatives,
                "current_threshold": self.current_threshold,
                "queue_size": self.input_queue.qsize(),
                "buffer_size": len(self.score_buffer),
                "workers": len(self._workers),
            },
            "threshold_history": {
                "count": len(self.threshold_history),
                "latest": (
                    self.threshold_history[-1].to_dict()
                    if self.threshold_history else None
                ),
            },
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
        
        # Check queue health
        queue_size = self.input_queue.qsize()
        queue_capacity = self.input_queue.maxsize
        queue_utilization = queue_size / queue_capacity if queue_capacity > 0 else 0
        
        health["checks"]["queue_health"] = {
            "status": "ok" if queue_utilization < 0.9 else "warning",
            "message": f"Queue utilization: {queue_utilization:.1%}",
            "queue_size": queue_size,
            "queue_capacity": queue_capacity,
        }
        
        # Check workers
        alive_workers = sum(1 for w in self._workers if w.is_alive())
        total_workers = len(self._workers)
        
        health["checks"]["workers"] = {
            "status": "ok" if alive_workers == total_workers else "warning",
            "message": f"{alive_workers}/{total_workers} workers active",
            "alive_workers": alive_workers,
        }
        
        # Check buffer
        buffer_size = len(self.score_buffer)
        buffer_min = 100  # Minimum recommended buffer size
        
        health["checks"]["buffer"] = {
            "status": "ok" if buffer_size >= buffer_min else "warning",
            "message": f"Buffer size: {buffer_size}",
            "buffer_size": buffer_size,
            "minimum_recommended": buffer_min,
        }
        
        return health