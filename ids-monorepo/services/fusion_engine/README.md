# Fusion Engine

The Fusion Engine is a core component of the Smart Home IDS. It is responsible for combining anomaly scores from different analytical models (e.g., device behavior and network flow) to produce a unified risk score. This combined score helps in making more accurate decisions about potential intrusions while minimizing false positives.

## Core Logic

The engine uses a logistic regression-style equation to fuse the scores:

$$ \hat{p}_t = \sigma(\beta_0 + \beta_1 s_t^{dev} + \beta_2 s_t^{flow} + \beta_3 s_t^{dev}s_t^{flow}) $$

Where:
- $\hat{p}_t$ is the final fused risk probability.
- $\sigma(x)$ is the sigmoid function: $1 / (1 + e^{-x})$.
- $s_t^{dev}$ is the anomaly score from device behavior analysis.
- $s_t^{flow}$ is the anomaly score from network flow analysis.
- $\beta_0, \beta_1, \beta_2, \beta_3$ are configurable weights.

## Features

- **Sigmoid Probability Scoring:** Outputs a normalized risk score between 0.0 and 1.0.
- **Configurable Beta Weights:** Allows tuning of the model's sensitivity to different anomaly sources and their interactions.
- **Threshold Evaluation:** Evaluates the final score against a configurable threshold to determine if an alert should be triggered.
- **Confidence Scoring:** Calculates a confidence score indicating the certainty of the decision.
- **Edge Optimization:** Rounds calculations to a specified precision to optimize performance on edge devices like Raspberry Pi.

## Installation

```bash
cd services/fusion_engine
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Testing

```bash
cd services/fusion_engine
PYTHONPATH=src pytest tests/
```
