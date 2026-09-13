# opr-source-risk-corpus

Walks **20 curated Linux-world GitHub projects**, picks **major semver
milestones** (latest tag per major, skip rc/beta), and runs
[`opr-source-risk`](https://github.com/calledtoconstruct/opr-source-risk)
v1 against each ref. Writes JSON per scan plus `REPORT.md`.

This is not CVE ingest and not a live nmap. It is a corpus harness for the
static behavior scanner.

## Projects

See `projects.yaml` (systemd, util-linux, runc, podman, nginx, caddy,
neovim, tmux, jq, ripgrep, fish, wireguard-tools, i3, sway, alacritty,
git, syncthing, restic, OpenVPN, node_exporter).

## Run

Needs `git`, Python 3, PyYAML, and the scanner (sibling checkout or
`OPR_SOURCE_RISK`).

```bash
# first two projects, one major each — smoke
./bin/opr-source-risk-corpus scan --limit 2 --max-majors 1 --out-dir ./out

# full corpus (slow: clones + 23 checks per ref)
./bin/opr-source-risk-corpus scan --max-majors 3 --out-dir ./out

./bin/opr-source-risk-corpus list
./bin/opr-source-risk-corpus report --out-dir ./out
```

Defaults: 3 majors per repo, 600s timeout per scan. Kernel-sized trees
are not in the list on purpose.

## Local OPR (CVE sidecar + risk sidecar)

Needs a checkout of `omarchy-pkgs` next to this repo (or `OMARCHY_PKGS`).
Builds a synthetic `edge/x86_64` db for the packages in `demo-packages.yaml`,
runs `fetch-advisories` + `sync-advisories --no-sign`, scans each git ref,
writes `omarchy.advisories.json` and `omarchy.risk.json` side by side.

```bash
./bin/opr-source-risk-corpus demo-opr --limit 1 --max-majors 1 --repo-root ./local-opr
ls local-opr/edge/x86_64/
```

## Tests

```bash
python3 tests/test_milestones.py
python3 tests/test_report.py
```
