# SPDX-License-Identifier: MIT
# Adapted from CSRBT tools/evidence.py::compare(), source SHA-256
# f781c90be83039483e90d31737ae55c30667e445743690d5e1f4ada29942f64d.
# That module credits FlowersForever's evidence design; no runtime is imported.
#
# Copyright (c) 2026 Richmond
# Copyright (c) 2026 RicheyWorks
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Compare declared asset identities; no files, imports or original assets change.

Values are full SHA-256 declarations from validated export catalogs. This does
not inspect asset bytes or establish import, placement, collision or gameplay.
Removed means absent from the current catalog, never permission to delete it.
"""
from collections.abc import Mapping


def _validated(catalog):
    if not isinstance(catalog, Mapping):
        raise ValueError("Asset catalog must map IDs to full SHA256 declarations")
    result = {}
    for key, digest in catalog.items():
        if not isinstance(key, str) or not key or key != key.strip():
            raise ValueError("Asset catalog ID must be a nonempty trimmed string")
        if (not isinstance(digest, str) or len(digest) != 64
                or any(c not in '0123456789abcdef' for c in digest)):
            raise ValueError(f"Invalid SHA256 for {key}")
        result[key] = digest
    return result


def _compare(recorded, current):
    """CSRBT's deterministic changed/added/removed comparison."""
    rf = (recorded or {}).get("files") or {}
    cf = (current or {}).get("files") or {}
    return {"changed": sorted(k for k in rf if k in cf and rf[k] != cf[k]),
            "added": sorted(k for k in cf if k not in rf),
            "removed": sorted(k for k in rf if k not in cf)}


def compare_catalogs(previous, current):
    """Return sorted changes over complete, validated digest declarations."""
    before, after = _validated(previous), _validated(current)
    result = _compare({"files": before}, {"files": after})
    result["unchanged"] = sorted(k for k in before if k in after and before[k] == after[k])
    return result
