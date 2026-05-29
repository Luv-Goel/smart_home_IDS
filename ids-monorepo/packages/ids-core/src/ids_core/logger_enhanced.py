"""Enhanced structured logging for production IDS.

This module provides comprehensive structured logging with metrics,
performance tracing, and distributed tracing support.
"""

import logging
import sys
import json
import time
import uuid
from typing import Optional, Dict, Any, Callable, List
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

import structlog
from structlog.types import Processor, EventDict

# Log levels
class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


@dataclass
class LogContext:
    """Standard logging context for distributed tracing."""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_path: Optional[str] = None
    service_name: str = "unknown"
    node_id: str = "unknown"
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Performance metrics for timing operations."""
    operation: str
    duration_ms: float
    start_time: datetime
    end_time: datetime
    status: str = "success"
    error_message: Optional[str] = None
    additional_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        data = asdict(self)
        data["start_time"] = self.start_time.isoformat()
        data["end_time"] = self.end_time.isoformat()
        return data


class StructuredLogger:
    """Enhanced logger with context management and metrics."""
    
    def __init__(self, name: str, service_name: str, node_id: str):
        """Initialize enhanced logger.
        
        Args:
            name: Logger name
            service_name: Service name for context
            node_id: Node identifier
        """
        self.name = name
        self.service_name = service_name
        self.node_id = node_id
        self._logger = structlog.get_logger(name)
        self._context_stack: List[Dict[str, Any]] = []
        self._metrics: Dict[str, List[PerformanceMetrics]] = {}
    
    def _get_context(self) -> Dict[str, Any]:
        """Get current context dictionary."""
        context = {
            "service": self.service_name,
            "node_id": self.node_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Add nested contexts
        for ctx in self._context_stack:
            context.update(ctx)
        
        return context
    
    @contextmanager
    def log_context(self, **context_vars):
        """Context manager for adding context to logs.
        
        Args:
            **context_vars: Context variables to add
        """
        self._context_stack.append(context_vars)
        try:
            yield
        finally:
            self._context_stack.pop()
    
    def info(self, event: str, **kwargs):
        """Log info message."""
        self._logger.info(event, **self._get_context(), **kwargs)
    
    def error(self, event: str, **kwargs):
        """Log error message."""
        self._logger.error(event, **self._get_context(), **kwargs)
    
    def warning(self, event: str, **kwargs):
        """Log warning message."""
        self._logger.warning(event, **self._get_context(), **kwargs)
    
    def debug(self, event: str, **kwargs):
        """Log debug message."""
        self._logger.debug(event, **self._get_context(), **kwargs)
    
    def critical(self, event: str, **kwargs):
        """Log critical message."""
        self._logger.critical(event, **self._get_context(), **kwargs)
    
    @contextmanager
    def time_operation(self, operation_name: str, **context_vars):
        """Time an operation and log performance metrics.
        
        Args:
            operation_name: Name of the operation
            **context_vars: Additional context variables
        """
        start_time = datetime.utcnow()
        start_perf = time.perf_counter()
        
        try:
            with self.log_context(operation=operation_name, **context_vars):
                yield
                
            end_perf = time.perf_counter()
            duration_ms = (end_perf - start_perf) * 1000
            
            # Record metrics
            metric = PerformanceMetrics(
                operation=operation_name,
                duration_ms=duration_ms,
                start_time=start_time,
                end_time=datetime.utcnow(),
                status="success",
            )
            
            if operation_name not in self._metrics:
                self._metrics[operation_name] = []
            self._metrics[operation_name].append(metric)
            
            # Log performance
            self.info(
                "operation_completed",
                operation=operation_name,
                duration_ms=duration_ms,
                status="success",
            )
            
        except Exception as e:
            end_perf = time.perf_counter()
            duration_ms = (end_perf - start_perf) * 1000
            
            # Record error metric
            metric = PerformanceMetrics(
                operation=operation_name,
                duration_ms=duration_ms,
                start_time=start_time,
                end_time=datetime.utcnow(),
                status="error",
                error_message=str(e),
            )
            
            if operation_name not in self._metrics:
                self._metrics[operation_name] = []
            self._metrics[operation_name].append(metric)
            
            # Log error
            self.error(
                "operation_failed",
                operation=operation_name,
                duration_ms=duration_ms,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    def get_operation_metrics(self, operation_name: str) -> List[Dict[str, Any]]:
        """Get metrics for a specific operation.
        
        Args:
            operation_name: Name of the operation
            
        Returns:
            List of operation metrics dictionaries
        """
        if operation_name not in self._metrics:
            return []
        
        return [metric.to_dict() for metric in self._metrics[operation_name]]
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics.
        
        Returns:
            Dictionary with aggregated metrics
        """
        result = {
            "service": self.service_name,
            "node_id": self.node_id,
            "timestamp": datetime.utcnow().isoformat(),
            "operations": {},
        }
        
        for op_name, metrics in self._metrics.items():
            if not metrics:
                continue
                
            durations = [m.duration_ms for m in metrics]
            success_count = sum(1 for m in metrics if m.status == "success")
            error_count = sum(1 for m in metrics if m.status == "error")
            
            result["operations"][op_name] = {
                "total_count": len(metrics),
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": success_count / len(metrics) if metrics else 0,
                "avg_duration_ms": sum(durations) / len(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "p95_duration_ms": sorted(durations)[int(len(durations) * 0.95)]
                if len(durations) > 1 else durations[0],
                "last_10_metrics": [m.to_dict() for m in metrics[-10:]],
            }
        
        return result


def setup_enhanced_logging(
    service_name: str,
    node_id: str,
    log_level: str = "INFO",
    log_format: str = "json",
    enable_console: bool = True,
    enable_file: bool = False,
    log_file_path: str = "/var/log/ids.log",
    enable_metrics_collection: bool = True,
):
    """Setup enhanced logging system.
    
    Args:
        service_name: Name of the service
        node_id: Node identifier
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format (json, pretty, console)
        enable_console: Enable console logging
        enable_file: Enable file logging
        log_file_path: Path to log file
        enable_metrics_collection: Enable metrics collection
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    handlers = []
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        
        if log_format == "json":
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"service": "%(name)s", "message": "%(message)s"}'
            )
        elif log_format == "pretty":
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        else:  # console
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
            )
        
        console_handler.setFormatter(formatter)
        handlers.append(console_handler)
    
    # File handler
    if enable_file:
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.DEBUG)  # File gets everything
        
        # Always JSON for file
        json_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"service": "%(name)s", "node": "%(node_id)s", "message": "%(message)s"}'
        )
        file_handler.setFormatter(json_formatter)
        handlers.append(file_handler)
    
    # Add all handlers
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Configure structlog
    processors: List[Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    elif log_format == "pretty":
        processors.append(structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.rich_traceback,
        ))
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=False))
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.AsyncBoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Log startup message
    logger = structlog.get_logger(service_name)
    logger.info(
        "Logging system initialized",
        service_name=service_name,
        node_id=node_id,
        log_level=log_level,
        log_format=log_format,
        console_enabled=enable_console,
        file_enabled=enable_file,
        metrics_enabled=enable_metrics_collection,
    )


def get_enhanced_logger(name: str, service_name: str, node_id: str) -> StructuredLogger:
    """Get enhanced logger instance.
    
    Args:
        name: Logger name
        service_name: Service name
        node_id: Node identifier
        
    Returns:
        Enhanced StructuredLogger instance
    """
    return StructuredLogger(name, service_name, node_id)