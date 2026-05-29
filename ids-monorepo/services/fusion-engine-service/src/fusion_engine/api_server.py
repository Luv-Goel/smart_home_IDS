"""FastAPI server for Fusion Engine Service."""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, Field
import numpy as np

from ids_core.logger_enhanced import get_enhanced_logger, PerformanceTimer

from .config import Config
from .fusion_engine import FusionEngine, AnomalyScore, FusedResult


class FusionRequest(BaseModel):
    """Request model for fusion."""
    
    scores: Dict[str, Dict[str, float]] = Field(..., description="Anomaly scores by source")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class FusionResponse(BaseModel):
    """Response model for fusion."""
    
    fused_id: str = Field(..., description="Fusion request ID")
    timestamp: str = Field(..., description="ISO timestamp")
    fused_score: float = Field(..., description="Fused anomaly score")
    fused_confidence: float = Field(..., description="Fusion confidence")
    is_anomaly: bool = Field(..., description="Is anomaly")
    severity: str = Field(..., description="Severity level")
    threshold_used: float = Field(..., description="Threshold used")
    individual_scores: Dict[str, Dict[str, float]] = Field(..., description="Individual scores")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="Timestamp")
    checks: Dict[str, Any] = Field(..., description="Health checks")


class StatsResponse(BaseModel):
    """Statistics response."""
    
    engine: Dict[str, Any] = Field(..., description="Engine statistics")
    threshold_history: Dict[str, Any] = Field(..., description="Threshold statistics")
    timestamp: str = Field(..., description="Timestamp")


class ThresholdUpdateRequest(BaseModel):
    """Request to update threshold."""
    
    threshold: float = Field(..., ge=0.0, le=1.0, description="New threshold value")


class ThresholdResponse(BaseModel):
    """Threshold response."""
    
    old_threshold: float = Field(..., description="Old threshold")
    new_threshold: float = Field(..., description="New threshold")
    message: str = Field(..., description="Response message")


