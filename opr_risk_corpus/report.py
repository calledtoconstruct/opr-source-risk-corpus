from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def aggregate(scan_dir: Path) -> dict[str, Any]:
    facets: Counter[str] = Counter()
    projects: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"milestones": 0, "findings": 0, "by_ref": []}
    )
    scans = 0
    errors = 0
    for path in sorted(scan_dir.glob("*.json")):
        if path.name in {"summary.json"}:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors += 1
            continue
        if data.get("error"):
            errors += 1
            continue
        scans += 1
        name = data.get("pkgname") or path.stem
        findings = data.get("findings") or []
        rec = projects[name]
        rec["milestones"] += 1
        rec["findings"] += len(findings)
        rec["by_ref"].append(
            {
                "ref": data.get("ref"),
                "findings": len(findings),
                "facets": sorted({f.get("facet", "") for f in findings if f.get("facet")}),
            }
        )
        for f in findings:
            facet = f.get("facet")
            if facet:
                facets[facet] += 1
    return {
        "scans": scans,
        "errors": errors,
        "facets": dict(facets.most_common()),
        "projects": dict(projects),
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# opr-source-risk corpus report",
        "",
        f"Scans: {summary.get('scans', 0)}. Errors: {summary.get('errors', 0)}.",
        "",
        "## Findings by facet",
        "",
        "| facet | count |",
        "|---|---|",
    ]
    facets = summary.get("facets") or {}
    if not facets:
        lines.append("| (none) | 0 |")
    for facet, count in facets.items():
        lines.append(f"| {facet} | {count} |")
    lines += ["", "## Projects", "", "| project | milestones | findings |", "|---|---|---|"]
    for name, rec in sorted((summary.get("projects") or {}).items()):
        lines.append(f"| {name} | {rec.get('milestones', 0)} | {rec.get('findings', 0)} |")
    lines += ["", "## Per milestone", ""]
    for name, rec in sorted((summary.get("projects") or {}).items()):
        lines.append(f"### {name}")
        lines.append("")
        for row in rec.get("by_ref") or []:
            facets = ", ".join(row.get("facets") or []) or "none"
            lines.append(
                f"- `{row.get('ref')}`: {row.get('findings', 0)} findings ({facets})"
            )
        lines.append("")
    return "\n".join(lines) + "\n"
