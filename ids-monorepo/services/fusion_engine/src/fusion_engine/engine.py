import math
from typing import Dict, Any, Tuple
from dataclasses import dataclass
from .config import FusionConfig

@dataclass
class FusionResult:
    """Result of a fusion scoring operation."""
    risk_score: float
    trigger_alert: bool
    confidence_score: float
    details: Dict[str, float]

class FusionEngine:
    """
    Fusion Engine for calculating combined risk scores from multiple anomaly sources.
    Uses the equation: \\hat{p}_t = \\sigma(\\beta_0 + \\beta_1 s_t^{dev} + \\beta_2 s_t^{flow} + \\beta_3 s_t^{dev}s_t^{flow})
    """

    def __init__(self, config: FusionConfig | None = None) -> None:
        self.config = config or FusionConfig()

    def _sigmoid(self, x: float) -> float:
        """
        Calculate the sigmoid function for a given input.
        \\sigma(x) = 1 / (1 + e^{-x})
        """
        try:
            # Prevent overflow for very large negative numbers
            if x < -700:
                return 0.0
            return 1.0 / (1.0 + math.exp(-x))
        except OverflowError:
            return 1.0 if x > 0 else 0.0

    def calculate_score(self, device_score: float, flow_score: float) -> FusionResult:
        """
        Calculate the fusion score, evaluate thresholds, and determine alert status.

        Args:
            device_score (float): Anomaly score from device behavior analysis (0.0 to 1.0)
            flow_score (float): Anomaly score from network flow analysis (0.0 to 1.0)

        Returns:
            FusionResult: Object containing risk score, alert status, and calculation details
        """
        # Ensure inputs are within expected bounds
        s_dev = max(0.0, min(1.0, float(device_score)))
        s_flow = max(0.0, min(1.0, float(flow_score)))

        # Calculate interaction term
        interaction = s_dev * s_flow

        # Calculate logit (linear combination)
        logit = (
            self.config.beta_0
            + (self.config.beta_1 * s_dev)
            + (self.config.beta_2 * s_flow)
            + (self.config.beta_3 * interaction)
        )

        # Apply sigmoid to get probability/risk score
        raw_risk_score = self._sigmoid(logit)

        # Edge optimization: Round to specified precision
        risk_score = round(raw_risk_score, self.config.precision_decimals)

        # Evaluate threshold
        trigger_alert = risk_score >= self.config.alert_threshold

        # Calculate confidence score based on how far the score is from the threshold/uncertainty region
        # High confidence if score is very low (definitely benign) or very high (definitely malicious)
        # Lower confidence if score is near 0.5
        confidence = round(
            abs((raw_risk_score - 0.5) * 2.0), self.config.precision_decimals
        )

        return FusionResult(
            risk_score=risk_score,
            trigger_alert=trigger_alert,
            confidence_score=confidence,
            details={
                "device_score": s_dev,
                "flow_score": s_flow,
                "interaction_term": interaction,
                "logit": round(logit, self.config.precision_decimals)
            }
        )

    def update_config(self, **kwargs: Any) -> None:
        """Update fusion configuration parameters."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                raise ValueError(f"Invalid configuration parameter: {key}")
