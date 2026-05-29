"""Fusion Engine for Smart Home IDS.

This package provides a cost-aware fusion engine that combines multiple
anomaly detection results using the fusion equation:

\hat{p}_t = \sigma(\beta_0 + \beta_1 s_t^{dev} + \beta_2 s_t^{flow} + \beta_3 s_t^{dev}s_t^{flow})

And threshold optimization using:

J(\tau)=C_{FN}P_{FN}(\tau)+C_{FP}P_{FP}(\tau)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

__version__ = "0.1.0"


class AnomalyType(Enum):
    """Types of anomalies."""
    DEVICE_ANOMALY = "device_anomaly"
    FLOW_ANOMALY = "flow_anomaly"
    NETWORK_ANOMALY = "network_anomaly"
    PROTOCOL_ANOMALY = "protocol_anomaly"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"


class SeverityLevel(Enum):
    """Severity levels for anomalies."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AnomalyScore:
    """Individual anomaly score from a detector."""
    
    anomaly_type: AnomalyType
    score: float  # Between 0 and 1
    confidence: float  # Between 0 and 1
    detector_id: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate score range."""
        if not 0 <= self.score <= 1:
            raise ValueError(f"Score must be between 0 and 1, got {self.score}")
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")


@dataclass
class FusionResult:
    """Result from fusion engine."""
    
    fused_score: float  # Combined score between 0 and 1
    is_anomaly: bool
    confidence: float
    anomaly_type: AnomalyType
    severity: SeverityLevel
    component_scores: List[AnomalyScore]
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and compute severity."""
        if not 0 <= self.fused_score <= 1:
            raise ValueError(f"Fused score must be between 0 and 1, got {self.fused_score}")
        
        # Ensure severity is set
        if not self.severity:
            self.severity = self._compute_severity()
    
    def _compute_severity(self) -> SeverityLevel:
        """Compute severity based on fused score."""
        if self.fused_score >= 0.9:
            return SeverityLevel.CRITICAL
        elif self.fused_score >= 0.7:
            return SeverityLevel.HIGH
        elif self.fused_score >= 0.5:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW


@dataclass
class FusionWeights:
    """Weights for fusion equation."""
    
    beta_0: float = 0.0  # Bias term
    beta_1: float = 1.0  # Device anomaly weight
    beta_2: float = 1.0  # Flow anomaly weight
    beta_3: float = 0.5  # Interaction term weight
    
    def __post_init__(self):
        """Validate weights."""
        # Weights can be any real number, but typically non-negative
        if self.beta_1 < 0 or self.beta_2 < 0:
            raise ValueError("Weights beta_1 and beta_2 should be non-negative")


@dataclass
class CostParameters:
    """Cost parameters for threshold optimization."""
    
    cost_false_negative: float = 10.0  # Cost of missing an attack (C_FN)
    cost_false_positive: float = 1.0   # Cost of false alarm (C_FP)
    
    def __post_init__(self):
        """Validate costs."""
        if self.cost_false_negative <= 0 or self.cost_false_positive <= 0:
            raise ValueError("Costs must be positive")


class BaseFusionEngine(ABC):
    """Base class for fusion engines."""
    
    def __init__(
        self,
        weights: Optional[FusionWeights] = None,
        costs: Optional[CostParameters] = None,
        anomaly_threshold: float = 0.5,
    ):
        """Initialize fusion engine.
        
        Args:
            weights: Fusion weights
            costs: Cost parameters for optimization
            anomaly_threshold: Default threshold for anomaly detection
        """
        self.weights = weights or FusionWeights()
        self.costs = costs or CostParameters()
        self.anomaly_threshold = anomaly_threshold
        self._history: List[Tuple[List[AnomalyScore], FusionResult]] = []
    
    @abstractmethod
    def fuse(self, scores: List[AnomalyScore]) -> FusionResult:
        """Fuse multiple anomaly scores.
        
        Args:
            scores: List of anomaly scores
            
        Returns:
            Fusion result
        """
        pass
    
    @abstractmethod
    def optimize_threshold(self, historical_data: List[Tuple[List[AnomalyScore], bool]]) -> float:
        """Optimize anomaly threshold using cost function.
        
        Args:
            historical_data: List of (scores, ground_truth) pairs
            
        Returns:
            Optimized threshold
        """
        pass
    
    def update_weights(self, weights: FusionWeights):
        """Update fusion weights.
        
        Args:
            weights: New fusion weights
        """
        self.weights = weights
    
    def update_costs(self, costs: CostParameters):
        """Update cost parameters.
        
        Args:
            costs: New cost parameters
        """
        self.costs = costs
    
    def get_history(self) -> List[FusionResult]:
        """Get fusion history.
        
        Returns:
            List of previous fusion results
        """
        return [result for _, result in self._history]
    
    def clear_history(self):
        """Clear fusion history."""
        self._history.clear()


