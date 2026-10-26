#!/usr/bin/env python3
"""secret_scan: refuse to push anything that could leak credentials.

Scans files (default: every file changed on the current branch versus a base
ref, plus untracked files git would add) for:
  * forbidden names: .env*, *.key, *.pem, *.pfx, *.p12, id_rsa*, relay-webhook*.json
  * forbidden build/cache dirs: Saved/, Intermediate/, Binaries/, DerivedDataCache/
  * content patterns: private key blocks, bearer tokens, crsr_/ghp_/github_pat_/xox*/AKIA/sk- style keys,
    Slack/Discord/generic webhook URLs, "key|token|secret|password": "<long value>" assignments,
    absolute user paths next to credential words.
Findings print as PATH:LINE RULE only. The matched value is never printed.
Exit 0 clean, 1 findings, 2 error. Standard library only.

Use a real scanner too when one is installed (gitleaks, detect-secrets); this is the floor, not the ceiling.
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from typing import Iterable, List, Optional, Tuple

FORBIDDEN_NAMES = (".env", ".env.*", "*.key", "*.pem", "*.pfx", "*.p12", "id_rsa*", "id_ed25519*",
                   "relay-webhook*.json", "*.kdbx", "credentials.json", "token.json")
FORBIDDEN_DIRS = ("Saved", "Intermediate", "Binaries", "DerivedDataCache")
ALLOW_NAMES = (".env.example", "*.example.json")

RULES: List[Tuple[str, "re.Pattern[str]"]] = [
    ("private-key-block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("cursor-key", re.compile(r"\bcrsr_[A-Za-z0-9]{20,}")),
    ("github-token", re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("openai-style-key", re.compile(r"\bsk-[A-Za-z0-9_-]{32,}")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("bearer-literal", re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}")),
    ("webhook-url", re.compile(r"https://(hooks\.slack\.com/services|discord(?:app)?\.com/api/webhooks)/\S+"
                               r"|https?://\S*/(webhook|webhooks|hooks)/[A-Za-z0-9_-]{16,}")),
    ("secret-assignment", re.compile(
        r"""(?i)["']?(api[_-]?key|secret|token|password|passwd|auth[_-]?key|private[_-]?key)["']?\s*[:=]\s*["'][^"'\s$<{]{16,}["']""")),
    ("user-path-credential", re.compile(
        r"(?i)[A-Z]:[\\/]+Users[\\/]+[^\\/\s]+[\\/][^\s\"']*(token|secret|credential|\.pem|\.key|relay-webhook|\.env)")),
]


def _is_forbidden_path(rel: str) -> Optional[str]:
    parts = rel.replace("\\", "/").split("/")
    name = parts[-1]
    if any(fnmatch.fnmatch(name, a) for a in ALLOW_NAMES):
        return None
    for d in parts[:-1]:
        if d in FORBIDDEN_DIRS:
            return f"forbidden-dir:{d}"
    for pat in FORBIDDEN_NAMES:
        if fnmatch.fnmatch(name, pat):
            return f"forbidden-name:{pat}"
    return None


def scan_file(root: str, rel: str) -> List[Tuple[str, int, str]]:
    findings: List[Tuple[str, int, str]] = []
    why = _is_forbidden_path(rel)
    if why:
        findings.append((rel, 0, why))
    full = os.path.join(root, rel)
    try:
        with open(full, "rb") as fh:
            data = fh.read(8 * 1024 * 1024)
    except OSError:
        return findings
    if b"\x00" in data[:4096]:
        return findings  # binary; name rules above still apply
    text = data.decode("utf-8", errors="replace")
    for i, line in enumerate(text.splitlines(), 1):
        for rule, rx in RULES:
            if rx.search(line):
                findings.append((rel, i, rule))
    return findings


def scan_paths(root: str, rels: Iterable[str]) -> List[Tuple[str, int, str]]:
    out: List[Tuple[str, int, str]] = []
    for rel in sorted(set(rels)):
        if os.path.isfile(os.path.join(root, rel)):
            out.extend(scan_file(root, rel))
    return out


def git_candidate_files(root: str, base: str) -> List[str]:
    def run(*args: str) -> List[str]:
        r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, check=True)
        return [l for l in r.stdout.splitlines() if l.strip()]
    files = set(run("diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"))
    files |= set(run("diff", "--name-only", "--diff-filter=ACMR", "HEAD"))
    files |= set(run("diff", "--name-only", "--cached", "--diff-filter=ACMR"))
    files |= set(run("ls-files", "--others", "--exclude-standard"))
    return sorted(files)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Path-only secret scan before a push.")
    p.add_argument("--root", default=".", help="repo or folder root")
    p.add_argument("--base", default="origin/main", help="git base ref for changed-file mode")
    p.add_argument("--all", action="store_true", help="scan every file under --root instead of git changes")
    p.add_argument("paths", nargs="*", help="explicit relative paths to scan")
    a = p.parse_args(argv)
    root = os.path.abspath(a.root)
    try:
        if a.paths:
            rels = a.paths
        elif a.all:
            rels = []
            for dp, dn, fn in os.walk(root):
                dn[:] = [d for d in dn if d != ".git"]
                rels += [os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/") for f in fn]
        else:
            rels = git_candidate_files(root, a.base)
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"secret_scan: {e}", file=sys.stderr)
        return 2
    findings = scan_paths(root, rels)
    for rel, line, rule in findings:
        print(f"{rel}:{line} {rule}")
    print(f"secret_scan: files={len(set(rels))} findings={len(findings)}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
