from pathlib import Path

import pandas as pd

from portguard_ais.evaluation.article import article_summary_frame, write_article_summary_csv
from portguard_ais.evaluation.benchmark import run_article_benchmark


def test_article_summary_table(tmp_path: Path) -> None:
    benchmark = run_article_benchmark(steps=12)
    frame = article_summary_frame(benchmark)
    assert list(frame["scenario"]) == ["head-on", "crossing", "overtaking"]
    assert frame["classification_consistency"].eq(1.0).all()

    output = write_article_summary_csv(benchmark, tmp_path / "summary.csv")
    reloaded = pd.read_csv(output)
    assert len(reloaded) == 3
    assert set(reloaded["colreg_context"]) == {"Rule 13", "Rule 14", "Rule 15"}
