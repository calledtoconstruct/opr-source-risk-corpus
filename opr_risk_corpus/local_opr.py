"""Stand up a tiny local OPR tree and emit both sidecars."""

from __future__ import annotations

import json
import os
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opr_risk_corpus.milestones import list_remote_tags, pick_major_milestones
from opr_risk_corpus.runner import scan_ref, safe_stem


def default_pkgs() -> Path:
    env = os.environ.get("OMARCHY_PKGS")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "omarchy-pkgs"


def pkgver_from_tag(tag: str, prefix: str | None) -> str:
    name = tag
    if prefix and name.startswith(prefix):
        name = name[len(prefix) :]
    if name.startswith("v") and name[1:2].isdigit():
        name = name[1:]
    return name


def write_desc(staging: Path, pkgname: str, pkgver: str, pkgrel: str, arch: str) -> None:
    ident = f"{pkgname}-{pkgver}-{pkgrel}-{arch}"
    d = staging / ident
    d.mkdir(parents=True)
    (d / "desc").write_text(
        "\n".join(
            [
                "%FILENAME%",
                f"{ident}.pkg.tar.zst",
                "%NAME%",
                pkgname,
                "%VERSION%",
                f"{pkgver}-{pkgrel}",
                "%ARCH%",
                arch,
                "",
            ]
        ),
        encoding="utf-8",
    )


def make_channel_db(repo_dir: Path, packages: list[dict[str, str]], arch: str) -> Path:
    repo_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="opr-db-"))
    members: list[str] = []
    for p in packages:
        ident = f"{p['pkgname']}-{p['pkgver']}-{p['pkgrel']}-{arch}"
        write_desc(staging, p["pkgname"], p["pkgver"], p["pkgrel"], arch)
        (repo_dir / f"{ident}.pkg.tar.zst").write_bytes(b"synthetic-package\n")
        members.append(ident)
    db = repo_dir / "omarchy.db.tar.zst"
    # pacman dbs are often zstd; ingest only needs tar of */desc
    tar_path = repo_dir / "omarchy.db.tar"
    with tarfile.open(tar_path, "w") as tar:
        for name in members:
            tar.add(staging / name, arcname=name)
    tar_path.replace(db)
    return db


def write_risk_sidecar(
    repo_dir: Path,
    *,
    channel: str,
    arch: str,
    entries: dict[str, Any],
) -> Path:
    payload = {
        "schema": 1,
        "channel": channel,
        "arch": arch,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "risks": entries,
    }
    path = repo_dir / "omarchy.risk.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def run_local_opr(
    packages_yaml: Path,
    *,
    repo_root: Path,
    pkgs: Path,
    scanner: Path,
    channel: str = "edge",
    arch: str = "x86_64",
    max_majors: int = 1,
    timeout: int = 600,
    log=None,
) -> dict[str, Path]:
    log = log or __import__("sys").stderr
    specs = _load_demo(packages_yaml)
    if os.environ.get("OPR_DEMO_LIMIT"):
        specs = specs[: int(os.environ["OPR_DEMO_LIMIT"])]
    resolved: list[dict[str, str]] = []
    scans: dict[str, Any] = {}
    for spec in specs:
        prefix = spec.get("tag_prefix") or None
        if prefix == "":
            prefix = None
        tags = list_remote_tags(spec["git"])
        refs = pick_major_milestones(tags, max_majors=max_majors, prefix=prefix)
        if not refs:
            print(f"no tags for {spec['pkgname']}", file=log)
            continue
        ref = refs[0]
        pkgver = pkgver_from_tag(ref, prefix)
        resolved.append(
            {
                "pkgname": spec["pkgname"],
                "pkgver": pkgver,
                "pkgrel": "1",
                "git": spec["git"],
                "ref": ref,
                "purl": spec.get("purl") or "",
            }
        )
        print(f"{spec['pkgname']} {ref} -> {pkgver}-1", file=log)

    repo_dir = repo_root / channel / arch
    make_channel_db(repo_dir, resolved, arch)

    feed = repo_root / "advisories-feed"
    feed.mkdir(parents=True, exist_ok=True)
    purl_map = repo_root / "purls"
    purl_map.write_text(
        "".join(
            f"{p['pkgname']} {p['purl']}\n" for p in resolved if p.get("purl")
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["OMARCHY_REPO_ROOT"] = str(repo_root)
    fetch = pkgs / "bin" / "fetch-advisories"
    sync = pkgs / "bin" / "sync-advisories"
    if fetch.is_file():
        cmd = [
            str(fetch),
            "--mirror",
            channel,
            "--arch",
            arch,
            "--feed",
            str(feed),
            "--purl-map",
            str(purl_map),
        ]
        print("fetch-advisories...", file=log)
        subprocess.run(cmd, check=False, env=env)
    if sync.is_file():
        cmd = [
            str(sync),
            "--mirror",
            channel,
            "--arch",
            arch,
            "--feed",
            str(feed),
            "--no-sign",
        ]
        print("sync-advisories...", file=log)
        subprocess.run(cmd, check=False, env=env)

    risk_entries: dict[str, Any] = {}
    for p in resolved:
        dest = repo_root / "scans" / f"{safe_stem(p['pkgname'], p['ref'])}.json"
        print(f"source-risk {p['pkgname']} {p['ref']}", file=log)
        report = scan_ref(
            scanner=scanner,
            git_url=p["git"],
            ref=p["ref"],
            pkgname=p["pkgname"],
            out_file=dest,
            timeout=timeout,
        )
        key = f"{p['pkgname']}:{p['pkgver']}-{p['pkgrel']}:{arch}"
        risk_entries[key] = {
            "pkgname": p["pkgname"],
            "pkgver": p["pkgver"],
            "pkgrel": p["pkgrel"],
            "arch": arch,
            "source": p["git"],
            "ref": p["ref"],
            "commit": report.get("commit") or "",
            "scan_status": "error" if report.get("error") else "ok",
            "finding_count": len(report.get("findings") or []),
            "facets": sorted(
                {f.get("facet") for f in report.get("findings") or [] if f.get("facet")}
            ),
            "findings": report.get("findings") or [],
        }
        scans[p["pkgname"]] = dest

    risk_path = write_risk_sidecar(repo_dir, channel=channel, arch=arch, entries=risk_entries)
    return {
        "repo_dir": repo_dir,
        "advisories": repo_dir / "omarchy.advisories.json",
        "risk": risk_path,
        **scans,
    }


def _load_demo(path: Path) -> list[dict[str, Any]]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out = []
    for item in data.get("packages") or []:
        out.append(
            {
                "pkgname": item["pkgname"],
                "git": item["git"],
                "tag_prefix": item.get("tag_prefix") or None,
                "purl": item.get("purl") or "",
            }
        )
    return out
