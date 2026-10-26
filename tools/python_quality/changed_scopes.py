# SPDX-License-Identifier: MIT
"""Route verified Git name-status records; emit fixed paths, never commands."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCOPES = (("team_handoff", "tools/team_handoff"), ("world_package", "tools/world_package"))
SHARED_PATHS = (
    "tools/python_quality",
    ".github/workflows/python-source-quality.yml",
    ".github/workflows/world-census-static.yml",
    ".github/workflows/team-handoff-offline.yml",
    ".github/workflows/world-package-preflight.yml",
)
MAX_DIFF_BYTES = 1024 * 1024
MAX_MAP_BYTES = 64 * 1024
SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
REASONS = {"manual", "missing_context", "invalid_context", "unavailable_context", "unsupported_event", "invalid_diff", "shared_change", "verified_diff"}


class ScopeError(ValueError):
    """Malformed finite policy or Git status record."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ScopeError(f"duplicate scope-map key: {key}")
        result[key] = value
    return result


def validate_scope_map(data: object) -> dict:
    """Validate the complete finite schema; no additional scopes or commands."""
    if not isinstance(data, dict) or set(data) != {"format", "version", "scopes", "shared_paths"}:
        raise ScopeError("scope map requires exactly format, version, scopes, shared_paths")
    if data["format"] != "daedalus-python-quality-scopes" or type(data["version"]) is not int or data["version"] != 1:
        raise ScopeError("scope map requires daedalus-python-quality-scopes version 1")
    rows = data["scopes"]
    if not isinstance(rows, list) or len(rows) != len(SCOPES):
        raise ScopeError("scope map must contain exactly the two approved modules")
    found = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"scope", "path"}:
            raise ScopeError("each scope requires exactly scope and path")
        if not isinstance(row["scope"], str) or not isinstance(row["path"], str):
            raise ScopeError("scope identifiers and paths must be strings")
        found.append((row["scope"], row["path"]))
    if len(set(found)) != len(SCOPES) or set(found) != set(SCOPES):
        raise ScopeError("scope identifiers and paths must match the fixed allowlist")
    shared = data["shared_paths"]
    if not isinstance(shared, list) or not all(isinstance(path, str) for path in shared):
        raise ScopeError("shared_paths must be an array of strings")
    if len(shared) != len(SHARED_PATHS) or set(shared) != set(SHARED_PATHS):
        raise ScopeError("shared_paths must match the complete approved dependency list")
    return data


