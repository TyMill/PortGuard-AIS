from pathlib import Path

import pytest

from portguard_ais.evaluation.synthetic import synthetic_scenarios
from portguard_ais.pipeline import PortGuardPipeline
from portguard_ais.visualization.encounter import plot_encounter


def test_plot_encounter(tmp_path: Path) -> None:
    assessment = PortGuardPipeline().process_frame(synthetic_scenarios(steps=2)).assessments[0]
    output = plot_encounter(assessment, tmp_path / "encounter.png")
    assert output.is_file()


def test_plot_requires_positions(tmp_path: Path) -> None:
    assessment = PortGuardPipeline().process_frame(synthetic_scenarios(steps=2)).assessments[0]
    without_positions = assessment.model_copy(update={"own_position": None})
    with pytest.raises(ValueError):
        plot_encounter(without_positions, tmp_path / "encounter.png")
