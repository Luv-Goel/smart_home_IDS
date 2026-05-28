import json
import io
import logging
import pytest
from unittest.mock import MagicMock, patch

from shared.logging.setup import setup_logging, get_logger
from shared.logging.tracing import get_correlation_id, set_correlation_id
from shared.logging.middleware import LoggingMiddleware
from shared.logging.hooks import log_mqtt_on_connect, WebSocketLogger

# --- Tracing Tests ---


def test_correlation_id_generation():
    """Test that setting correlation ID without value generates a UUID."""
    cid = set_correlation_id()
    assert cid is not None
    assert get_correlation_id() == cid


def test_correlation_id_explicit():
    """Test that setting an explicit correlation ID works."""
    set_correlation_id("test-id-123")
    assert get_correlation_id() == "test-id-123"


# --- Setup & JSON Formatting Tests ---


def test_json_logging_format():
    """Test that structlog is correctly configured to output JSON."""
    stream = io.StringIO()

    # We patch standard logging StreamHandler to capture output
    with patch("logging.StreamHandler", return_value=logging.StreamHandler(stream)):
        setup_logging(log_level="INFO", json_format=True)

        # Reset any correlation ID for deterministic testing
        set_correlation_id("test-corr-id")

        logger = get_logger("test_logger")
        logger.info("test_event", key="value")

        log_output = stream.getvalue()
        assert log_output != ""

        log_data = json.loads(log_output)
        assert log_data["event"] == "test_event"
        assert log_data["key"] == "value"
        assert log_data["correlation_id"] == "test-corr-id"
        assert log_data["logger"] == "test_logger"
        assert log_data["level"] == "info"
        assert "timestamp" in log_data


# --- Middleware Tests ---


@pytest.mark.asyncio
async def test_logging_middleware():
    """Test the FastAPI logging middleware."""
    middleware = LoggingMiddleware(app=MagicMock())

    # Mock request
    mock_request = MagicMock()
    mock_request.method = "GET"
    mock_request.url.path = "/api/test"
    mock_request.headers.get.return_value = "custom-corr-id"
    mock_request.client.host = "127.0.0.1"

    # Mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {}

    async def call_next(request):
        return mock_response

    # Patch structlog logger to verify it's called
    with patch("shared.logging.middleware.logger.info") as mock_info:
        response = await middleware.dispatch(mock_request, call_next)

        assert response == mock_response
        assert response.headers["X-Correlation-ID"] == "custom-corr-id"
        assert get_correlation_id() == "custom-corr-id"

        assert mock_info.call_count == 2

        # Check start log
        start_call_args = mock_info.call_args_list[0][1]
        assert mock_info.call_args_list[0][0][0] == "request_started"
        assert start_call_args["method"] == "GET"
        assert start_call_args["path"] == "/api/test"

        # Check finish log
        finish_call_args = mock_info.call_args_list[1][1]
        assert mock_info.call_args_list[1][0][0] == "request_finished"
        assert finish_call_args["status_code"] == 200
        assert "duration_s" in finish_call_args


# --- Hooks Tests ---


def test_mqtt_on_connect_hook():
    """Test MQTT on_connect logging hook."""
    mock_client = MagicMock()
    mock_client._client_id = b"test_client"

    with patch("shared.logging.hooks.logger.info") as mock_info:
        log_mqtt_on_connect(mock_client, None, None, 0)

        assert mock_info.call_count == 1
        assert mock_info.call_args[0][0] == "mqtt_connected"
        assert mock_info.call_args[1]["result_code"] == 0


def test_websocket_logger():
    """Test WebSocketLogger wrapper."""
    ws_logger = WebSocketLogger("client-123")

    with patch.object(ws_logger.logger, "info") as mock_info:
        ws_logger.on_connect(client_ip="192.168.1.1")

        assert mock_info.call_count == 1
        assert mock_info.call_args[0][0] == "websocket_connected"
        assert mock_info.call_args[1]["client_ip"] == "192.168.1.1"


def test_mqtt_on_connect_hook_failure():
    """Test MQTT on_connect logging hook on failure."""
    mock_client = MagicMock()
    mock_client._client_id = b"test_client"

    with patch("shared.logging.hooks.logger.error") as mock_error:
        log_mqtt_on_connect(mock_client, None, None, 1)

        assert mock_error.call_count == 1
        assert mock_error.call_args[0][0] == "mqtt_connection_failed"
        assert mock_error.call_args[1]["result_code"] == 1