def load_scope_map(path: Path) -> dict:
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_MAP_BYTES + 1)
        if len(raw) > MAX_MAP_BYTES:
            raise ScopeError("scope map exceeds its byte limit")
        return validate_scope_map(json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ScopeError(f"cannot read valid scope map: {path}") from exc


def parse_name_status_z(raw: bytes) -> tuple[str, ...]:
    """Parse git diff --name-status -z, including both rename/copy endpoints."""
    if not isinstance(raw, bytes) or len(raw) > MAX_DIFF_BYTES:
        raise ScopeError("invalid or oversized NUL-delimited diff")
    if not raw:
        return ()
    if not raw.endswith(b"\0"):
        raise ScopeError("truncated NUL-delimited diff")
    fields = raw[:-1].split(b"\0")
    paths = []
    index = 0
    while index < len(fields):
        try:
            status = fields[index].decode("ascii")
        except UnicodeError as exc:
            raise ScopeError("invalid Git status") from exc
        index += 1
        if status in {"A", "D", "M", "T"}:
            count = 1
        elif re.fullmatch(r"[RC][0-9]{1,3}", status) and int(status[1:]) <= 100:
            count = 2
        else:
            raise ScopeError("unknown or unmerged Git status")
        if index + count > len(fields):
            raise ScopeError("truncated Git status paths")
        for value in fields[index:index + count]:
            try:
                path = value.decode("utf-8")
            except UnicodeError as exc:
                raise ScopeError("non-UTF-8 Git path") from exc
            if not path or path.startswith("/") or any(part in {"", ".", ".."} for part in path.split("/")):
                raise ScopeError("Git path must be canonical and relative")
            paths.append(path)  # Do not strip, split whitespace, or normalize literal backslashes.
        index += count
    return tuple(paths)


def _under(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def _result(selected: set[str], reason: str) -> dict:
    if reason not in REASONS:
        raise ScopeError("unknown routing reason")
    return {"matrix": {"include": [{"scope": scope, "path": path} for scope, path in SCOPES if scope in selected]},
            "any": bool(selected), "reason": reason}


def select_scopes(raw: bytes | None, policy: dict, context_valid: bool = True, reason: str = "missing_context") -> dict:
    validate_scope_map(policy)
    if type(context_valid) is not bool:
        raise ScopeError("context_valid must be a boolean")
    if raw is None or not context_valid:
        return _result({scope for scope, _ in SCOPES}, reason)
    try:
        paths = parse_name_status_z(raw)
    except ScopeError:
        return _result({scope for scope, _ in SCOPES}, "invalid_diff")
    if any(_under(path, "tools/python_quality") or path in SHARED_PATHS[1:] for path in paths):
        return _result({scope for scope, _ in SCOPES}, "shared_change")
    selected = {scope for scope, root in SCOPES if any(_under(path, root) for path in paths)}
    return _result(selected, "verified_diff")


class _ContextError(Exception):
    pass


def _git(repository: Path, *args: str) -> bytes:
    run = subprocess.run(["git", *args], cwd=repository, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         timeout=15, check=False)
    if run.returncode:
        raise _ContextError()
    return run.stdout


def route_git(policy: dict, repository: Path, event: str, base: str | None, head: str | None, pr_head: str | None = None) -> dict:
    """Compare a verified PR merge snapshot or the complete recorded push range."""
    validate_scope_map(policy)
    if event == "workflow_dispatch":
        return select_scopes(None, policy, reason="manual")
    if event not in {"push", "pull_request"}:
        return select_scopes(None, policy, reason="unsupported_event")
    ids = [base, head] + ([pr_head] if event == "pull_request" else [])
    if not all(isinstance(value, str) and SHA.fullmatch(value) and set(value) != {"0"} for value in ids):
        return select_scopes(None, policy, reason="invalid_context")
    if len({len(value) for value in ids}) != 1:
        return select_scopes(None, policy, reason="invalid_context")
    try:
        if _git(repository, "rev-parse", "--verify", "HEAD").decode("ascii").strip() != head:
            raise _ContextError()
        for value in ids:
            if _git(repository, "cat-file", "-t", value).strip() != b"commit":
                raise _ContextError()
        if event == "pull_request":
            parents = _git(repository, "show", "--no-patch", "--format=%P", head).decode("ascii").split()
            if parents != [base, pr_head]:
                raise _ContextError()
        else:
            _git(repository, "merge-base", "--is-ancestor", base, head)
        raw = _git(repository, "diff", "--name-status", "-z", "--find-renames", "--no-ext-diff", "--no-textconv", base, head, "--")
    except (OSError, subprocess.TimeoutExpired, UnicodeError, _ContextError):
        return select_scopes(None, policy, reason="unavailable_context")
    return select_scopes(raw, policy)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope-map", type=Path, default=Path(__file__).with_name("scopes.json"))
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--event", default="")
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--pr-head")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = route_git(load_scope_map(args.scope_map), args.repository, args.event, args.base, args.head, args.pr_head)
        if args.github_output is not None:
            with args.github_output.open("a", encoding="utf-8", newline="") as stream:
                stream.write("matrix=" + json.dumps(result["matrix"], separators=(",", ":")) + "\n")
                stream.write("any=" + str(result["any"]).lower() + "\nreason=" + result["reason"] + "\n")
    except (ScopeError, OSError) as exc:
        print(f"python-quality: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
