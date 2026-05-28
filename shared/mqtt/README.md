# Shared MQTT Infrastructure

This package provides a production-grade, asynchronous MQTT infrastructure for the Smart Home IoT IDS. It handles robust connections, auto-reconnects with exponential backoff, serialization, and central topic management.

## Features

- **Asyncio Native**: Built on top of `aiomqtt`.
- **Auto-reconnect**: Exponential backoff built-in.
- **Strongly Typed Configuration**: Uses Pydantic v2.
- **Automatic Serialization**: Handles Python dicts, strings, and Pydantic models automatically.
- **Topic Registry**: Centralized management of system topics.
- **TLS & Auth Support**: Fully supports secure connections.

## Installation

This is an internal shared package. It is intended to be included via your `pyproject.toml` or `requirements.txt` referring to this local directory.

## Quick Start

```python
import asyncio
from shared_mqtt import MQTTConfig, MQTTConnectionManager, IDSMQTTTopic

async def on_message(topic: str, payload: dict):
    print(f"Received on {topic}: {payload}")

async def main():
    config = MQTTConfig(broker="localhost")

    async with MQTTConnectionManager(config) as mqtt:
        await mqtt.subscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, on_message)
        await mqtt.publish(IDSMQTTTopic.SYSTEM_HEALTH.value, {"status": "ok"})
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
```

See `examples/basic_pub_sub.py` for more details.