class LinearFusionEngine(BaseFusionEngine):
    """Linear fusion engine using the fusion equation."""
    
    def __init__(
        self,
        weights: Optional[FusionWeights] = None,
        costs: Optional[CostParameters] = None,
        anomaly_threshold: float = 0.7,
    ):
        """Initialize linear fusion engine.
        
        Args:
            weights: Fusion weights
            costs: Cost parameters
            anomaly_threshold: Anomaly threshold
        """
        super().__init__(weights, costs, anomaly_threshold)
        
        # Initialize statistics
        self._false_positives = 0
        self._false_negatives = 0
        self._true_positives = 0
        self._true_negatives = 0
        self._total_samples = 0
    
    def _sigmoid(self, x: float) -> float:
        """Sigmoid function.
        
        Args:
            x: Input value
            
        Returns:
            Sigmoid of x
        """
        return 1.0 / (1.0 + np.exp(-x))
    
    def _extract_scores(self, scores: List[AnomalyScore]) -> Tuple[float, float]:
        """Extract device and flow scores from anomaly scores.
        
        Args:
            scores: List of anomaly scores
            
        Returns:
            Tuple of (device_score, flow_score)
        """
        device_score = 0.0
        flow_score = 0.0
        
        for score in scores:
            if score.anomaly_type == AnomalyType.DEVICE_ANOMALY:
                device_score = max(device_score, score.score * score.confidence)
            elif score.anomaly_type == AnomalyType.FLOW_ANOMALY:
                flow_score = max(flow_score, score.score * score.confidence)
        
        return device_score, flow_score
    
    def fuse(self, scores: List[AnomalyScore]) -> FusionResult:
        """Fuse scores using the linear fusion equation.
        
        Fusion equation:
        \hat{p}_t = \sigma(\beta_0 + \beta_1 s_t^{dev} + \beta_2 s_t^{flow} + \beta_3 s_t^{dev}s_t^{flow})
        
        Args:
            scores: List of anomaly scores
            
        Returns:
            Fusion result
        """
        # Extract device and flow scores
        device_score, flow_score = self._extract_scores(scores)
        
        # Apply fusion equation
        linear_term = (
            self.weights.beta_0 +
            self.weights.beta_1 * device_score +
            self.weights.beta_2 * flow_score +
            self.weights.beta_3 * device_score * flow_score
        )
        
        # Apply sigmoid to get probability
        fused_probability = self._sigmoid(linear_term)
        
        # Determine anomaly
        is_anomaly = fused_probability > self.anomaly_threshold
        
        # Compute overall confidence (average of component confidences)
        if scores:
            confidence = np.mean([s.confidence for s in scores])
        else:
            confidence = 0.0
        
        # Determine anomaly type
        anomaly_type = self._determine_anomaly_type(scores, device_score, flow_score)
        
        # Create result
        result = FusionResult(
            fused_score=fused_probability,
            is_anomaly=is_anomaly,
            confidence=confidence,
            anomaly_type=anomaly_type,
            severity=None,  # Will be computed in __post_init__
            component_scores=scores,
            timestamp=np.mean([s.timestamp for s in scores]) if scores else 0.0,
            metadata={
                "device_score": device_score,
                "flow_score": flow_score,
                "linear_term": linear_term,
                "weights": {
                    "beta_0": self.weights.beta_0,
                    "beta_1": self.weights.beta_1,
                    "beta_2": self.weights.beta_2,
                    "beta_3": self.weights.beta_3,
                }
            }
        )
        
        # Store in history
        self._history.append((scores, result))
        
        return result
    
    def _determine_anomaly_type(
        self,
        scores: List[AnomalyScore],
        device_score: float,
        flow_score: float,
    ) -> AnomalyType:
        """Determine the primary anomaly type.
        
        Args:
            scores: Component anomaly scores
            device_score: Combined device anomaly score
            flow_score: Combined flow anomaly score
            
        Returns:
            Primary anomaly type
        """
        if not scores:
            return AnomalyType.DEVICE_ANOMALY  # Default
        
        # Find the highest scoring component
        max_score = max(scores, key=lambda s: s.score * s.confidence)
        
        # If both are high, it's a network anomaly
        if device_score > 0.7 and flow_score > 0.7:
            return AnomalyType.NETWORK_ANOMALY
        else:
            return max_score.anomaly_type
    
    def optimize_threshold(self, historical_data: List[Tuple[List[AnomalyScore], bool]]) -> float:
        """Optimize threshold using cost function.
        
        Cost function:
        J(\tau) = C_FN * P_FN(\tau) + C_FP * P_FP(\tau)
        
        Args:
            historical_data: List of (scores, ground_truth) pairs
            
        Returns:
            Optimized threshold
        """
        if not historical_data:
            return self.anomaly_threshold
        
        # Generate predictions for different thresholds
        thresholds = np.linspace(0.1, 0.9, 81)  # 0.1 to 0.9 with step 0.01
        costs = []
        
        for tau in thresholds:
            false_negatives = 0
            false_positives = 0
            
            for scores, ground_truth in historical_data:
                # Get fusion result for this threshold
                self.anomaly_threshold = tau
                result = self.fuse(scores)
                
                # Count errors
                if ground_truth and not result.is_anomaly:
                    false_negatives += 1
                elif not ground_truth and result.is_anomaly:
                    false_positives += 1
            
            # Compute probabilities
            total = len(historical_data)
            p_fn = false_negatives / total if total > 0 else 0.0
            p_fp = false_positives / total if total > 0 else 0.0
            
            # Compute cost
            cost = self.costs.cost_false_negative * p_fn + self.costs.cost_false_positive * p_fp
            costs.append((tau, cost))
        
        # Find threshold with minimum cost
        best_threshold, min_cost = min(costs, key=lambda x: x[1])
        
        # Update statistics
        self._update_statistics(historical_data, best_threshold)
        
        # Update threshold
        self.anomaly_threshold = best_threshold
        
        return best_threshold
    
    def _update_statistics(
        self,
        historical_data: List[Tuple[List[AnomalyScore], bool]],
        threshold: float,
    ):
        """Update performance statistics.
        
        Args:
            historical_data: Historical data
            threshold: Threshold to use
        """
        self._total_samples += len(historical_data)
        
        for scores, ground_truth in historical_data:
            self.anomaly_threshold = threshold
            result = self.fuse(scores)
            
            if ground_truth and result.is_anomaly:
                self._true_positives += 1
            elif ground_truth and not result.is_anomaly:
                self._false_negatives += 1
            elif not ground_truth and result.is_anomaly:
                self._false_positives += 1
            elif not ground_truth and not result.is_anomaly:
                self._true_negatives += 1
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        total_positive = self._true_positives + self._false_negatives
        total_negative = self._true_negatives + self._false_positives
        total_samples = self._total_samples
        
        # Compute metrics
        metrics = {
            "true_positives": self._true_positives,
            "false_positives": self._false_positives,
            "true_negatives": self._true_negatives,
            "false_negatives": self._false_negatives,
            "total_samples": total_samples,
        }
        
        if total_samples > 0:
            metrics.update({
                "accuracy": (self._true_positives + self._true_negatives) / total_samples,
                "precision": self._true_positives / (self._true_positives + self._false_positives)
                           if (self._true_positives + self._false_positives) > 0 else 0.0,
                "recall": self._true_positives / total_positive if total_positive > 0 else 0.0,
                "f1_score": 2 * metrics["precision"] * metrics["recall"] / (metrics["precision"] + metrics["recall"])
                           if (metrics["precision"] + metrics["recall"]) > 0 else 0.0,
                "false_positive_rate": self._false_positives / total_negative if total_negative > 0 else 0.0,
                "false_negative_rate": self._false_negatives / total_positive if total_positive > 0 else 0.0,
            })
        
        # Compute cost
        p_fn = metrics.get("false_negative_rate", 0.0)
        p_fp = metrics.get("false_positive_rate", 0.0)
        metrics["total_cost"] = self.costs.cost_false_negative * p_fn + self.costs.cost_false_positive * p_fp
        
        return metrics
    
    def reset_statistics(self):
        """Reset performance statistics."""
        self._false_positives = 0
        self._false_negatives = 0
        self._true_positives = 0
        self._true_negatives = 0
        self._total_samples = 0


