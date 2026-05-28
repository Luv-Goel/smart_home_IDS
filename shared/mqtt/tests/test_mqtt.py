import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiomqtt import MqttError
from shared_mqtt.models import MQTTConfig, MQTTMessageData
from shared_mqtt.client import MQTTConnectionManager
from shared_mqtt.topics import IDSMQTTTopic
from shared_mqtt.serializer import MessageSerializer


@pytest.fixture
def config():
    return MQTTConfig(broker="localhost", port=1883, client_id="test_client")


@pytest.mark.asyncio
async def test_serializer():
    data = {"test": 123}
    encoded = MessageSerializer.serialize(data)
    assert isinstance(encoded, bytes)

    decoded = MessageSerializer.deserialize(encoded)
    assert decoded == data


@pytest.mark.asyncio
async def test_pydantic_serializer():
    msg = MQTTMessageData(payload={"test": "abc"})
    encoded = MessageSerializer.serialize(msg)
    assert isinstance(encoded, bytes)

    decoded = MessageSerializer.deserialize(encoded)
    assert decoded["payload"] == {"test": "abc"}
    assert "timestamp" in decoded


@pytest.mark.asyncio
async def test_connection_manager_init(config):
    manager = MQTTConnectionManager(config)
    assert manager.is_connected is False
    assert manager._running is False


@pytest.mark.asyncio
async def test_subscribe_unsubscribe(config):
    manager = MQTTConnectionManager(config)

    async def dummy_callback(topic, payload):
        pass

    await manager.subscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, dummy_callback)
    assert IDSMQTTTopic.SYSTEM_HEALTH.value in manager._subscriptions
    assert dummy_callback in manager._subscriptions[IDSMQTTTopic.SYSTEM_HEALTH.value]

    await manager.unsubscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, dummy_callback)
    assert IDSMQTTTopic.SYSTEM_HEALTH.value not in manager._subscriptions


@pytest.mark.asyncio
async def test_publish_not_connected(config):
    manager = MQTTConnectionManager(config)
    result = await manager.publish(IDSMQTTTopic.SYSTEM_HEALTH.value, {"status": "ok"})
    assert result is False


@pytest.mark.asyncio
async def test_publish_connected(config):
    manager = MQTTConnectionManager(config)
    manager._connected = True
    manager._client = AsyncMock()

    result = await manager.publish(IDSMQTTTopic.SYSTEM_HEALTH.value, {"status": "ok"})
    assert result is True
    manager._client.publish.assert_called_once()


@pytest.mark.asyncio
async def test_subscribe_connected(config):
    manager = MQTTConnectionManager(config)
    manager._connected = True
    manager._client = AsyncMock()

    async def dummy_callback(topic, payload):
        pass

    result = await manager.subscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, dummy_callback)
    assert result is True
    manager._client.subscribe.assert_called_once_with(IDSMQTTTopic.SYSTEM_HEALTH.value)


@pytest.mark.asyncio
async def test_unsubscribe_connected(config):
    manager = MQTTConnectionManager(config)
    manager._connected = True
    manager._client = AsyncMock()

    async def dummy_callback(topic, payload):
        pass

    await manager.subscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, dummy_callback)
    manager._client.subscribe.assert_called_once()

    result = await manager.unsubscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, dummy_callback)
    assert result is True
    manager._client.unsubscribe.assert_called_once_with(
        IDSMQTTTopic.SYSTEM_HEALTH.value
    )


@pytest.mark.asyncio
async def test_topic_registry():
    from shared_mqtt.topics import registry, IDSMQTTTopic

    topics = registry.list_topics()
    assert len(topics) >= 9
    assert IDSMQTTTopic.SYSTEM_HEALTH.value in topics

    registry.register("custom/topic", "Custom topic")
    assert "custom/topic" in registry.list_topics()

    desc = registry.get_description("custom/topic")
    assert desc == "Custom topic"

    assert registry.unregister("custom/topic") is True
    assert "custom/topic" not in registry.list_topics()


@pytest.mark.asyncio
async def test_connection_loop_start_stop(config):
    manager = MQTTConnectionManager(config)
    await manager.start()
    assert manager._running is True
    await manager.stop()
    assert manager._running is False


@pytest.mark.asyncio
async def test_safe_invoke_callback(config):
    manager = MQTTConnectionManager(config)
    called = False

    async def cb(topic, payload):
        nonlocal called
        called = True

    await manager._safe_invoke_callback(cb, "test/topic", {"a": 1})
    assert called is True


@pytest.mark.asyncio
async def test_safe_invoke_callback_error(config):
    manager = MQTTConnectionManager(config)

    async def cb(topic, payload):
        raise ValueError("test error")

    # Should not raise
    await manager._safe_invoke_callback(cb, "test/topic", {"a": 1})


@pytest.mark.asyncio
async def test_publish_error(config):
    manager = MQTTConnectionManager(config)
    manager._connected = True
    manager._client = AsyncMock()
    manager._client.publish.side_effect = MqttError("test error")

    result = await manager.publish("test/topic", {"a": 1})
    assert result is False


