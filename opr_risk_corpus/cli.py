from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from opr_risk_corpus.projects import load_projects
from opr_risk_corpus.report import aggregate, render_markdown
from opr_risk_corpus.runner import default_scanner, run_corpus

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="opr-source-risk-corpus",
        description="Scan major milestones of curated Linux GitHub projects with opr-source-risk.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    scan = sub.add_parser("scan", help="clone major tags and run the v1 scanner")
    scan.add_argument("--projects", type=Path, default=ROOT / "projects.yaml")
    scan.add_argument("--out-dir", type=Path, default=ROOT / "out")
    scan.add_argument("--scanner", type=Path, default=default_scanner())
    scan.add_argument("--max-majors", type=int, default=3)
    scan.add_argument("--timeout", type=int, default=600)
    scan.add_argument("--limit", type=int, default=0, help="scan only the first N projects (0=all)")

    report = sub.add_parser("report", help="rebuild summary from out/*.json")
    report.add_argument("--out-dir", type=Path, default=ROOT / "out")

    listed = sub.add_parser("list", help="print the curated project list")
    listed.add_argument("--projects", type=Path, default=ROOT / "projects.yaml")

    args = parser.parse_args(argv)
    if args.cmd == "list":
        for p in load_projects(args.projects):
            print(f"{p['repo']}\t{p['git']}")
        return 0

    if args.cmd == "report":
        return _write_report(args.out_dir)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    projects = load_projects(args.projects)
    limit = args.limit or None
    run_corpus(
        projects,
        out_dir=args.out_dir,
        scanner=args.scanner,
        max_majors=args.max_majors,
        timeout=args.timeout,
        limit=limit,
    )
    return _write_report(args.out_dir)


def _write_report(out_dir: Path) -> int:
    summary = aggregate(out_dir)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    md = render_markdown(summary)
    (out_dir / "REPORT.md").write_text(md, encoding="utf-8")
    sys.stdout.write(md)
    return 0 if summary.get("errors", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
