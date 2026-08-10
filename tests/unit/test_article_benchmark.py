from portguard_ais.evaluation.benchmark import run_article_benchmark


def test_article_benchmark_is_reproducible() -> None:
    result = run_article_benchmark(steps=12)

    assert result.input_rows == 72
    assert result.unique_vessels == 6
    assert result.assessments == 36
    assert len(result.scenarios) == 3
    assert all(item.classification_consistency == 1.0 for item in result.scenarios)
    assert all(item.near_miss_detected for item in result.scenarios)


def test_article_benchmark_scenarios_have_expected_rules() -> None:
    result = run_article_benchmark(steps=12)
    rules = {item.name: item.expected_colreg_rule for item in result.scenarios}
    assert rules == {"head-on": "Rule 14", "crossing": "Rule 15", "overtaking": "Rule 13"}