@pytest.mark.asyncio
async def test_serializer_error_handling():
    # Test fallback to string decoding
    data = b"not json"
    decoded = MessageSerializer.deserialize(data)
    assert decoded == "not json"

    # Test complete decode failure
    data = b"\xff\xff"
    decoded = MessageSerializer.deserialize(data)
    assert decoded == data


@pytest.mark.asyncio
async def test_unsubscribe_not_connected(config):
    manager = MQTTConnectionManager(config)

    async def dummy_callback(topic, payload):
        pass

    await manager.subscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, dummy_callback)
    result = await manager.unsubscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, dummy_callback)
    assert result is True


@pytest.mark.asyncio
async def test_unsubscribe_no_topic(config):
    manager = MQTTConnectionManager(config)
    result = await manager.unsubscribe("nonexistent/topic")
    assert result is True


@pytest.mark.asyncio
async def test_unsubscribe_all(config):
    manager = MQTTConnectionManager(config)
    manager._connected = True
    manager._client = AsyncMock()

    async def dummy_callback(topic, payload):
        pass

    await manager.subscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, dummy_callback)
    result = await manager.unsubscribe(IDSMQTTTopic.SYSTEM_HEALTH.value)
    assert result is True
    manager._client.unsubscribe.assert_called_once_with(
        IDSMQTTTopic.SYSTEM_HEALTH.value
    )


@pytest.mark.asyncio
async def test_publish_unhandled_exception(config):
    manager = MQTTConnectionManager(config)
    manager._connected = True
    manager._client = AsyncMock()
    manager._client.publish.side_effect = Exception("test error")

    result = await manager.publish("test/topic", {"a": 1})
    assert result is False


@pytest.mark.asyncio
async def test_subscribe_error(config):
    manager = MQTTConnectionManager(config)
    manager._connected = True
    manager._client = AsyncMock()
    manager._client.subscribe.side_effect = MqttError("test error")

    async def dummy_callback(topic, payload):
        pass

    result = await manager.subscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, dummy_callback)
    assert result is False


@pytest.mark.asyncio
async def test_unsubscribe_error(config):
    manager = MQTTConnectionManager(config)
    manager._connected = True
    manager._client = AsyncMock()
    manager._client.unsubscribe.side_effect = MqttError("test error")

    async def dummy_callback(topic, payload):
        pass

    await manager.subscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, dummy_callback)
    result = await manager.unsubscribe(IDSMQTTTopic.SYSTEM_HEALTH.value)
    assert result is False


@patch("ssl.create_default_context")
@pytest.mark.asyncio
async def test_tls_config(mock_create_context):
    from shared_mqtt.models import MQTTTLSConfig

    mock_context = MagicMock()
    mock_create_context.return_value = mock_context
    tls_conf = MQTTTLSConfig(ca_certs="/tmp/ca.crt", insecure=True)
    conf = MQTTConfig(broker="localhost", tls=tls_conf)
    manager = MQTTConnectionManager(conf)
    mock_create_context.assert_called_once_with(cafile="/tmp/ca.crt")
    assert manager._tls_context.check_hostname is False


@pytest.mark.asyncio
async def test_unsubscribe_specific_callback_connected(config):
    manager = MQTTConnectionManager(config)
    manager._connected = True
    manager._client = AsyncMock()

    async def dummy_callback1(topic, payload):
        pass

    async def dummy_callback2(topic, payload):
        pass

    await manager.subscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, dummy_callback1)
    await manager.subscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, dummy_callback2)

    # Remove one callback, shouldn't call client.unsubscribe
    result = await manager.unsubscribe(
        IDSMQTTTopic.SYSTEM_HEALTH.value, dummy_callback1
    )
    assert result is True
    manager._client.unsubscribe.assert_not_called()
    assert dummy_callback2 in manager._subscriptions[IDSMQTTTopic.SYSTEM_HEALTH.value]


@pytest.mark.asyncio
async def test_unsubscribe_last_callback_connected(config):
    manager = MQTTConnectionManager(config)
    manager._connected = True
    manager._client = AsyncMock()

    async def dummy_callback(topic, payload):
        pass

    await manager.subscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, dummy_callback)

    # Remove the last callback, should call client.unsubscribe
    result = await manager.unsubscribe(IDSMQTTTopic.SYSTEM_HEALTH.value, dummy_callback)
    assert result is True
    manager._client.unsubscribe.assert_called_once_with(
        IDSMQTTTopic.SYSTEM_HEALTH.value
    )


@pytest.mark.asyncio
async def test_publish_raw_bytes(config):
    manager = MQTTConnectionManager(config)
    manager._connected = True
    manager._client = AsyncMock()

    result = await manager.publish(IDSMQTTTopic.SYSTEM_HEALTH.value, b"raw data")
    assert result is True
    manager._client.publish.assert_called_once()
    args, kwargs = manager._client.publish.call_args
    assert kwargs.get("payload") == b"raw data"


@pytest.mark.asyncio
async def test_context_manager(config):
    async with MQTTConnectionManager(config) as manager:
        assert manager._running is True
    assert manager._running is False
