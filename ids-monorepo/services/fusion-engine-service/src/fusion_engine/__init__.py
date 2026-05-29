"""Fusion Engine for Smart Home IDS.

This service implements cost-aware fusion of anomaly scores from
multiple sources with threshold optimization.
"""

__version__ = "0.1.0"

from fusion_engine.fusion_engine import FusionEngine
from fusion_engine.config import Config
from fusion_engine.api_server import APIServer

__all__ = ["FusionEngine", "Config", "APIServer"]