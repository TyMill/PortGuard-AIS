from pathlib import Path

from portguard_ais.evaluation.synthetic import article_scenarios
from portguard_ais.pipeline import PortGuardPipeline
from portguard_ais.visualization.article import plot_scenario_encounter


def test_article_encounter_plot(tmp_path: Path) -> None:
    frame = article_scenarios(steps=6)
    result = PortGuardPipeline().process_frame(frame)
    output = plot_scenario_encounter(
        frame,
        result.assessments,
        261300001,
        261300002,
        tmp_path / "overtaking.png",
    )
    assert output.is_file()
    assert output.stat().st_size > 0
