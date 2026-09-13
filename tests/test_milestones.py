#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from opr_risk_corpus.local_opr import pkgver_from_tag  # noqa: E402
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

    def test_drops_crate_and_start_markers(self) -> None:
        tags = [
            "v0.13.0",
            "alacritty_terminal_v9.4.5",
            "7.0-start",
            "AnyEvent-0.17",
            "start_of_2.8",
            "v2.42.3",
        ]
        got = pick_major_milestones(tags, max_majors=5)
        self.assertEqual(got, ["v2.42.3", "v0.13.0"])

    def test_optional_prefix(self) -> None:
        tags = ["v1.2.0", "release-1.31.5", "v0.9.7"]
        got = pick_major_milestones(tags, max_majors=5, prefix="release-")
        self.assertEqual(got, ["release-1.31.5"])

    def test_v_prefix_does_not_match_vfox(self) -> None:
        tags = ["vfox-v2026.9.8", "v2026.9.4", "v2025.1.0"]
        got = pick_major_milestones(tags, max_majors=5, prefix="v")
        self.assertEqual(got, ["v2026.9.4", "v2025.1.0"])

    def test_pkgver_from_tag(self) -> None:
        self.assertEqual(pkgver_from_tag("v2026.9.4", "v"), "2026.9.4")
        self.assertEqual(pkgver_from_tag("jq-1.8.2", "jq-"), "1.8.2")
        self.assertEqual(pkgver_from_tag("15.2.0", None), "15.2.0")


if __name__ == "__main__":
    unittest.main()