class WeightedFusionEngine(LinearFusionEngine):
    """Weighted fusion engine with adaptive weights."""
    
    def __init__(
        self,
        initial_weights: Optional[FusionWeights] = None,
        costs: Optional[CostParameters] = None,
        anomaly_threshold: float = 0.7,
        learning_rate: float = 0.01,
    ):
        """Initialize weighted fusion engine.
        
        Args:
            initial_weights: Initial fusion weights
            costs: Cost parameters
            anomaly_threshold: Anomaly threshold
            learning_rate: Learning rate for weight adaptation
        """
        super().__init__(initial_weights, costs, anomaly_threshold)
        self.learning_rate = learning_rate
        self.adaptation_enabled = True
    
    def adapt_weights(self, feedback_data: List[Tuple[List[AnomalyScore], bool]]):
        """Adapt weights based on feedback.
        
        Args:
            feedback_data: List of (scores, correct_classification) pairs
        """
        if not self.adaptation_enabled or not feedback_data:
            return
        
        # Simple gradient descent adaptation
        total_error = 0.0
        
        for scores, correct_classification in feedback_data:
            # Get current prediction
            result = self.fuse(scores)
            current_prediction = result.is_anomaly
            
            # Compute error
            error = 1.0 if correct_classification != current_prediction else 0.0
            total_error += error
            
            # Extract scores
            device_score, flow_score = self._extract_scores(scores)
            
            # Update weights (simplified gradient)
            if error > 0:
                # Adjust weights based on which component was wrong
                if current_prediction and not correct_classification:
                    # False positive: reduce weights
                    self.weights.beta_1 -= self.learning_rate * device_score
                    self.weights.beta_2 -= self.learning_rate * flow_score
                elif not current_prediction and correct_classification:
                    # False negative: increase weights
                    self.weights.beta_1 += self.learning_rate * device_score
                    self.weights.beta_2 += self.learning_rate * flow_score
        
        # Normalize weights
        self._normalize_weights()
        
        return total_error / len(feedback_data) if feedback_data else 0.0
    
    def _normalize_weights(self):
        """Normalize weights to reasonable ranges."""
        # Keep weights positive
        self.weights.beta_1 = max(0.0, self.weights.beta_1)
        self.weights.beta_2 = max(0.0, self.weights.beta_2)
        
        # Cap weights to prevent explosion
        max_weight = 10.0
        self.weights.beta_1 = min(max_weight, self.weights.beta_1)
        self.weights.beta_2 = min(max_weight, self.weights.beta_2)
        self.weights.beta_3 = min(max_weight, self.weights.beta_3)


def create_fusion_engine(
    engine_type: str = "linear",
    weights: Optional[FusionWeights] = None,
    costs: Optional[CostParameters] = None,
    **kwargs,
) -> BaseFusionEngine:
    """Factory function to create fusion engine.
    
    Args:
        engine_type: Type of fusion engine ("linear" or "weighted")
        weights: Fusion weights
        costs: Cost parameters
        **kwargs: Additional arguments for specific engines
        
    Returns:
        Fusion engine instance
    """
    if engine_type == "linear":
        return LinearFusionEngine(weights, costs, **kwargs)
    elif engine_type == "weighted":
        return WeightedFusionEngine(weights, costs, **kwargs)
    else:
        raise ValueError(f"Unknown fusion engine type: {engine_type}")