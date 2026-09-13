#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from opr_risk_corpus.milestones import pick_major_milestones  # noqa: E402


class PickMajors(unittest.TestCase):
    def test_picks_latest_per_major_and_caps(self) -> None:
        tags = [
            "v1.0.0",
            "v1.2.3",
            "v2.0.0-rc1",
            "v2.1.0",
            "v2.1.1",
            "v3.0.0",
            "nightly",
            "v0.9.0",
        ]
        got = pick_major_milestones(tags, max_majors=3)
        self.assertEqual(got, ["v3.0.0", "v2.1.1", "v1.2.3"])

    def test_skips_prerelease_by_default(self) -> None:
        tags = ["v2.0.0-beta", "v2.0.0-rc.1", "v1.0.0"]
        got = pick_major_milestones(tags, max_majors=5)
        self.assertEqual(got, ["v1.0.0"])

    def test_plain_semver_without_v(self) -> None:
        tags = ["1.0.0", "1.1.0", "2.0.0"]
        got = pick_major_milestones(tags, max_majors=5)
        self.assertEqual(got, ["2.0.0", "1.1.0"])

    def test_prefixed_tags(self) -> None:
        tags = ["jq-1.6", "jq-1.7.1", "jq-1.7"]
        got = pick_major_milestones(tags, max_majors=5)
        self.assertEqual(got, ["jq-1.7.1"])


if __name__ == "__main__":
    unittest.main()
