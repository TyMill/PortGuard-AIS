"""Dependency-free HTML summary reports."""

from html import escape
from pathlib import Path

from portguard_ais.pipeline import ProcessingResult


def write_html_report(result: ProcessingResult, output: str | Path) -> Path:
    """Write a compact standalone report suitable for reproducibility bundles."""
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    top = sorted(result.assessments, key=lambda item: item.risk_score, reverse=True)[:20]
    rows = "".join(
        "<tr>"
        f"<td>{escape(item.encounter_id)}</td>"
        f"<td>{item.own_mmsi}</td>"
        f"<td>{item.target_mmsi}</td>"
        f"<td>{escape(item.encounter_type.value)}</td>"
        f"<td>{item.risk_score:.3f}</td>"
        f"<td>{item.relative_motion.dcpa_nm:.3f}</td>"
        f"<td>{item.relative_motion.tcpa_min:.2f}</td>"
        "</tr>"
        for item in top
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PortGuard-AIS report</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 1rem; }}
.card {{ border: 1px solid #ddd; border-radius: 8px; padding: 1rem; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
th, td {{ border-bottom: 1px solid #ddd; padding: .55rem; text-align: left; }}
.warning {{ padding: 1rem; border-left: 4px solid #b45309; background: #fffbeb; }}
</style>
</head>
<body>
<h1>PortGuard-AIS 1.0 report</h1>
<p class="warning">Research decision support only. This report does not prescribe vessel routes or manoeuvres.</p>
<div class="cards">
<div class="card"><strong>Validated AIS rows</strong><br>{result.validation.output_rows}</div>
<div class="card"><strong>Assessments</strong><br>{len(result.assessments)}</div>
<div class="card"><strong>Emitted alerts</strong><br>{sum(item.emitted for item in result.alerts)}</div>
<div class="card"><strong>Near misses</strong><br>{len(result.near_misses)}</div>
<div class="card"><strong>Hotspot cells</strong><br>{len(result.hotspots)}</div>
</div>
<h2>Highest-risk assessments</h2>
<table>
<thead><tr><th>Encounter</th><th>Own MMSI</th><th>Target MMSI</th><th>Type</th><th>Risk</th><th>DCPA NM</th><th>TCPA min</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</body>
</html>
"""
    target.write_text(html, encoding="utf-8")
    return target
