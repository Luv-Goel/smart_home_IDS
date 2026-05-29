"""Main entry point for ML Inference Service."""

import asyncio
import signal
import sys
from typing import Optional

from ids_core.logger_enhanced import get_enhanced_logger
from ids_core.config import get_settings

from .config import Config
from .inference_engine import InferenceEngine
from .api_server import APIServer
from .mqtt_client import MQTTClient


class MLInferenceService:
    """Main ML Inference Service class."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the service.
        
        Args:
            config: Optional configuration (uses default if None)
        """
        self.config = config or Config()
        self.settings = get_settings()
        
        # Setup logger
        self.logger = get_enhanced_logger(
            name="ml-inference-service",
            service_name=self.config.service_name,
            node_id=self.config.node_id,
        )
        
        # Core components
        self.engine: Optional[InferenceEngine] = None
        self.api_server: Optional[APIServer] = None
        self.mqtt_client: Optional[MQTTClient] = None
        
        # Signal handling
        self.shutdown_event = asyncio.Event()
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info(
            "ML Inference Service initialized",
            node_id=self.config.node_id,
            backend=self.config.inference_backend.value,
            model_path=self.config.model_path,
        )
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.warning(
            "Received shutdown signal",
            signal=signal.Signals(signum).name,
        )
        self.shutdown_event.set()
    
    async def startup(self):
        """Start up all service components."""
        self.logger.info("Starting ML Inference Service")
        
        try:
            # Create inference engine
            self.logger.info("Creating inference engine")
            self.engine = InferenceEngine(self.config)
            await self.engine.startup()
            
            # Create MQTT client
            self.logger.info("Creating MQTT client")
            self.mqtt_client = MQTTClient(self.config, self.engine)
            
            # Connect to MQTT broker
            connected = await self.mqtt_client.connect()
            if not connected:
                self.logger.error("Failed to connect to MQTT broker")
                # Continue without MQTT for now
            
            # Start MQTT message processor
            mqtt_task = asyncio.create_task(
                self.mqtt_client.process_incoming_messages()
            )
            
            # Create API server
            self.logger.info("Creating API server")
            self.api_server = APIServer(self.config, self.engine)
            
            # Start API server in background
            api_task = asyncio.create_task(self.api_server.start())
            
            # Log startup complete
            self.logger.info(
                "ML Inference Service started successfully",
                api_host=self.config.api_host,
                api_port=self.config.api_port,
                mqtt_connected=self.mqtt_client.connected,
                model_loaded=self.engine.model_loaded,
            )
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            # Cancel tasks
            mqtt_task.cancel()
            api_task.cancel()
            
            try:
                await mqtt_task
                await api_task
            except asyncio.CancelledError:
                pass
            
            self.logger.info("Shutdown signal received, shutting down")
            
        except Exception as e:
            self.logger.critical(
                "Service startup failed",
                error=str(e),
                exc_info=True,
            )
            raise
    
    async def shutdown(self):
        """Shut down all service components."""
        self.logger.info("Shutting down ML Inference Service")
        
        shutdown_tasks = []
        
        # Disconnect MQTT client
        if self.mqtt_client:
            self.logger.info("Disconnecting MQTT client")
            shutdown_tasks.append(self.mqtt_client.disconnect())
        
        # Shutdown inference engine
        if self.engine:
            self.logger.info("Shutting down inference engine")
            shutdown_tasks.append(self.engine.shutdown())
        
        # Wait for all shutdown tasks
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        self.logger.info("ML Inference Service shutdown complete")
    
    async def run(self):
        """Run the service."""
        try:
            await self.startup()
        finally:
            await self.shutdown()


async def main():
    """Main entry point."""
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="ML Inference Service")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default=None,
        help="Model directory path",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    
    args = parser.parse_args()
    
    # Create config with overrides
    config_kwargs = {}
    
    if args.config:
        # Load config from file
        import yaml
        try:
            with open(args.config, 'r') as f:
                file_config = yaml.safe_load(f)
            config_kwargs.update(file_config)
        except Exception as e:
            print(f"Failed to load config file: {e}")
            sys.exit(1)
    
    if args.model_dir:
        config_kwargs["model_dir"] = args.model_dir
    
    if args.debug:
        config_kwargs["debug"] = True
        config_kwargs["log_level"] = "DEBUG"
    
    # Create and run service
    config = Config(**config_kwargs)
    service = MLInferenceService(config)
    
    try:
        await service.run()
    except KeyboardInterrupt:
        service.logger.info("Service stopped by user")
    except Exception as e:
        service.logger.critical(
            "Service crashed",
            error=str(e),
            exc_info=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())