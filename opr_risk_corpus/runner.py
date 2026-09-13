from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from opr_risk_corpus.milestones import list_remote_tags, pick_major_milestones


def default_scanner() -> Path:
    env = os.environ.get("OPR_SOURCE_RISK")
    if env:
        return Path(env)
    sibling = Path(__file__).resolve().parents[2] / "opr-source-risk" / "bin" / "opr-source-risk"
    if sibling.is_file():
        return sibling
    return Path("opr-source-risk")


def scan_ref(
    *,
    scanner: Path,
    git_url: str,
    ref: str,
    pkgname: str,
    out_file: Path,
    timeout: int,
) -> dict[str, Any]:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(scanner),
        "scan",
        "--git",
        git_url,
        "--ref",
        ref,
        "--pkgname",
        pkgname,
        "--out",
        str(out_file),
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        payload = {"error": "timeout", "pkgname": pkgname, "ref": ref, "source": git_url}
        out_file.write_text(json.dumps(payload), encoding="utf-8")
        return payload
    except OSError as exc:
        payload = {"error": str(exc), "pkgname": pkgname, "ref": ref, "source": git_url}
        out_file.write_text(json.dumps(payload), encoding="utf-8")
        return payload
    if proc.returncode not in (0, 2) or not out_file.is_file():
        payload = {
            "error": proc.stderr.strip() or f"exit {proc.returncode}",
            "pkgname": pkgname,
            "ref": ref,
            "source": git_url,
        }
        out_file.write_text(json.dumps(payload), encoding="utf-8")
        return payload
    return json.loads(out_file.read_text(encoding="utf-8"))


def safe_stem(name: str, ref: str) -> str:
    raw = f"{name}_{ref}"
    return "".join(c if c.isalnum() or c in "-._" else "_" for c in raw)


def run_corpus(
    projects: list[dict[str, Any]],
    *,
    out_dir: Path,
    scanner: Path,
    max_majors: int,
    timeout: int,
    limit: int | None = None,
    log=sys.stderr,
) -> list[Path]:
    written: list[Path] = []
    selected = projects[:limit] if limit else projects
    for project in selected:
        name = project["name"]
        git_url = project["git"]
        print(f"== {project['repo']} ==", file=log)
        try:
            tags = list_remote_tags(git_url)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            print(f"  tags failed: {exc}", file=log)
            fail = out_dir / f"{safe_stem(name, 'tags')}.json"
            fail.write_text(
                json.dumps({"error": f"tags: {exc}", "pkgname": name, "source": git_url}),
                encoding="utf-8",
            )
            written.append(fail)
            continue
        refs = pick_major_milestones(tags, max_majors=max_majors)
        if not refs:
            print("  no semver majors", file=log)
            continue
        for ref in refs:
            dest = out_dir / f"{safe_stem(name, ref)}.json"
            print(f"  scan {ref} -> {dest.name}", file=log)
            scan_ref(
                scanner=scanner,
                git_url=git_url,
                ref=ref,
                pkgname=name,
                out_file=dest,
                timeout=timeout,
            )
            written.append(dest)
    return written
