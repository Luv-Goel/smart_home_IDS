from pydantic import BaseModel, Field, ConfigDict

class FusionConfig(BaseModel):
    """Configuration for the fusion engine."""

    # Beta weights for the fusion equation
    # \\hat{p}_t = \\sigma(\\beta_0 + \\beta_1 s_t^{dev} + \\beta_2 s_t^{flow} + \\beta_3 s_t^{dev}s_t^{flow})
    beta_0: float = Field(default=-2.0, description="Intercept/Bias term")
    beta_1: float = Field(default=1.5, description="Device anomaly score weight")
    beta_2: float = Field(default=1.5, description="Flow anomaly score weight")
    beta_3: float = Field(default=2.0, description="Interaction term weight")

    # Thresholds for triggering alerts
    alert_threshold: float = Field(
        default=0.75, description="Threshold above which an alert is triggered (0.0 to 1.0)"
    )

    # Edge optimization settings
    precision_decimals: int = Field(
        default=4, description="Number of decimal places to round results to for edge optimization"
    )

    model_config = ConfigDict(validate_assignment=True)
