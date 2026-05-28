import pytest
import math
from fusion_engine.engine import FusionEngine, FusionResult
from fusion_engine.config import FusionConfig


def test_config_initialization():
    config = FusionConfig()
    assert config.beta_0 == -2.0
    assert config.beta_1 == 1.5
    assert config.beta_2 == 1.5
    assert config.beta_3 == 2.0
    assert config.alert_threshold == 0.75


def test_engine_initialization():
    engine = FusionEngine()
    assert isinstance(engine.config, FusionConfig)

    custom_config = FusionConfig(beta_0=0.0, alert_threshold=0.9)
    engine = FusionEngine(config=custom_config)
    assert engine.config.beta_0 == 0.0
    assert engine.config.alert_threshold == 0.9


def test_sigmoid_calculation():
    engine = FusionEngine()
    assert math.isclose(engine._sigmoid(0), 0.5)
    assert engine._sigmoid(100) > 0.99
    assert engine._sigmoid(-100) < 0.01


def test_calculate_score_low_risk():
    engine = FusionEngine()
    result = engine.calculate_score(0.1, 0.1)

    assert isinstance(result, FusionResult)
    # logit = -2.0 + 1.5*0.1 + 1.5*0.1 + 2.0*0.01 = -2.0 + 0.15 + 0.15 + 0.02 = -1.68
    # sigmoid(-1.68) = ~0.157
    assert result.risk_score < 0.2
    assert result.trigger_alert is False
    assert result.details["device_score"] == 0.1
    assert result.details["flow_score"] == 0.1
    assert math.isclose(result.details["interaction_term"], 0.01)


def test_calculate_score_high_risk():
    engine = FusionEngine()
    result = engine.calculate_score(0.9, 0.9)

    # logit = -2.0 + 1.5*0.9 + 1.5*0.9 + 2.0*0.81 = -2.0 + 1.35 + 1.35 + 1.62 = 2.32
    # sigmoid(2.32) = ~0.91
    assert result.risk_score > 0.9
    assert result.trigger_alert is True


def test_calculate_score_mixed_risk():
    # One high, one low
    engine = FusionEngine()
    result = engine.calculate_score(0.9, 0.1)

    # logit = -2.0 + 1.5*0.9 + 1.5*0.1 + 2.0*0.09 = -2.0 + 1.35 + 0.15 + 0.18 = -0.32
    # sigmoid(-0.32) = ~0.42
    assert result.risk_score > 0.3
    assert result.risk_score < 0.5
    assert result.trigger_alert is False


def test_bounds_clamping():
    engine = FusionEngine()
    result1 = engine.calculate_score(-0.5, 1.5)
    result2 = engine.calculate_score(0.0, 1.0)

    assert result1.risk_score == result2.risk_score
    assert result1.details["device_score"] == 0.0
    assert result1.details["flow_score"] == 1.0


def test_confidence_score():
    engine = FusionEngine()

    # Extremely low risk should have high confidence
    low_risk = engine.calculate_score(0.0, 0.0)
    assert low_risk.confidence_score > 0.7

    # Middle risk (~0.5) should have low confidence
    # To get logit=0 (sigmoid=0.5), we need beta_0 + beta_1*x + beta_2*y + beta_3*x*y = 0
    engine.update_config(beta_0=0.0, beta_1=0.0, beta_2=0.0, beta_3=0.0)
    mid_risk = engine.calculate_score(0.5, 0.5)
    assert mid_risk.confidence_score == 0.0


def test_update_config():
    engine = FusionEngine()
    engine.update_config(alert_threshold=0.5, beta_0=-1.0)

    assert engine.config.alert_threshold == 0.5
    assert engine.config.beta_0 == -1.0

    with pytest.raises(ValueError):
        engine.update_config(non_existent_param=1.0)
