"""FastAPI server for ML Inference Service."""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, Field

from ids_core.api_client import APIClient
from ids_core.logger_enhanced import get_enhanced_logger, PerformanceTimer

from .config import Config
from .inference_engine import InferenceEngine, InferenceResponse
from .utils import validate_features, calculate_feature_hash


class InferenceRequest(BaseModel):
    """Request model for inference."""
    
    features: List[float] = Field(..., description="Feature vector")
    request_id: Optional[str] = Field(None, description="Optional request ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class BatchInferenceRequest(BaseModel):
    """Request model for batch inference."""
    
    batch: List[InferenceRequest] = Field(..., description="Batch of inference requests")
    batch_id: Optional[str] = Field(None, description="Optional batch ID")


class InferenceResponseModel(BaseModel):
    """Response model for inference."""
    
    request_id: str = Field(..., description="Request ID")
    is_anomaly: bool = Field(..., description="Is anomaly")
    anomaly_score: float = Field(..., description="Anomaly score")
    confidence: float = Field(..., description="Confidence score")
    inference_time_ms: float = Field(..., description="Inference time in ms")
    model_id: str = Field(..., description="Model ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="Timestamp")
    checks: Dict[str, Any] = Field(..., description="Health checks")


class StatsResponse(BaseModel):
    """Statistics response."""
    
    engine: Dict[str, Any] = Field(..., description="Engine statistics")
    performance: Dict[str, Any] = Field(..., description="Performance metrics")
    model: Dict[str, Any] = Field(..., description="Model statistics")
    timestamp: str = Field(..., description="Timestamp")


class ModelInfoResponse(BaseModel):
    """Model information response."""
    
    model_id: str = Field(..., description="Model ID")
    model_type: str = Field(..., description="Model type")
    backend: str = Field(..., description="Inference backend")
    version: str = Field(..., description="Model version")
    feature_count: int = Field(..., description="Number of features")
    loaded: bool = Field(..., description="Is model loaded")
    metadata: Dict[str, Any] = Field(..., description="Model metadata")


class APIServer:
    """FastAPI server for ML inference."""
    
    def __init__(self, config: Config, inference_engine: InferenceEngine):
        """Initialize API server.
        
        Args:
            config: Service configuration
            inference_engine: Inference engine instance
        """
        self.config = config
        self.engine = inference_engine
        
        # Setup logger
        self.logger = get_enhanced_logger(
            name="api",
            service_name=config.service_name,
            node_id=config.node_id,
        )
        
        # Create FastAPI app
        self.app = self._create_app()
        self._setup_routes()
        
        # Performance tracking
        self.request_counts = {
            "total": 0,
            "success": 0,
            "error": 0,
        }
        
        self.logger.info(
            "API server initialized",
            host=config.api_host,
            port=config.api_port,
        )
    
    def _create_app(self) -> FastAPI:
        """Create FastAPI application.
        
        Returns:
            FastAPI application
        """
        # CORS middleware
        middleware = [
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            ),
        ]
        
        # Create app
        app = FastAPI(
            title="ML Inference Service API",
            description="Real-time ML inference for anomaly detection",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
            middleware=middleware,
        )
        
        # Add exception handler
        @app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            self.logger.error(
                "Unhandled exception",
                error=str(exc),
                path=request.url.path,
                method=request.method,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "error": str(exc),
                },
            )
        
        # Add request logging middleware
        @app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = asyncio.get_event_loop().time()
            
            # Log request
            self.logger.info(
                "Request started",
                method=request.method,
                path=request.url.path,
                client_ip=request.client.host if request.client else None,
            )
            
            try:
                response = await call_next(request)
                
                # Calculate duration
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                
                # Log response
                self.logger.info(
                    "Request completed",
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )
                
                # Add performance header
                response.headers["X-Processing-Time"] = f"{duration_ms:.2f}ms"
                
                return response
                
            except Exception as e:
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                self.logger.error(
                    "Request failed",
                    method=request.method,
                    path=request.url.path,
                    error=str(e),
                    duration_ms=duration_ms,
                )
                raise
        
        return app
    
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint."""
            with PerformanceTimer("health_check", self.logger):
                health = await self.engine.health_check()
                return health
        
        @self.app.get("/stats", response_model=StatsResponse)
        async def get_stats():
            """Get engine statistics."""
            with PerformanceTimer("get_stats", self.logger):
                stats = self.engine.get_stats()
                return stats
        
        @self.app.get("/model/info", response_model=ModelInfoResponse)
        async def get_model_info():
            """Get model information."""
            with PerformanceTimer("get_model_info", self.logger):
                if not self.engine.model_loaded:
                    raise HTTPException(
                        status_code=404,
                        detail="No model loaded",
                    )
                
                model_info = self.engine.active_detector.get_model_info()
                return ModelInfoResponse(**model_info)
        
        @self.app.post("/predict", response_model=InferenceResponseModel)
        async def predict(request: InferenceRequest):
            """Single prediction endpoint."""
            self.request_counts["total"] += 1
            
            with self.logger.time_operation("predict_single"):
                # Extract features
                features = request.features
                request_id = request.request_id or f"req_{datetime.utcnow().timestamp()}"
                
                # Convert to numpy array
                features_array = np.array(features, dtype=np.float32)
                
                # Validate
                if not self.engine.model_loaded:
                    raise HTTPException(
                        status_code=503,
                        detail="Model not loaded",
                    )
                
                # Check feature count
                expected_features = self.engine.active_detector.metadata.feature_count
                if len(features_array) != expected_features:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Expected {expected_features} features, got {len(features_array)}",
                    )
                
                # Make prediction
                try:
                    response = await self.engine.predict(
                        features_array,
                        metadata={
                            "request_id": request_id,
                            "feature_hash": calculate_feature_hash(features_array),
                        }
                    )
                    
                    # Convert to response model
                    result = response.result
                    
                    inference_response = InferenceResponseModel(
                        request_id=request_id,
                        is_anomaly=result.is_anomaly,
                        anomaly_score=result.anomaly_score,
                        confidence=result.confidence,
                        inference_time_ms=result.inference_time_ms,
                        model_id=result.model_id,
                        metadata={
                            "processing_time_ms": response.processing_time_ms,
                            **result.metadata,
                        } if result.metadata else None,
                    )
                    
                    self.request_counts["success"] += 1
                    return inference_response
                    
                except Exception as e:
                    self.request_counts["error"] += 1
                    self.logger.error(
                        "Prediction failed",
                        error=str(e),
                        request_id=request_id,
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"Inference failed: {str(e)}",
                    )
        
        @self.app.post("/predict/batch")
        async def predict_batch(request: BatchInferenceRequest):
            """Batch prediction endpoint."""
            self.request_counts["total"] += len(request.batch)
            
            with self.logger.time_operation("predict_batch"):
                # Extract batch data
                batch_requests = []
                batch_metadata = []
                
                for i, req in enumerate(request.batch):
                    features_array = np.array(req.features, dtype=np.float32)
                    batch_requests.append(features_array)
                    
                    batch_metadata.append({
                        "request_id": req.request_id or f"batch_{i}",
                        "feature_hash": calculate_feature_hash(features_array),
                        "batch_index": i,
                        "batch_id": request.batch_id,
                    })
                
                # Validate
                if not self.engine.model_loaded:
                    raise HTTPException(
                        status_code=503,
                        detail="Model not loaded",
                    )
                
                # Check feature counts
                expected_features = self.engine.active_detector.metadata.feature_count
                invalid_indices = []
                
                for i, features in enumerate(batch_requests):
                    if len(features) != expected_features:
                        invalid_indices.append(i)
                
                if invalid_indices:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Invalid feature counts at indices {invalid_indices}. "
                            f"Expected {expected_features} features."
                        ),
                    )
                
                # Make batch prediction
                try:
                    responses = await self.engine.predict_batch(
                        batch_requests,
                        metadata=batch_metadata,
                    )
                    
                    # Convert to response models
                    inference_responses = []
                    
                    for i, response in enumerate(responses):
                        result = response.result
                        
                        inference_response = InferenceResponseModel(
                            request_id=(
                                request.batch[i].request_id or 
                                f"batch_{i}_{datetime.utcnow().timestamp()}"
                            ),
                            is_anomaly=result.is_anomaly,
                            anomaly_score=result.anomaly_score,
                            confidence=result.confidence,
                            inference_time_ms=result.inference_time_ms,
                            model_id=result.model_id,
                            metadata={
                                "processing_time_ms": response.processing_time_ms,
                                "batch_index": i,
                                "batch_id": request.batch_id,
                                **result.metadata,
                            } if result.metadata else None,
                        )
                        
                        inference_responses.append(inference_response)
                    
                    self.request_counts["success"] += len(inference_responses)
                    return {
                        "batch_id": request.batch_id,
                        "count": len(inference_responses),
                        "results": inference_responses,
                    }
                    
                except Exception as e:
                    self.request_counts["error"] += len(request.batch)
                    self.logger.error(
                        "Batch prediction failed",
                        error=str(e),
                        batch_id=request.batch_id,
                        batch_size=len(request.batch),
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"Batch inference failed: {str(e)}",
                    )
        
        @self.app.post("/model/load")
        async def load_model(model_path: str, model_id: Optional[str] = None):
            """Load model endpoint."""
            with PerformanceTimer("load_model", self.logger):
                success = await self.engine.load_model(model_path, model_id)
                
                if success:
                    return {
                        "status": "success",
                        "message": f"Model loaded: {model_path}",
                        "model_id": self.engine.active_detector.metadata.model_id,
                    }
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to load model: {model_path}",
                    )
        
        @self.app.get("/metrics")
        async def get_metrics():
            """Prometheus metrics endpoint (in development)."""
            # Simple metrics for now
            metrics = {
                "inference_engine": {
                    "requests_total": self.request_counts["total"],
                    "requests_success": self.request_counts["success"],
                    "requests_error": self.request_counts["error"],
                    "success_rate": (
                        self.request_counts["success"] / self.request_counts["total"]
                        if self.request_counts["total"] > 0 else 0.0
                    ),
                },
                "engine_stats": self.engine.get_stats(),
            }
            
            # Format for Prometheus (simplified)
            prometheus_lines = []
            
            # Request metrics
            prometheus_lines.append(
                f'inference_requests_total {self.request_counts["total"]}'
            )
            prometheus_lines.append(
                f'inference_requests_success {self.request_counts["success"]}'
            )
            prometheus_lines.append(
                f'inference_requests_error {self.request_counts["error"]}'
            )
            
            # Engine metrics from stats
            stats = self.engine.get_stats()
            engine_stats = stats.get("engine", {})
            
            prometheus_lines.append(
                f'inference_engine_avg_time_ms {engine_stats.get("avg_inference_time_ms", 0.0)}'
            )
            prometheus_lines.append(
                f'inference_engine_queue_size {engine_stats.get("queue_size", 0)}'
            )
            
            return Response(
                content="\n".join(prometheus_lines),
                media_type="text/plain",
            )
    
    async def start(self):
        """Start the API server."""
        self.logger.info(
            "Starting API server",
            host=self.config.api_host,
            port=self.config.api_port,
            workers=self.config.api_workers,
        )
        
        # Start server
        config = uvicorn.Config(
            self.app,
            host=self.config.api_host,
            port=self.config.api_port,
            log_level="info" if self.config.debug else "warning",
            access_log=False,  # We handle logging ourselves
            workers=self.config.api_workers,
        )
        
        server = uvicorn.Server(config)
        await server.serve()
    
    async def stop(self):
        """Stop the API server."""
        self.logger.info("Stopping API server")
        # Uvicorn server will be stopped by the main process


import numpy as np  # Import numpy
from fastapi import Response  # Import Response