from __future__ import annotations

import re
import subprocess
from typing import NamedTuple

_PRE = re.compile(r"(?i)(alpha|beta|rc|pre|dev|nightly|snapshot)")
_SEMVER = re.compile(
    r"v?(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?"
)


class Version(NamedTuple):
    major: int
    minor: int
    patch: int
    tag: str


def parse_tag(tag: str) -> Version | None:
    name = tag.split("/")[-1]
    if _PRE.search(name):
        return None
    m = _SEMVER.search(name)
    if not m:
        return None
    return Version(
        int(m.group("major")),
        int(m.group("minor")),
        int(m.group("patch") or 0),
        name,
    )


def pick_major_milestones(tags: list[str], *, max_majors: int = 5) -> list[str]:
    best: dict[int, Version] = {}
    for tag in tags:
        ver = parse_tag(tag)
        if ver is None:
            continue
        cur = best.get(ver.major)
        if cur is None or (ver.minor, ver.patch) > (cur.minor, cur.patch):
            best[ver.major] = ver
    ordered = sorted(best.values(), key=lambda v: v.major, reverse=True)
    return [v.tag for v in ordered[:max_majors]]


def list_remote_tags(git_url: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", git_url],
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    tags: list[str] = []
    for line in out.stdout.splitlines():
        if not line.strip():
            continue
        ref = line.split()[-1]
        if ref.startswith("refs/tags/"):
            tags.append(ref.removeprefix("refs/tags/"))
    return tags
