import asyncio
import structlog
from shared_mqtt import (
    MQTTConfig,
    MQTTConnectionManager,
    IDSMQTTTopic,
    TopicBuilder,
    MQTTMessageData
)

logger = structlog.get_logger()

async def handle_health_message(topic: str, payload: dict):
    logger.info("Received health message", topic=topic, payload=payload)

async def main():
    # 1. Configure the connection
    config = MQTTConfig(
        broker="localhost", # Assume a local broker is running
        port=1883,
        client_id="example_client"
    )

    # 2. Use the async context manager to handle connect/disconnect automatically
    async with MQTTConnectionManager(config) as mqtt:

        # 3. Subscribe to a predefined topic
        await mqtt.subscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, handle_health_message)

        # Or build a dynamic topic
        node_topic = TopicBuilder.build_node_topic(IDSMQTTTopic.ALERTS_CRITICAL.value, "node_01")
        await mqtt.subscribe(node_topic, handle_health_message)

        # 4. Wait a bit for the connection to fully establish in the background
        await asyncio.sleep(1)

        # 5. Publish a simple dictionary
        await mqtt.publish(IDSMQTTTopic.SYSTEM_HEALTH.value, {"status": "ok", "cpu": 45})

        # 6. Publish a strongly-typed message
        msg = MQTTMessageData(source_node="edge_1", payload={"alert": "Suspicious pattern detected"})
        await mqtt.publish(node_topic, msg)

        # Wait to receive messages
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
