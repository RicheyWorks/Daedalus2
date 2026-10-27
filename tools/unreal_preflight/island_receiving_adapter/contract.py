# SPDX-License-Identifier: MIT
"""PROPOSED island production receiving-adapter contract (R22 job 2, hephaestus). FOR BOSS REVIEW. NOT ADOPTED.

Built ONLY from two existing local shapes, read-only:
  * the offline boundary in Codex `island-continuation-source` (island_policy.build_request / check_guard,
    island_checkpoint.validate_mock_receipt, and the injected `guard` / `receipt` mocks in
    test_island_continuation.py);
  * the proven legacy recipe `focused_native_islands_20261023.run(seed)`: the `value` returned by its
    `AdmitSavedWholeIsland` stage plus its `items[0]` report.

No field below is invented. Where the legacy recipe does not produce a field the boundary needs, the mapper
records it under OPEN and the result is refused. This module has no I/O, no provider loader, no editor, broker
or lease calls, and no production wiring. `ProposedNativeAdapter` deliberately raises.
"""
import copy
import hashlib
import json
from typing import Any, Dict, List, Protocol, TypedDict

CONTRACT_STATUS = "PROPOSED-for-Boss-review"
REQUEST_SCHEMA = "island-receiving-invocation/v1"      # island_policy.build_request
PREFLIGHT_SCHEMA = "island-mock-preflight/v1"          # test mock `guard`, checked by island_policy.check_guard
RESULT_SCHEMA = "island-mock-result/v1"                # test mock `receipt`, checked by validate_mock_receipt
TOTAL_KEYS = ("imported", "saved", "admitted", "held", "failed", "reused")
RECIPE_CHECK_KEYS = ("geometry_matches", "material_mapping_matches", "source_factor_bindings_match",
                     "vertex_colour_sample_matches", "validation_reported_valid")
PRESERVATION_KEYS = ("source", "world", "actors", "camera", "selection")
ITEM_KEYS = ("seed", "source_id", "source", "sidecar", "destination")
IDENTITY_KEYS = ("session_id", "invocation_id", "seed", "request_sha256")

# OPEN questions (also in docs/production/ISLAND-RECEIVING-ADAPTER-CONTRACT-PROPOSED-20261027.md)
OPEN = {
    "OPEN-native-schema": "No native preflight/result schema exists; only island-mock-*/v1 with execution_mode=mock, "
                          "simulated=True, native_admission=False. Boss names the native schema and who may set native_admission.",
    "OPEN-preservation-source": "Legacy preservation has {world, actors, camera, selection, clean}; boundary needs "
                                "{source, world, actors, camera, selection}. Legacy checks source pins in NativeImportWholeIsland "
                                "(raises if changed) but does not report a 'source' flag.",
    "OPEN-pending": "Boundary needs pending_native_operations=False; legacy only exports native_import_active (state.pending is internal).",
    "OPEN-known-terminal": "Boundary needs known_terminal=True; legacy proves it only via a KNOWN_TERMINAL row in "
                           "NativeImportWholeIsland/native-substeps.jsonl, so the caller must supply that observation.",
    "OPEN-identity": "Legacy run(seed) has no session_id/invocation_id/request_sha256; an adapter can only echo the request, "
                     "which is adapter-asserted, not recipe-proven.",
    "OPEN-destination": "Legacy hard-codes destination '/Game/Daedalus/Art/Islands/HDNative20261023/<stem>' and source_for(seed); "
                        "boundary supplies item.destination/source pins. Equality must be proven, not assumed.",
    "OPEN-world": "Legacy works in f.WORLD + '.L_Daedalus_MorningReview'; boundary supplies expected_world.",
    "OPEN-leases": "Legacy calls f.claim() and close_saved_batch (lease/package mutations); boundary forbids automatic lease "
                   "mutation. Which custodian performs them is unassigned.",
}


class Pin(TypedDict, total=False):
    path: str
    sha256: str
    bytes: int


class Item(TypedDict):
    seed: int
    source_id: str
    source: Pin
    sidecar: Pin
    destination: str