class APIServer:
    """FastAPI server for Fusion Engine."""
    
    def __init__(self, config: Config, fusion_engine: FusionEngine):
        """Initialize API server.
        
        Args:
            config: Service configuration
            fusion_engine: Fusion engine instance
        """
        self.config = config
        self.engine = fusion_engine
        
        # Setup logger
        self.logger = get_enhanced_logger(
            name="api",
            service_name=config.service_name,
            node_id=config.node_id,
        )
        
        # Create FastAPI app
        self.app = self._create_app()
        self._setup_routes()
        
        # Request tracking
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
        # Create app
        app = FastAPI(
            title="Fusion Engine Service API",
            description="Cost-aware fusion of anomaly scores with threshold optimization",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
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
        
        @self.app.post("/fuse", response_model=FusionResponse)
        async def fuse(request: FusionRequest):
            """Fuse anomaly scores."""
            self.request_counts["total"] += 1
            
            with self.logger.time_operation("fuse"):
                try:
                    # Convert scores to AnomalyScore objects
                    anomaly_scores = {}
                    
                    for source, score_data in request.scores.items():
                        score = score_data.get("score", 0.0)
                        confidence = score_data.get("confidence", 0.0)
                        
                        anomaly_scores[source] = AnomalyScore(
                            source_type=source,
                            score=score,
                            confidence=confidence,
                            metadata=score_data.get("metadata", {}),
                        )
                    
                    # Process fusion
                    result = await self.engine.process_scores(anomaly_scores)
                    
                    # Convert to response
                    response = FusionResponse(
                        fused_id=result.fused_id,
                        timestamp=datetime.fromtimestamp(result.timestamp).isoformat(),
                        fused_score=result.fused_score,
                        fused_confidence=result.fused_confidence,
                        is_anomaly=result.is_anomaly,
                        severity=result.severity,
                        threshold_used=result.threshold_used,
                        individual_scores={
                            source: {
                                "score": score.score,
                                "confidence": score.confidence,
                            }
                            for source, score in result.individual_scores.items()
                        },
                        metadata=result.metadata,
                    )
                    
                    self.request_counts["success"] += 1
                    return response
                    
                except Exception as e:
                    self.request_counts["error"] += 1
                    self.logger.error(
                        "Fusion failed",
                        error=str(e),
                        scores_count=len(request.scores),
                        exc_info=True,
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"Fusion failed: {str(e)}",
                    )
        
        @self.app.get("/threshold")
        async def get_threshold():
            """Get current fusion threshold."""
            with PerformanceTimer("get_threshold", self.logger):
                return {
                    "threshold": self.engine.current_threshold,
                    "method": self.config.threshold_optimization.value,
                    "cost_matrix": self.config.cost_matrix,
                    "coefficients": self.config.fusion_coefficients,
                }
        
        @self.app.post("/threshold", response_model=ThresholdResponse)
        async def update_threshold(request: ThresholdUpdateRequest):
            """Update fusion threshold (manual override)."""
            with PerformanceTimer("update_threshold", self.logger):
                old_threshold = self.engine.current_threshold
                new_threshold = request.threshold
                
                self.engine.current_threshold = new_threshold
                
                self.logger.info(
                    "Threshold updated",
                    old_threshold=old_threshold,
                    new_threshold=new_threshold,
                )
                
                return ThresholdResponse(
                    old_threshold=old_threshold,
                    new_threshold=new_threshold,
                    message="Threshold updated successfully",
                )
        
        @self.app.post("/threshold/optimize")
        async def optimize_threshold():
            """Trigger threshold optimization."""
            with PerformanceTimer("optimize_threshold", self.logger):
                self.engine._optimize_threshold()
                
                return {
                    "message": "Threshold optimization triggered",
                    "new_threshold": self.engine.current_threshold,
                    "buffer_size": len(self.engine.score_buffer),
                }
        
        @self.app.get("/config")
        async def get_config():
            """Get current configuration."""
            with PerformanceTimer("get_config", self.logger):
                return {
                    "fusion_method": self.config.fusion_method.value,
                    "threshold_optimization": self.config.threshold_optimization.value,
                    "confidence_method": self.config.confidence_method.value,
                    "fusion_coefficients": self.config.fusion_coefficients,
                    "cost_matrix": self.config.cost_matrix,
                    "severity_thresholds": self.config.severity_thresholds,
                    "edge_optimized": self.config.optimize_for_edge,
                }
        
        @self.app.post("/config/coefficients")
        async def update_coefficients(
            beta_0: Optional[float] = None,
            beta_1: Optional[float] = None,
            beta_2: Optional[float] = None,
            beta_3: Optional[float] = None,
        ):
            """Update linear fusion coefficients."""
            with PerformanceTimer("update_coefficients", self.logger):
                old_coefficients = self.config.fusion_coefficients.copy()
                
                if beta_0 is not None:
                    self.config.beta_0 = beta_0
                if beta_1 is not None:
                    self.config.beta_1 = beta_1
                if beta_2 is not None:
                    self.config.beta_2 = beta_2
                if beta_3 is not None:
                    self.config.beta_3 = beta_3
                
                self.logger.info(
                    "Coefficients updated",
                    old_coefficients=old_coefficients,
                    new_coefficients=self.config.fusion_coefficients,
                )
                
                return {
                    "message": "Coefficients updated",
                    "old_coefficients": old_coefficients,
                    "new_coefficients": self.config.fusion_coefficients,
                }
        
        @self.app.post("/config/costs")
        async def update_costs(
            cost_false_negative: Optional[float] = None,
            cost_false_positive: Optional[float] = None,
        ):
            """Update cost matrix."""
            with PerformanceTimer("update_costs", self.logger):
                old_costs = self.config.cost_matrix.copy()
                
                if cost_false_negative is not None:
                    self.config.cost_false_negative = cost_false_negative
                if cost_false_positive is not None:
                    self.config.cost_false_positive = cost_false_positive
                
                self.logger.info(
                    "Costs updated",
                    old_costs=old_costs,
                    new_costs=self.config.cost_matrix,
                )
                
                return {
                    "message": "Cost matrix updated",
                    "old_costs": old_costs,
                    "new_costs": self.config.cost_matrix,
                }
    
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