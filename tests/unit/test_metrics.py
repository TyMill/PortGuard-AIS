import pytest

from portguard_ais.evaluation.metrics import binary_alert_metrics


def test_binary_metrics() -> None:
    metrics = binary_alert_metrics([True, True, False, False], [True, False, True, False])
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.f1 == 0.5
    assert metrics.false_alert_rate == 0.5


def test_binary_metrics_length_validation() -> None:
    with pytest.raises(ValueError):
        binary_alert_metrics([True], [True, False])
