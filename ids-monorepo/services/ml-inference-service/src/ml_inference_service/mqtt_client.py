"""MQTT client for ML Inference Service."""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

import paho.mqtt.client as mqtt
from structlog import get_logger

from ids_core.logger_enhanced import get_enhanced_logger, PerformanceTimer
from ids_schemas import InferenceEvent, DeviceEvent

from .config import Config
from .inference_engine import InferenceEngine


@dataclass
class MQTTMessage:
    """MQTT message wrapper."""
    
    topic: str
    payload: bytes
    qos: int = 0
    retain: bool = False
    timestamp: float = field(default_factory=time.time)
    
    @property
    def payload_str(self) -> str:
        """Get payload as string."""
        return self.payload.decode('utf-8')
    
    @property
    def payload_json(self) -> Dict[str, Any]:
        """Get payload as JSON."""
        return json.loads(self.payload_str)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "topic": self.topic,
            "payload": self.payload_json,
            "qos": self.qos,
            "retain": self.retain,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
        }


class MQTTClient:
    """Async MQTT client for ML inference service."""
    
    def __init__(
        self,
        config: Config,
        inference_engine: InferenceEngine,
    ):
        """Initialize MQTT client.
        
        Args:
            config: Service configuration
            inference_engine: Inference engine instance
        """
        self.config = config
        self.engine = inference_engine
        
        # Setup logger
        self.logger = get_enhanced_logger(
            name="mqtt",
            service_name=config.service_name, 
            node_id=config.node_id,
        )
        
        # MQTT client
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        
        # Message queues
        self.incoming_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.outgoing_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        
        # Topics
        self.input_topic = config.mqtt_input_topic
        self.output_topic = config.mqtt_output_topic
        self.status_topic = config.mqtt_status_topic
        self.command_topic = config.mqtt_command_topic
        
        # Callbacks
        self.on_connect_callbacks: List[Callable] = []
        self.on_message_callbacks: List[Callable] = []
        
        # Statistics
        self.messages_received = 0
        self.messages_sent = 0
        self.connection_errors = 0
        
        self.logger.info(
            "MQTT client initialized",
            broker_url=config.mqtt_broker_url,
            client_id=config.mqtt_client_id,
            input_topic=self.input_topic,
            output_topic=self.output_topic,
        )
    
    def _setup_client(self):
        """Setup MQTT client configuration."""
        # Create client
        self.client = mqtt.Client(
            client_id=self.config.mqtt_client_id,
            clean_session=self.config.mqtt_clean_session,
        )
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
        self.client.on_subscribe = self._on_subscribe
        self.client.on_log = self._on_log
        
        # Set authentication if provided
        if self.config.mqtt_username and self.config.mqtt_password:
            self.client.username_pw_set(
                self.config.mqtt_username,
                self.config.mqtt_password,
            )
        
        # Set last will and testament
        will_message = json.dumps({
            "node_id": self.config.node_id,
            "service": self.config.service_name,
            "status": "offline",
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        self.client.will_set(
            self.status_topic,
            will_message,
            qos=1,
            retain=True,
        )
    
    def _on_connect(self, client, userdata, flags, rc):
        """Handle connection callback."""
        self.connected = rc == 0
        
        if self.connected:
            self.reconnect_attempts = 0
            
            self.logger.info(
                "Connected to MQTT broker",
                broker_url=self.config.mqtt_broker_url,
                return_code=rc,
                flags=flags,
            )
            
            # Subscribe to topics
            self._subscribe_topics()
            
            # Publish connected status
            self._publish_status("connected")
            
            # Call connect callbacks
            for callback in self.on_connect_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(
                        "Connect callback failed",
                        error=str(e),
                        callback=str(callback),
                    )
            
        else:
            self.logger.error(
                "Failed to connect to MQTT broker",
                return_code=rc,
                error_message=mqtt.error_string(rc),
            )
            
            # Schedule reconnection
            self._schedule_reconnect()
    
    def _on_disconnect(self, client, userdata, rc):
        """Handle disconnection callback."""
        self.connected = False
        
        self.logger.warning(
            "Disconnected from MQTT broker",
            return_code=rc,
            error_message=mqtt.error_string(rc) if rc != 0 else "Normal disconnect",
        )
        
        # Schedule reconnection if unexpected disconnect
        if rc != 0:
            self._schedule_reconnect()
    
    def _on_message(self, client, userdata, message):
        """Handle incoming message callback."""
        self.messages_received += 1
        
        # Create message wrapper
        mqtt_message = MQTTMessage(
            topic=message.topic,
            payload=message.payload,
            qos=message.qos,
            retain=message.retain,
        )
        
        # Put in incoming queue
        try:
            asyncio.create_task(self.incoming_queue.put(mqtt_message))
        except Exception as e:
            self.logger.error(
                "Failed to queue incoming message",
                error=str(e),
                topic=message.topic,
            )
        
        # Log message
        self.logger.debug(
            "Message received",
            topic=message.topic,
            qos=message.qos,
            retain=message.retain,
            payload_size=len(message.payload),
        )
        
        # Call message callbacks
        for callback in self.on_message_callbacks:
            try:
                callback(mqtt_message)
            except Exception as e:
                self.logger.error(
                    "Message callback failed",
                    error=str(e),
                    topic=message.topic,
                    callback=str(callback),
                )
    
    def _on_publish(self, client, userdata, mid):
        """Handle publish callback."""
        self.logger.debug("Message published", message_id=mid)
    
    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Handle subscribe callback."""
        self.logger.info(
            "Subscribed to topic",
            message_id=mid,
            granted_qos=granted_qos,
        )
    
    def _on_log(self, client, userdata, level, buf):
        """Handle log callback."""
        if level >= mqtt.MQTT_LOG_WARNING:
            self.logger.warning("MQTT client log", level=level, message=buf)
        elif self.config.debug:
            self.logger.debug("MQTT client log", level=level, message=buf)
    
    def _subscribe_topics(self):
        """Subscribe to required topics."""
        if not self.connected or not self.client:
            return
        
        # Subscribe with QoS 1 for reliable delivery
        topics = [
            (self.input_topic, self.config.mqtt_qos),
            (self.command_topic, self.config.mqtt_qos),
        ]
        
        result, mid = self.client.subscribe(topics)
        
        if result == mqtt.MQTT_ERR_SUCCESS:
            self.logger.info(
                "Subscribed to topics",
                topics=[t[0] for t in topics],
                qos=[t[1] for t in topics],
            )
        else:
            self.logger.error(
                "Failed to subscribe to topics",
                error=mqtt.error_string(result),
                topics=[t[0] for t in topics],
            )
    
    def _schedule_reconnect(self):
        """Schedule reconnection attempt."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.critical(
                "Maximum reconnection attempts reached",
                attempts=self.reconnect_attempts,
                max_attempts=self.max_reconnect_attempts,
            )
            return
        
        self.reconnect_attempts += 1
        delay = min(30, 2 ** self.reconnect_attempts)  # Exponential backoff
        
        self.logger.info(
            "Scheduling reconnection attempt",
            attempt=self.reconnect_attempts,
            delay_seconds=delay,
        )
        
        asyncio.create_task(self._reconnect_after_delay(delay))
    
    async def _reconnect_after_delay(self, delay: float):
        """Reconnect after delay."""
        await asyncio.sleep(delay)
        
        if not self.connected:
            self.logger.info("Attempting reconnection")
            await self.connect()
    
    def _publish_status(self, status: str):
        """Publish status message.
        
        Args:
            status: Status string (connected, disconnected, error, etc.)
        """
        status_message = {
            "node_id": self.config.node_id,
            "service": self.config.service_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "model_loaded": self.engine.model_loaded,
            "engine_stats": self.engine.get_stats()["engine"],
        }
        
        self.publish(
            topic=self.status_topic,
            payload=json.dumps(status_message),
            qos=1,
            retain=True,
        )
    
    async def connect(self) -> bool:
        """Connect to MQTT broker.
        
        Returns:
            True if successful
        """
        try:
            if self.client is None:
                self._setup_client()
            
            # Parse broker URL
            broker_url = self.config.mqtt_broker_url
            if broker_url.startswith("mqtt://"):
                broker_url = broker_url[7:]
            elif broker_url.startswith("tcp://"):
                broker_url = broker_url[6:]
            
            # Split host and port
            if ":" in broker_url:
                host, port_str = broker_url.split(":", 1)
                port = int(port_str)
            else:
                host = broker_url
                port = 1883
            
            # Connect
            self.logger.info(
                "Connecting to MQTT broker",
                host=host,
                port=port,
                client_id=self.config.mqtt_client_id,
            )
            
            self.client.connect(host, port, keepalive=self.config.mqtt_keepalive)
            self.client.loop_start()
            
            # Wait for connection
            await asyncio.sleep(2)  # Give time for connection
            
            if self.connected:
                self.logger.info("MQTT client connected successfully")
                return True
            else:
                self.connection_errors += 1
                self.logger.error("MQTT client failed to connect")
                return False
                
        except Exception as e:
            self.connection_errors += 1
            self.logger.error(
                "Failed to connect to MQTT broker",
                error=str(e),
                broker_url=self.config.mqtt_broker_url,
            )
            return False
    
    async def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client and self.connected:
            # Publish disconnecting status
            self._publish_status("disconnecting")
            
            # Disconnect
            self.client.disconnect()
            self.client.loop_stop()
            self.connected = False
            
            self.logger.info("Disconnected from MQTT broker")
    
    def publish(
        self,
        topic: str,
        payload: Any,
        qos: int = 0,
        retain: bool = False,
    ) -> bool:
        """Publish message to MQTT topic.
        
        Args:
            topic: MQTT topic
            payload: Message payload (string, bytes, or dict)
            qos: Quality of service (0, 1, 2)
            retain: Retain message
            
        Returns:
            True if successful
        """
        if not self.connected or not self.client:
            self.logger.warning("Cannot publish, not connected", topic=topic)
            return False
        
        try:
            # Convert payload to bytes
            if isinstance(payload, dict):
                payload_bytes = json.dumps(payload).encode('utf-8')
            elif isinstance(payload, str):
                payload_bytes = payload.encode('utf-8')
            elif isinstance(payload, bytes):
                payload_bytes = payload
            else:
                # Try to convert to string
                payload_bytes = str(payload).encode('utf-8')
            
            # Publish message
            result = self.client.publish(
                topic=topic,
                payload=payload_bytes,
                qos=qos,
                retain=retain,
            )
            
            # Check result
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.messages_sent += 1
                self.logger.debug(
                    "Message published",
                    topic=topic,
                    qos=qos,
                    retain=retain,
                    payload_size=len(payload_bytes),
                )
                return True
            else:
                self.logger.error(
                    "Failed to publish message",
                    topic=topic,
                    error=mqtt.error_string(result.rc),
                )
                return False
                
        except Exception as e:
            self.logger.error(
                "Exception publishing message",
                error=str(e),
                topic=topic,
            )
            return False
    
    async def process_incoming_messages(self):
        """Process incoming messages from queue."""
        self.logger.info("Starting incoming message processor")
        
        while True:
            try:
                # Get message from queue
                message = await self.incoming_queue.get()
                
                # Process message based on topic
                await self._process_message(message)
                
                # Mark as done
                self.incoming_queue.task_done()
                
            except asyncio.CancelledError:
                self.logger.info("Incoming message processor cancelled")
                break
                
            except Exception as e:
                self.logger.error(
                    "Error processing incoming message",
                    error=str(e),
                    exc_info=True,
                )
                await asyncio.sleep(1)  # Avoid tight error loop
    
    async def _process_message(self, message: MQTTMessage):
        """Process incoming message.
        
        Args:
            message: MQTT message
        """
        with self.logger.time_operation("process_mqtt_message"):
            try:
                # Parse payload
                payload = message.payload_json
                
                # Process based on topic pattern
                if message.topic.startswith("ids/edge/"):
                    await self._process_edge_message(message.topic, payload)
                    
                elif message.topic == self.command_topic:
                    await self._process_command_message(payload)
                    
                else:
                    self.logger.warning(
                        "Unhandled topic",
                        topic=message.topic,
                        payload_keys=list(payload.keys()),
                    )
                    
            except json.JSONDecodeError:
                self.logger.error(
                    "Invalid JSON payload",
                    topic=message.topic,
                    payload=message.payload_str[:100],  # First 100 chars
                )
                
            except Exception as e:
                self.logger.error(
                    "Failed to process message",
                    error=str(e),
                    topic=message.topic,
                    payload_keys=list(payload.keys()) if isinstance(payload, dict) else "N/A",
                )
    
    async def _process_edge_message(self, topic: str, payload: Dict[str, Any]):
        """Process edge-related message.
        
        Args:
            topic: MQTT topic
            payload: Message payload
        """
        # Extract node ID from topic
        # Format: ids/edge/{node_id}/features
        topic_parts = topic.split('/')
        if len(topic_parts) >= 4:
            node_id = topic_parts[2]
        else:
            node_id = "unknown"
        
        # Check message type
        if "features" in topic:
            await self._process_features_message(node_id, payload)
        elif "status" in topic:
            await self._process_status_message(node_id, payload)
        else:
            self.logger.debug(
                "Unhandled edge topic",
                node_id=node_id,
                topic=topic,
                payload_type=type(payload),
            )
    
    async def _process_features_message(self, node_id: str, payload: Dict[str, Any]):
        """Process features message for inference.
        
        Args:
            node_id: Edge node ID
            payload: Features payload
        """
        if not self.engine.model_loaded:
            self.logger.warning("Ignoring features, model not loaded", node_id=node_id)
            return
        
        # Extract features
        features = payload.get("features")
        if not features:
            self.logger.warning("No features in payload", node_id=node_id)
            return
        
        # Validate features
        try:
            import numpy as np
            features_array = np.array(features, dtype=np.float32)
        except Exception as e:
            self.logger.error("Invalid features format", error=str(e), node_id=node_id)
            return
        
        # Get additional metadata
        metadata = {
            "node_id": node_id,
            "timestamp": payload.get("timestamp"),
            "device_id": payload.get("device_id"),
            "flow_id": payload.get("flow_id"),
            "request_id": payload.get("request_id"),
        }
        
        # Perform inference
        try:
            response = await self.engine.predict(features_array, metadata)
            result = response.result
            
            # Create inference event
            inference_event = {
                "event_id": f"inf_{int(time.time())}",
                "node_id": node_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_id": result.model_id,
                "inference_result": {
                    "is_anomaly": result.is_anomaly,
                    "anomaly_score": result.anomaly_score,
                    "confidence": result.confidence,
                    "inference_time_ms": result.inference_time_ms,
                },
                "metadata": {
                    "processing_time_ms": response.processing_time_ms,
                    "queue_time_ms": (time.time() - metadata.get("timestamp", time.time())) * 1000,
                    **metadata,
                },
            }
            
            # Publish inference result
            output_topic = self.output_topic.replace("+", node_id)
            self.publish(
                topic=output_topic,
                payload=json.dumps(inference_event),
                qos=self.config.mqtt_qos,
            )
            
            self.logger.info(
                "Inference completed",
                node_id=node_id,
                is_anomaly=result.is_anomaly,
                anomaly_score=result.anomaly_score,
                confidence=result.confidence,
                inference_time_ms=result.inference_time_ms,
            )
            
        except Exception as e:
            self.logger.error(
                "Inference failed",
                error=str(e),
                node_id=node_id,
                features_shape=features_array.shape,
            )
    
    async def _process_status_message(self, node_id: str, payload: Dict[str, Any]):
        """Process status message from edge node.
        
        Args:
            node_id: Edge node ID
            payload: Status payload
        """
        self.logger.debug(
            "Status message received",
            node_id=node_id,
            status=payload.get("status"),
            timestamp=payload.get("timestamp"),
        )
        
        # Could store in database or forward to dashboard
    
    async def _process_command_message(self, payload: Dict[str, Any]):
        """Process command message.
        
        Args:
            payload: Command payload
        """
        command = payload.get("command")
        target_node = payload.get("node_id")
        
        # Check if command is for this node or all nodes
        if target_node and target_node != self.config.node_id:
            return  # Not for this node
        
        self.logger.info(
            "Processing command",
            command=command,
            target_node=target_node,
        )
        
        if command == "reload_model":
            model_path = payload.get("model_path", self.config.model_path)
            await self.engine.load_model(model_path)
            
        elif command == "get_stats":
            stats = self.engine.get_stats()
            self.publish(
                topic=f"ids/cloud/response/ml/stats",
                payload=json.dumps(stats),
                qos=1,
            )
            
        elif command == "health_check":
            health = await self.engine.health_check()
            self.publish(
                topic=f"ids/cloud/response/ml/health",
                payload=json.dumps(health),
                qos=1,
            )
            
        elif command == "shutdown":
            self.logger.warning("Shutdown command received")
            # In production, you'd signal the main process to shutdown
            
        else:
            self.logger.warning("Unknown command", command=command)
    
    def add_connect_callback(self, callback: Callable):
        """Add connect callback.
        
        Args:
            callback: Callback function
        """
        self.on_connect_callbacks.append(callback)
    
    def add_message_callback(self, callback: Callable):
        """Add message callback.
        
        Args:
            callback: Callback function
        """
        self.on_message_callbacks.append(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get MQTT client statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "connected": self.connected,
            "reconnect_attempts": self.reconnect_attempts,
            "messages_received": self.messages_received,
            "messages_sent": self.messages_sent,
            "connection_errors": self.connection_errors,
            "queue_sizes": {
                "incoming": self.incoming_queue.qsize(),
                "outgoing": self.outgoing_queue.qsize(),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }