# SPDX-License-Identifier: MIT
"""Execution-packet adapter over Codex Slate Inspector read-only result contract.

Consumes caller-supplied decoded FString returns plus an explicit approved_ref
through tools.unreal_mcp.slate_inspector_results only. Builds a versioned,
plan-only execution packet for later native operator use.

Never opens Unreal Editor, never calls MCP/sockets/native code, never executes
Observe/Unobserve/Snapshot/Windows, never invents a panel ref as asset identity,
and never competes with codex-play-guard as the sole Unreal writer.

Pinned contract commit: acf9ab7ae5186d2dd20b69f369460129053ddae5
Metaverse purpose (48162): bounded inspection of ONE operator-approved
asset/outliner/details panel to help verify ingestion/selection.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from tools.unreal_mcp import slate_inspector_results as results
from tools.unreal_mcp.slate_inspector_results import ContractViolation

PACKET_KIND = "slate_inspector_execution_packet"
PACKET_VERSION = 1
SOURCE_COMMIT = "acf9ab7ae5186d2dd20b69f369460129053ddae5"
DEFAULT_PURPOSE = "metaverse_panel_inspection"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_execution_packet(
    *,
    approved_ref: str,
    max_depth: int = 30,
    purpose: str = DEFAULT_PURPOSE,
    windows_return: Optional[str] = None,
    observers_return: Optional[str] = None,
    snapshot_return: Optional[str] = None,
    snapshot_ref: Optional[str] = None,
    snapshot_max_depth: Optional[int] = None,
    include_source_locations: bool = False,
    observers_before: Optional[str] = None,
    observers_after: Optional[str] = None,
    observe_return_value: Optional[str] = None,
    caller_owns_observer: bool = False,
) -> dict:
    """Build a plan-only execution packet from caller-supplied decoded returns.

    Validates every supplied slice through slate_inspector_results. Requires at
    least one of: windows_return, observers_return, snapshot_return, or the
    cleanup trio (observers_before + observers_after + observe_return_value).
    Snapshot path requires snapshot_ref matching approved_ref (defaults to it).

    Raises ContractViolation on invalid inputs (from this adapter or the
    underlying contract). Never executes native Unobserve/Snapshot/Windows/Observe.
    """
    has_windows = windows_return is not None
    has_observers = observers_return is not None
    has_snapshot = snapshot_return is not None
    cleanup_parts = (observers_before, observers_after, observe_return_value)
    has_cleanup = any(part is not None for part in cleanup_parts)

    if not (has_windows or has_observers or has_snapshot or has_cleanup):
        raise ContractViolation(
            "at least one of windows/observers/snapshot/cleanup trio required"
        )

    if has_cleanup and any(part is None for part in cleanup_parts):
        raise ContractViolation(
            "cleanup trio requires observers_before, observers_after, "
            "and observe_return_value"
        )

    if type(purpose) is not str or not purpose.strip():
        raise ContractViolation("nonempty purpose string required")

    # PanelResults validates approved_ref (explicit/nonempty) and depth <= 64.
    panel = results.PanelResults(approved_ref, max_depth)

    steps: list = []
    content_hashes: dict = {}

    if has_windows:
        windows = results.read_windows(windows_return, action="list")
        steps.append({
            "step": "windows_list",
            "tool": "Windows",
            "action": "list",
            "row_count": len(windows),
            "note": "index/title only; NOT panel identity",
        })
        content_hashes["windows_return"] = _sha256_text(windows_return)
        content_hashes["windows_rows"] = _sha256_json(windows)

    if has_observers:
        observers = results.read_observers(observers_return)
        steps.append({
            "step": "observers",
            "tool": "ListObservers",
            "row_count": len(observers),
        })
        content_hashes["observers_return"] = _sha256_text(observers_return)
        content_hashes["observers_rows"] = _sha256_json(observers)

    if has_snapshot:
        ref = approved_ref if snapshot_ref is None else snapshot_ref
        depth = max_depth if snapshot_max_depth is None else snapshot_max_depth
        snap = panel.snapshot(
            snapshot_return,
            ref=ref,
            max_depth=depth,
            include_source_locations=include_source_locations,
        )
        steps.append({
            "step": "snapshot",
            "tool": "Snapshot",
            "approved_ref": snap["approved_ref"],
            "requested_depth": snap["requested_depth"],
            "include_source_locations": snap["include_source_locations"],
            "content_sha256": snap["content_sha256"],
            "utf8_bytes": snap["utf8_bytes"],
            "representation": snap["representation"],
            "freshness": snap["freshness"],
            "cache": snap["cache"],
            "panel_binding": snap["panel_binding"],
        })
        content_hashes["snapshot_return"] = snap["content_sha256"]

    if has_cleanup:
        plan = panel.cleanup_plan(
            observers_before,
            observers_after,
            observe_return_value=observe_return_value,
            caller_owns_observer=caller_owns_observer,
        )
        steps.append({
            "step": "cleanup_plan",
            "planned_tool": plan["planned_tool"],
            "identifier": plan["identifier"],
            "approved_ref": plan["approved_ref"],
            "caller_attested_ownership": plan["caller_attested_ownership"],
            "before_sha256": plan["before_sha256"],
            "after_sha256": plan["after_sha256"],
            "plan_only": plan["plan_only"],
            "execution_authorized": plan["execution_authorized"],
            "live_revalidation_required": plan["live_revalidation_required"],
        })
        content_hashes["observers_before"] = plan["before_sha256"]
        content_hashes["observers_after"] = plan["after_sha256"]

    packet = {
        "kind": PACKET_KIND,
        "version": PACKET_VERSION,
        "toolset": results.TOOLSET,
        "approved_ref": panel.approved_ref,
        "max_depth": panel.max_depth,
        "purpose": purpose,
        "source_commit": SOURCE_COMMIT,
        "steps": steps,
        "content_hashes": content_hashes,
        "contract_valid": True,
        "execution_authorized": False,
        "plan_only": True,
        "native_runtime_qualified": False,
        "freshness": "unproven",
        "panel_binding": "qualified_caller_request_only",
        "source_provenance": dict(results.SOURCE_PROVENANCE),
        "never_executes_natively": True,
        "sole_unreal_writer": "codex-play-guard",
    }
    packet["packet_sha256"] = _sha256_json(
        {key: value for key, value in packet.items() if key != "packet_sha256"}
    )
    return packet


class ExecutionPacketBuilder:
    """Reusable builder wrapping build_execution_packet for modular callers."""

    def __init__(
        self,
        *,
        approved_ref: str,
        max_depth: int = 30,
        purpose: str = DEFAULT_PURPOSE,
    ):
        self.approved_ref = approved_ref
        self.max_depth = max_depth
        self.purpose = purpose

    def build(self, **kwargs) -> dict:
        return build_execution_packet(
            approved_ref=self.approved_ref,
            max_depth=self.max_depth,
            purpose=self.purpose,
            **kwargs,
        )
