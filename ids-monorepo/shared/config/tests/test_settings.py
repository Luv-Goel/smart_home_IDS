import os
import pytest
from unittest.mock import patch
from shared.config import settings, reload

def test_yaml_loading():
    # By default, APP_ENV=dev if not set
    with patch.dict(os.environ, {"APP_ENV": "dev"}, clear=True):
        new_settings = reload()
        assert new_settings.app.name == "Smart Home IDS (Dev)"
        assert new_settings.app.debug is True
        assert new_settings.database.pool_size == 5

def test_env_overrides():
    with patch.dict(os.environ, {
        "APP_ENV": "dev",
        "APP__NAME": "Overridden Name",
        "DATABASE__POOL_SIZE": "99",
        "SECRET_KEY": "test-secret"
    }, clear=True):
        new_settings = reload()
        assert new_settings.app.name == "Overridden Name"
        assert new_settings.database.pool_size == 99
        assert new_settings.secret_key == "test-secret"

def test_edge_config_parsing():
    with patch.dict(os.environ, {"APP_ENV": "edge"}, clear=True):
        new_settings = reload()
        assert new_settings.app.name == "Smart Home IDS (Edge - Raspberry Pi)"
        assert new_settings.app.debug is False
        assert new_settings.inference.num_threads == 2

def test_hot_reload():
    with patch.dict(os.environ, {"APP_ENV": "dev"}, clear=True):
        s1 = reload()
        assert s1.app.log_level == "DEBUG"

    with patch.dict(os.environ, {"APP_ENV": "dev", "APP__LOG_LEVEL": "WARNING"}, clear=True):
        s2 = reload()
        assert s2.app.log_level == "WARNING"
        assert s1 is not s2