class InvocationRequest(TypedDict):
    """Exact key set of island_policy.build_request."""
    schema: str
    session_id: str
    invocation_id: str
    generation: int
    seed: int
    receiving_owner: str
    window: Dict[str, str]
    editor_generation: Dict[str, Any]
    item: Item
    expected_world: str
    protected_manifest: Pin
    recipe_pins: List[Pin]
    receiving_adapter_required: bool
    legacy_run_seed_is_directly_safe: bool
    automatic_restart: bool
    automatic_lease_mutation: bool
    execution_mode: str
    native_admission: bool


REQUEST_KEYS = frozenset(InvocationRequest.__annotations__)

# Exact key set of the injected `guard` mock (island-mock-preflight/v1).
PREFLIGHT_KEYS = frozenset((
    "schema", "execution_mode", "native_admission", "observed_utc", "session_id", "generation", "receiving_owner",
    "lease_holders", "editor_generation", "world", "single_writer", "editor_idle", "other_producers", "dirty", "bridge",
    "play", "native_import_active", "sequence_open", "movie_executor", "stop_requested", "resources",
    "editor_private_bytes", "source_target_binding", "source_target_verified", "protected_manifest_sha256",
    "protected_bytes_verified", "recipe_pins_verified"))

# Exact key set of the injected `receipt` mock (island-mock-result/v1).
RESULT_KEYS = frozenset(TOTAL_KEYS + (
    "schema", "simulated", "native_admission", "known_terminal", "pending_native_operations", "session_id",
    "invocation_id", "seed", "request_sha256", "recipe_checks", "preservation"))

# Keys of the legacy AdmitSavedWholeIsland `value` this contract reads (all present in the recipe).
LEGACY_ACTION_KEYS = frozenset(("prepared", "imported", "saved", "admitted", "held", "reused", "failed",
                                "geometry_matches", "material_mapping_matches", "items", "created_assets",
                                "native_import_active", "preservation", "dirty"))


class ContractError(ValueError):
    pass


class ReceivingAdapter(Protocol):
    """The two injected callables simulate_step already accepts: guard_provider and invocation_provider."""

    def preflight(self, request: InvocationRequest) -> Dict[str, Any]: ...

    def invoke(self, request: InvocationRequest) -> Dict[str, Any]: ...


class ProposedNativeAdapter:
    """Typed stub only. Boss owns any native implementation; nothing here may be bound to live side effects."""

    status = CONTRACT_STATUS

    def preflight(self, request):
        raise NotImplementedError("PROPOSED contract only: native preflight is Boss-owned (see OPEN-native-schema)")

    def invoke(self, request):
        raise NotImplementedError("PROPOSED contract only: native invocation is Boss-owned (see OPEN-native-schema)")


