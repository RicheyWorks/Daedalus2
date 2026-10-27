# SPDX-License-Identifier: MIT
"""Bounded reads of caller-supplied retained evidence; never creates pins."""
import hashlib
import json
import math
import os
import re
import stat
from pathlib import Path


class EvidenceError(ValueError):
    """Evidence is absent, ambiguous, changed or outside the supplied roots."""


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError("duplicate JSON key: " + key)
        result[key] = value
    return result


def decode(raw):
    def reject(value):
        raise EvidenceError("nonfinite JSON number: " + value)
    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise EvidenceError("nonfinite JSON number: " + value)
        return number
    try:
        return json.loads(raw, object_pairs_hook=_pairs, parse_constant=reject, parse_float=finite)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("invalid UTF-8 JSON: " + str(exc)) from exc


def checked_path(path, roots):
    candidate = Path(path)
    allowed = [Path(root) for root in roots]
    if not candidate.is_absolute() or ".." in candidate.parts or any(
            not root.is_absolute() or ".." in root.parts for root in allowed):
        raise EvidenceError("absolute evidence paths without traversal required")
    if not allowed or not any(candidate.is_relative_to(root) for root in allowed):
        raise EvidenceError("path outside explicit evidence roots: " + str(candidate))
    for parent in (candidate, *candidate.parents):
        info = parent.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise EvidenceError("link/reparse evidence path refused: " + str(parent))
    if not candidate.is_file():
        raise EvidenceError("regular evidence file required: " + str(candidate))
    return candidate


def read_pinned(pin, roots, *, json_document=False, limit=32 * 1024 * 1024):
    if not isinstance(pin, dict) or not isinstance(pin.get("path"), str):
        raise EvidenceError("pin requires path, bytes and sha256")
    size, sha = pin.get("bytes"), pin.get("sha256")
    if type(size) is not int or size < 0 or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise EvidenceError("invalid retained pin: " + pin["path"])
    path = checked_path(pin["path"], roots)
    before = path.stat()
    if before.st_size != size or (json_document and size > limit):
        raise EvidenceError("evidence byte count/cap mismatch: " + str(path))
    digest = hashlib.sha256()
    content = bytearray() if json_document else None
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode):
            raise EvidenceError("opened evidence is not a regular file")
        total = 0
        while block := stream.read(1024 * 1024):
            total += len(block)
            if total > size or (json_document and total > limit):
                raise EvidenceError("evidence grew beyond declared byte count/cap")
            digest.update(block)
            if content is not None:
                content.extend(block)
        closed = os.fstat(stream.fileno())
    checked_path(path, roots)
    after = path.stat()
    stamps = [(s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
              for s in (before, opened, closed, after)]
    if len(set(stamps)) != 1 or digest.hexdigest() != sha:
        raise EvidenceError("evidence hash/change mismatch: " + str(path))
    return decode(bytes(content)) if content is not None else None
