# SPDX-License-Identifier: MIT
"""Shared portable evidence-path decisions; no coercion, normalization or I/O.

Callers retain their own field admission, exceptions and return contracts. The
issue categories also retain the existing diagnostic precedence: path shape,
all normalized components, then portability and device names from left to right.
"""

import re


_PORTABLE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")
_RESERVED = frozenset({"CON", "PRN", "AUX", "NUL"} | {
    prefix + str(number) for prefix in ("COM", "LPT") for number in range(1, 10)
})


def evidence_path_issue(value):
    """Return a decision category, or None for an unchanged portable path."""
    if not isinstance(value, str) or len(value) > 220 or _PORTABLE.fullmatch(value) is None:
        return "shape"
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return "components"
    for part in parts:
        if part.endswith("."):
            return "nonportable_component"
        if part.split(".")[0].upper() in _RESERVED:
            return "reserved_component"
    return None