def test_mqtt_on_disconnect_hook():
    """Test MQTT on_disconnect logging hook."""
    mock_client = MagicMock()
    mock_client._client_id = b"test_client"

    with patch("shared.logging.hooks.logger.info") as mock_info:
        from shared.logging.hooks import log_mqtt_on_disconnect

        log_mqtt_on_disconnect(mock_client, None, 1)

        assert mock_info.call_count == 1
        assert mock_info.call_args[0][0] == "mqtt_disconnected"
        assert mock_info.call_args[1]["result_code"] == 1
        assert not mock_info.call_args[1]["expected"]


def test_mqtt_on_message_hook():
    """Test MQTT on_message logging hook."""
    mock_client = MagicMock()
    mock_msg = MagicMock()
    mock_msg.topic = "test/topic"
    mock_msg.qos = 1
    mock_msg.payload = b"test payload"

    with patch("shared.logging.hooks.logger.debug") as mock_debug:
        from shared.logging.hooks import log_mqtt_on_message

        log_mqtt_on_message(mock_client, None, mock_msg)

        assert mock_debug.call_count == 1
        assert mock_debug.call_args[0][0] == "mqtt_message_received"
        assert mock_debug.call_args[1]["topic"] == "test/topic"
        assert mock_debug.call_args[1]["qos"] == 1
        assert mock_debug.call_args[1]["payload_size"] == len(b"test payload")


def test_websocket_logger_events():
    """Test WebSocketLogger wrapper lifecycle events."""
    ws_logger = WebSocketLogger("client-123")

    with patch.object(ws_logger.logger, "info") as mock_info, patch.object(
        ws_logger.logger, "debug"
    ) as mock_debug, patch.object(ws_logger.logger, "error") as mock_error:

        ws_logger.on_disconnect(1001, "going away")
        assert mock_info.call_args[0][0] == "websocket_disconnected"
        assert mock_info.call_args[1]["close_code"] == 1001

        ws_logger.on_message("text", 123)
        assert mock_debug.call_args[0][0] == "websocket_message_received"
        assert mock_debug.call_args[1]["payload_size"] == 123

        exc = ValueError("test error")
        ws_logger.on_error(exc)
        assert mock_error.call_args[0][0] == "websocket_error"
        assert mock_error.call_args[1]["exc_info"] == exc


@pytest.mark.asyncio
async def test_logging_middleware_exception():
    """Test the FastAPI logging middleware when an exception is raised."""
    middleware = LoggingMiddleware(app=MagicMock())

    mock_request = MagicMock()
    mock_request.method = "POST"
    mock_request.url.path = "/api/fail"
    mock_request.headers.get.return_value = "custom-corr-id"
    mock_request.client.host = "127.0.0.1"

    exc = ValueError("Test Failure")

    async def call_next(request):
        raise exc

    with patch("shared.logging.middleware.logger.info"), patch(
        "shared.logging.middleware.logger.exception"
    ) as mock_exception:

        with pytest.raises(ValueError, match="Test Failure"):
            await middleware.dispatch(mock_request, call_next)

        assert mock_exception.call_count == 1
        assert mock_exception.call_args[0][0] == "request_failed"
        assert mock_exception.call_args[1]["method"] == "POST"
        assert mock_exception.call_args[1]["path"] == "/api/fail"
        assert mock_exception.call_args[1]["exc_info"] == exc
        assert "duration_s" in mock_exception.call_args[1]


def test_setup_logging_console_format():
    """Test setup_logging with console formatting."""
    with patch("logging.StreamHandler") as mock_handler:
        setup_logging(log_level="DEBUG", json_format=False)
        assert mock_handler.called


def test_setup_logging_file_format():
    """Test setup_logging with rotating file format."""
    with patch("logging.StreamHandler") as mock_handler, patch(
        "logging.handlers.RotatingFileHandler"
    ) as mock_file_handler:
        setup_logging(log_level="INFO", json_format=True, log_file="test.log")
        assert mock_handler.called
        assert mock_file_handler.called


@pytest.mark.asyncio
async def test_examples():
    """Test the example code."""
    from shared.logging.examples import main

    with patch("shared.logging.examples.logger.info") as mock_info, patch(
        "shared.logging.examples.logger.error"
    ) as mock_error:
        await main()
        assert mock_info.called
        assert mock_error.called
