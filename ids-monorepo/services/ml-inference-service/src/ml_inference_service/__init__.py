"""ML Inference Service for Smart Home IDS.

This service provides real-time ML inference for anomaly detection
using multiple backends (ONNX, scikit-learn) with plugin architecture.
"""

__version__ = "0.1.0"

from ml_inference_service.inference_engine import InferenceEngine
from ml_inference_service.api_server import APIServer
from ml_inference_service.mqtt_client import MQTTClient
from ml_inference_service.config import Config

__all__ = ["InferenceEngine", "APIServer", "MQTTClient", "Config"]