def request_sha256(request):
    """Same canonical encoding as island_checkpoint.encoded + digest."""
    data = (json.dumps(request, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode()
    return hashlib.sha256(data).hexdigest()


def validate_request(request):
    if not isinstance(request, dict) or set(request) != REQUEST_KEYS or request.get("schema") != REQUEST_SCHEMA:
        raise ContractError("request is not island-receiving-invocation/v1")
    if (request["receiving_adapter_required"] is not True or request["legacy_run_seed_is_directly_safe"] is not False or
            request["automatic_restart"] is not False or request["automatic_lease_mutation"] is not False):
        raise ContractError("request safety flags differ")
    if request["native_admission"] is not False or request["execution_mode"] != "mock":
        raise ContractError("only mock execution exists today (OPEN-native-schema)")
    item = request["item"]
    if not isinstance(item, dict) or set(item) != set(ITEM_KEYS) or item["seed"] != request["seed"]:
        raise ContractError("item binding differs from request seed")
    if request["invocation_id"] != "%s:%s" % (request["session_id"], request["generation"]):
        raise ContractError("invocation_id is not session_id:generation")
    return request


def validate_preflight_shape(request, snapshot):
    """Shape and binding only. Timing, window, resource floors and BossActionRequired stay in island_policy.check_guard."""
    if not isinstance(snapshot, dict) or set(snapshot) != PREFLIGHT_KEYS or snapshot.get("schema") != PREFLIGHT_SCHEMA:
        raise ContractError("preflight is not the island-mock-preflight/v1 shape")
    if snapshot["native_admission"] is not False or snapshot["execution_mode"] != "mock":
        raise ContractError("preflight must not claim native admission")
    owner = request["receiving_owner"]
    for key, want in (("session_id", request["session_id"]), ("generation", request["generation"]),
                      ("receiving_owner", owner), ("lease_holders", {"compute": owner, "unreal": owner}),
                      ("editor_generation", request["editor_generation"]), ("world", request["expected_world"]),
                      ("source_target_binding", request["item"]),
                      ("protected_manifest_sha256", request["protected_manifest"]["sha256"]),
                      ("recipe_pins_verified", request["recipe_pins"])):
        if snapshot[key] != want:
            raise ContractError("preflight binding differs: " + key)
    return snapshot


def validate_result(request, result):
    """Mirror of island_checkpoint.validate_mock_receipt for one whole island."""
    if not isinstance(result, dict) or set(result) != RESULT_KEYS:
        raise ContractError("result key set differs from island-mock-result/v1")
    want = dict((k, request[k]) for k in ("session_id", "invocation_id", "seed"))
    want["request_sha256"] = request_sha256(request)
    for key in IDENTITY_KEYS:
        if result[key] != want[key]:
            raise ContractError("result identity differs: " + key)
    if (result["schema"] != RESULT_SCHEMA or result["simulated"] is not True or result["native_admission"] is not False or
            result["known_terminal"] is not True or result["pending_native_operations"] is not False):
        raise ContractError("unknown/uncertain terminal; preserve intent, no replay")
    for key in TOTAL_KEYS:
        if type(result[key]) is not int or result[key] != (1 if key in ("imported", "saved", "admitted") else 0):
            raise ContractError("partial or held island: " + key)
    checks, keep = result["recipe_checks"], result["preservation"]
    if not isinstance(checks, dict) or any(checks.get(k) is not True for k in RECIPE_CHECK_KEYS):
        raise ContractError("recipe checks incomplete")
    if not isinstance(keep, dict) or set(keep) != set(PRESERVATION_KEYS) or any(v is not True for v in keep.values()):
        raise ContractError("preservation checks incomplete")
    return result


def map_legacy_action(request, action, known_terminal_observed):
    """Map a legacy AdmitSavedWholeIsland `value` onto the boundary result. Returns (candidate, open_ids).

    Only fields the legacy recipe actually reports are filled. Missing ones are left out and their OPEN ids are
    returned, so `validate_result(candidate)` refuses until Boss resolves them. Nothing is defaulted to True.
    """
    if not isinstance(action, dict) or not LEGACY_ACTION_KEYS <= set(action):
        raise ContractError("legacy action lacks AdmitSavedWholeIsland keys")
    items = action["items"]
    if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
        raise ContractError("legacy action must report exactly one whole island")
    report = items[0]
    validation = report.get("validation") or {}
    candidate = {k: action[k] for k in TOTAL_KEYS}
    candidate["recipe_checks"] = {
        "geometry_matches": action["geometry_matches"] is True,
        "material_mapping_matches": action["material_mapping_matches"] is True,
        "source_factor_bindings_match": report.get("source_factor_bindings_match") is True,
        "vertex_colour_sample_matches": report.get("vertex_colour_sample_matches") is True,
        # same expression the legacy recipe uses for `admitted`
        "validation_reported_valid": (validation.get("status") == "Valid" and validation.get("native_invoked") is True
                                      and validation.get("accepted") is True)}
    legacy_keep = action["preservation"] if isinstance(action["preservation"], dict) else {}
    candidate["preservation"] = {k: legacy_keep[k] is True for k in PRESERVATION_KEYS if k in legacy_keep}
    open_ids = ["OPEN-native-schema", "OPEN-identity", "OPEN-pending", "OPEN-destination", "OPEN-world", "OPEN-leases"]
    if "source" not in legacy_keep:
        open_ids.append("OPEN-preservation-source")
    if known_terminal_observed is True:
        candidate["known_terminal"] = True
    else:
        open_ids.append("OPEN-known-terminal")
    if action["dirty"] != {"maps": [], "content": []} or action["native_import_active"] is not False:
        raise ContractError("legacy island not saved clean/idle")
    if report.get("destination", request["item"]["destination"]) != request["item"]["destination"]:
        raise ContractError("legacy destination differs from request item (OPEN-destination)")
    src = report.get("source") or {}
    if src.get("sha256") != request["item"]["source"]["sha256"]:
        raise ContractError("legacy source pin differs from request item")
    return copy.deepcopy(candidate), sorted(set(open_ids))