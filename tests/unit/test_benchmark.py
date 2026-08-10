import pytest

from portguard_ais.evaluation.benchmark import run_synthetic_benchmark


def test_synthetic_benchmark() -> None:
    result = run_synthetic_benchmark(steps=4)
    assert result.input_rows == 16
    assert result.assessments > 0
    assert 0 <= result.maximum_risk_score <= 1


def test_benchmark_requires_two_steps() -> None:
    with pytest.raises(ValueError):
        run_synthetic_benchmark(steps=1)
