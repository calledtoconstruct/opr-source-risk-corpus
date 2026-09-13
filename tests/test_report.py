#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from opr_risk_corpus.report import aggregate, render_markdown  # noqa: E402


class Report(unittest.TestCase):
    def test_aggregate_counts_facets_per_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            sample = {
                "schema": 1,
                "pkgname": "jq",
                "source": "https://github.com/jqlang/jq.git",
                "ref": "jq-1.7",
                "findings": [
                    {"facet": "net.listen-all", "severity": "high"},
                    {"facet": "secret.in-tree", "severity": "high"},
                ],
                "checks_run": [],
            }
            (d / "jq_jq-1.7.json").write_text(json.dumps(sample), encoding="utf-8")
            summary = aggregate(d)
            self.assertEqual(summary["projects"]["jq"]["milestones"], 1)
            self.assertEqual(summary["facets"]["net.listen-all"], 1)
            md = render_markdown(summary)
            self.assertIn("jq", md)
            self.assertIn("net.listen-all", md)


if __name__ == "__main__":
    unittest.main()
