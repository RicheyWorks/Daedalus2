# SPDX-License-Identifier: MIT
"""Island production receiving-adapter contract (R22 job 2). PROPOSED by hephaestus 2026-10-27;
R27-ALIGNED revision by unreal-team (Claude) 2026-10-29 from unreal-epic-boss's answers to the 8 OPEN items
(PR #906 comment, Oct 29) and Richey's custodian decision (hub 57016, Oct 29 11:17 AM PT).

Two shapes are supported, both read-only, both refusing anything uncertain:

  * MOCK (unchanged from hephaestus): the offline boundary in Codex `island-continuation-source`
    (island_policy.build_request / check_guard, island_checkpoint.validate_mock_receipt and the injected
    `guard` / `receipt` mocks in test_island_continuation.py).
  * NATIVE (new): R27's existing production receiver, `task-2/producer-full-queue-r27-speed/native_receiver.py`.
    Per Boss ("no new framework"), the native result IS R27's `batch-complete.json` receipt exactly as
    `native_receiver.validate_result` (lines 375-398) checks it. The adapter maps it; it never produces it.

Nothing here does I/O, loads a provider, touches the editor, the broker, leases or packages. Every proof that
needs the live editor (pin re-hash, live reads, custodian receipt) is INJECTED as data by the custodian and
checked here. `ProposedNativeAdapter` still raises: execution stays with the custodian.
"""
import copy
import hashlib
import json
from typing import Any, Dict, List, Protocol, TypedDict

CONTRACT_STATUS = "R27-aligned-for-custodian-adoption"
REQUEST_SCHEMA = "island-receiving-invocation/v1"      # island_policy.build_request
PREFLIGHT_SCHEMA = "island-mock-preflight/v1"          # test mock `guard`, checked by island_policy.check_guard
RESULT_SCHEMA = "island-mock-result/v1"                # test mock `receipt`, checked by validate_mock_receipt
NATIVE_RESULT_SCHEMA = "r27-batch-complete/v1"         # adapter label for R27 batch-complete.json (receiver 375-398)
TOTAL_KEYS = ("imported", "saved", "admitted", "held", "failed", "reused")
RECIPE_CHECK_KEYS = ("geometry_matches", "material_mapping_matches", "source_factor_bindings_match",
                     "vertex_colour_sample_matches", "validation_reported_valid")
PRESERVATION_KEYS = ("source", "world", "actors", "camera", "selection")
ITEM_KEYS = ("seed", "source_id", "source", "sidecar", "destination")
IDENTITY_KEYS = ("session_id", "invocation_id", "seed", "request_sha256")

# Richey, Oct 29 11:17 AM PT (hub 57016/57017): the sole runtime custodian is codex-play-guard (R27).
# unreal-epic-boss handed over and is hands-off. Only this owner may hold/renew the `unreal` and `compute` leases.
RUNTIME_CUSTODIAN = "codex-play-guard"
LEASE_NAMES = ("unreal", "compute")

# Boss editor-time floors (PR #906 comment; R27 stopped on them Oct 29 10:36 AM PT). Bytes.
EDITOR_FLOORS = {
    "available_physical_bytes": 1_740_000_000,        # 1.74 GB physical
    "available_commit_bytes": 2_250_000_000,          # 2.25 GB commit
    "source_gallery_bytes": 3 * 1024 ** 3,            # 3 GiB source/gallery
    "free_disk_bytes": 25 * 1024 ** 3,                # 25 GiB disk
}
FORBIDDEN_EDITOR_FLAGS = ("-unattended", "-AutoDeclinePackageRecovery")
FORBIDDEN_RECIPE_IMPORTS = ("continue_native_islands_24h_20261023",)
PROTECTED_SHOWCASE_SUFFIX = ".L_Daedalus_MorningReview"   # HOW-WE-USE-UNREAL:26; receiver AST port 88-94 replaces it

# How each of hephaestus's OPEN items was closed (Boss, PR #906 comment, Oct 29). Kept for audit; not a gate.
RESOLVED = {
    "OPEN-native-schema": "R27 batch-complete.json receipt as checked by native_receiver.validate_result (375-398). "
                          "native_admission is per item and only true when the custodian's receipt shows "
                          "validation.status=='Valid', accepted and native_invoked all true. The adapter never sets it.",
    "OPEN-preservation-source": "Re-hash the pins and refuse on any change; legacy `clean` alone is not enough. "
                                "R27 also requires all(action.preservation.values()) (receiver 169, 379, 305-312).",
    "OPEN-pending": "Proved from the receipt: bridge_after all false, native_import_active false, dirty empty, "
                    "failed==0, counts close (receiver 379-386), plus one custodian live read before and after "
                    "(no PIE, sequence or dirty state; HOW-WE-USE:155).",
    "OPEN-known-terminal": "Required: result.known_terminal must be true (receiver 169, 379).",
    "OPEN-identity": "session_id, invocation_id and request_sha256 are bound in the adapter's own sealed receipt with "
                     "the pinned result hash. Recipe bodies are not edited to echo them (receiver ~70).",
    "OPEN-destination": "Proved before invoking: source is the pinned queue's island_by_seed[seed].source_path "
                        "(receiver 356), not the legacy source_for/HDNative constant; every returned package sits under "
                        "planned_destination_folder or is held (receiver 208, 221).",
    "OPEN-world": "Not the same. expected_world must be native_world(world) (receiver 62-63); the MorningReview "
                  "showcase is protected (HOW-WE-USE:26).",
    "OPEN-leases": "Only the sole runtime custodian claims/renews both leases; the adapter never claims, unlocks or "
                   "saves outside its owned folder; close_saved_batch retains leases (receiver 164, 181, 324-327). "
                   "Custodian today: codex-play-guard (Richey, Oct 29 11:17 AM PT).",
}
OPEN = {}   # nothing open after Boss's answers + Richey's custodian decision


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

# R27 batch-complete.json: keys native_receiver.validate_result / close_saved_batch actually read.
R27_RECEIPT_KEYS = frozenset(("utc", "result", "saved_files"))
R27_RESULT_KEYS = frozenset(("known_terminal", "bridge_after", "action"))
R27_ACTION_KEYS = frozenset(("prepared", "imported", "saved", "admitted", "held", "reused", "failed", "items",
                             "preservation", "native_import_active", "dirty"))
R27_COUNT_KEYS = ("prepared", "imported", "saved", "admitted", "held", "reused", "failed")
R27_BRIDGE_IDLE = {"queue": 0, "remote_locked": False, "other_running": [], "unfinished_async": []}
CLEAN_DIRTY = {"maps": [], "content": []}

# One custodian live read (HOW-WE-USE:155), taken before and after the native call. Exact keys; nothing else.
LIVE_READ_KEYS = frozenset(("observed_utc", "pid", "play", "sequence_open", "dirty", "native_import_active", "bridge"))


class ContractError(ValueError):
    pass


class ReceivingAdapter(Protocol):
    """The two injected callables simulate_step already accepts: guard_provider and invocation_provider."""

    def preflight(self, request: InvocationRequest) -> Dict[str, Any]: ...

    def invoke(self, request: InvocationRequest) -> Dict[str, Any]: ...


class ProposedNativeAdapter:
    """Typed stub only. The custodian (codex-play-guard, R27) owns every native call; nothing here has side effects."""

    status = CONTRACT_STATUS

    def preflight(self, request):
        raise NotImplementedError("contract only: native preflight is custodian-owned (RUNTIME_CUSTODIAN)")

    def invoke(self, request):
        raise NotImplementedError("contract only: native invocation is custodian-owned (RUNTIME_CUSTODIAN)")


def canonical_sha256(obj):
    """Same canonical encoding as island_checkpoint.encoded + digest."""
    data = (json.dumps(obj, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode()
    return hashlib.sha256(data).hexdigest()


def request_sha256(request):
    return canonical_sha256(request)


def native_world(world):
    """Identical to native_receiver.native_world (receiver 62-63): '/Game/X/Y' -> '/Game/X/Y.Y'."""
    return world + "." + world.rsplit("/", 1)[-1]


def validate_request(request):
    if not isinstance(request, dict) or set(request) != REQUEST_KEYS or request.get("schema") != REQUEST_SCHEMA:
        raise ContractError("request is not island-receiving-invocation/v1")
    if (request["receiving_adapter_required"] is not True or request["legacy_run_seed_is_directly_safe"] is not False or
            request["automatic_restart"] is not False or request["automatic_lease_mutation"] is not False):
        raise ContractError("request safety flags differ")
    if request["native_admission"] is not False:
        raise ContractError("the request never carries native admission; only the custodian receipt proves it")
    if request["execution_mode"] not in ("mock", "native"):
        raise ContractError("execution_mode must be mock or native")
    item = request["item"]
    if not isinstance(item, dict) or set(item) != set(ITEM_KEYS) or item["seed"] != request["seed"]:
        raise ContractError("item binding differs from request seed")
    if request["invocation_id"] != "%s:%s" % (request["session_id"], request["generation"]):
        raise ContractError("invocation_id is not session_id:generation")
    if request["execution_mode"] == "native":
        if request["receiving_owner"] != RUNTIME_CUSTODIAN:
            raise ContractError("native receiving_owner must be the sole runtime custodian: " + RUNTIME_CUSTODIAN)
        if request["expected_world"].endswith(PROTECTED_SHOWCASE_SUFFIX):
            raise ContractError("expected_world is the protected MorningReview showcase (OPEN-world)")
        if "." not in request["expected_world"].rsplit("/", 1)[-1]:
            raise ContractError("native expected_world must be the admitted world object, native_world(world)")
        for pin in request["recipe_pins"]:
            stem = str(pin.get("path", "")).replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0]
            if stem in FORBIDDEN_RECIPE_IMPORTS:
                raise ContractError("forbidden recipe pin: " + stem)
    return request


def validate_preflight_shape(request, snapshot):
    """Shape and binding only. Timing, window, resource floors and BossActionRequired stay in island_policy.check_guard."""
    if not isinstance(snapshot, dict) or set(snapshot) != PREFLIGHT_KEYS or snapshot.get("schema") != PREFLIGHT_SCHEMA:
        raise ContractError("preflight is not the island-mock-preflight/v1 shape")
    if snapshot["native_admission"] is not False:
        raise ContractError("preflight must not claim native admission")
    if snapshot["execution_mode"] != request["execution_mode"]:
        raise ContractError("preflight execution_mode differs from request")
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


def check_editor_floors(snapshot):
    """Boss floors for any native island run (OPEN-leases answer). Serial editor, both leases, floors, clean boundary."""
    res = snapshot.get("resources") or {}
    for key in ("available_physical_bytes", "available_commit_bytes", "free_disk_bytes"):
        if type(res.get(key)) is not int or res[key] < EDITOR_FLOORS[key]:
            raise ContractError("editor floor not met: " + key)
    if "source_gallery_bytes" in res and res["source_gallery_bytes"] < EDITOR_FLOORS["source_gallery_bytes"]:
        raise ContractError("editor floor not met: source_gallery_bytes")
    if (snapshot.get("single_writer") is not True or snapshot.get("editor_idle") is not True or snapshot.get("other_producers")
            or snapshot.get("play") is not False or snapshot.get("sequence_open") is not False
            or snapshot.get("native_import_active") is not False or snapshot.get("dirty") != CLEAN_DIRTY
            or snapshot.get("bridge") != R27_BRIDGE_IDLE or snapshot.get("stop_requested") is not False):
        raise ContractError("not a clean saved boundary with a single idle writer")
    holders = snapshot.get("lease_holders") or {}
    if any(holders.get(name) != RUNTIME_CUSTODIAN for name in LEASE_NAMES):
        raise ContractError("both leases must be held by the custodian: " + RUNTIME_CUSTODIAN)
    return snapshot


def validate_result(request, result):
    """Mirror of island_checkpoint.validate_mock_receipt for one whole island (mock mode)."""
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

    Kept from the PROPOSED revision for the offline boundary. For the native path use `map_r27_receipt`.
    Only fields the legacy recipe actually reports are filled; the rest are left out so `validate_result` refuses.
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
    if action["dirty"] != CLEAN_DIRTY or action["native_import_active"] is not False:
        raise ContractError("legacy island not saved clean/idle")
    if report.get("destination", request["item"]["destination"]) != request["item"]["destination"]:
        raise ContractError("legacy destination differs from request item (OPEN-destination)")
    src = report.get("source") or {}
    if src.get("sha256") != request["item"]["source"]["sha256"]:
        raise ContractError("legacy source pin differs from request item")
    return copy.deepcopy(candidate), sorted(set(open_ids))


# ----------------------------------------------------------------------------------------------------------
# NATIVE path: R27 receiver alignment (Boss answers 1-8)
# ----------------------------------------------------------------------------------------------------------

def _is_pin(row):
    return isinstance(row, dict) and isinstance(row.get("path"), str) and isinstance(row.get("sha256"), str) \
        and len(row["sha256"]) == 64


def _norm(path):
    return str(path).replace("\\", "/")


def prove_destination(request, queue_entry):
    """Answer 6. Before invoking: the request source must be the pinned queue's island_by_seed[seed].source_path
    (receiver 356) with the same sha256, and item.destination must be that entry's planned_destination_folder.
    Never the legacy source_for()/HDNative constant."""
    if not isinstance(queue_entry, dict):
        raise ContractError("queue entry missing for seed")
    if queue_entry.get("seed") != request["seed"]:
        raise ContractError("queue entry seed differs from request")
    src = request["item"]["source"]
    if _norm(queue_entry.get("source_path", "")) != _norm(src["path"]):
        raise ContractError("source path is not the pinned queue island_by_seed[seed].source_path (OPEN-destination)")
    if queue_entry.get("source_sha256") != src["sha256"]:
        raise ContractError("queue source sha256 differs from request item")
    dest = request["item"]["destination"]
    if queue_entry.get("planned_destination_folder") != dest or not dest.startswith("/Game/") or dest.endswith("/"):
        raise ContractError("item.destination is not the queue's planned_destination_folder")
    return queue_entry


def verify_rehash(request, rehash):
    """Answer 2. `rehash` is {path: sha256} the custodian computed from disk right now. Every pin in the request
    (item.source, item.sidecar, protected_manifest, each recipe pin) must re-hash identically. Refuse on any change
    or any pin not re-hashed. Returns the list of proven paths."""
    if not isinstance(rehash, dict):
        raise ContractError("rehash must map path -> sha256")
    norm = {_norm(k): v for k, v in rehash.items()}
    pins = [request["item"]["source"], request["item"]["sidecar"], request["protected_manifest"]] + list(request["recipe_pins"])
    proven = []
    for pin in pins:
        if not _is_pin(pin):
            raise ContractError("malformed pin in request")
        got = norm.get(_norm(pin["path"]))
        if got is None:
            raise ContractError("pin not re-hashed: " + pin["path"])
        if got != pin["sha256"]:
            raise ContractError("pin changed since request: " + pin["path"])
        proven.append(_norm(pin["path"]))
    return proven


def validate_live_read(read, editor_pid):
    """Answer 3. One custodian live read (HOW-WE-USE:155): no PIE, no sequence, no dirty state, idle bridge, same editor."""
    if not isinstance(read, dict) or set(read) != LIVE_READ_KEYS:
        raise ContractError("live read key set differs")
    if (read["pid"] != editor_pid or read["play"] is not False or read["sequence_open"] is not False
            or read["native_import_active"] is not False or read["dirty"] != CLEAN_DIRTY or read["bridge"] != R27_BRIDGE_IDLE):
        raise ContractError("live read is not a clean idle editor on the admitted pid")
    return read


def validate_r27_receipt(receipt, expected_count=1):
    """Answers 1, 3, 4. Exactly native_receiver.validate_result (375-398) plus the close_saved_batch gate (169-171),
    applied to a parsed batch-complete.json. Raises ContractError with the receiver's own reasons."""
    if not isinstance(receipt, dict) or not R27_RECEIPT_KEYS <= set(receipt):
        raise ContractError("not an R27 batch-complete.json receipt")
    result = receipt["result"]
    if not isinstance(result, dict) or not R27_RESULT_KEYS <= set(result):
        raise ContractError("receipt result lacks known_terminal/bridge_after/action")
    a = result["action"]
    if not isinstance(a, dict) or not R27_ACTION_KEYS <= set(a):
        raise ContractError("receipt action lacks R27 keys")
    if not isinstance(result["bridge_after"], dict) or set(result["bridge_after"]) != set(R27_BRIDGE_IDLE):
        raise ContractError("bridge_after shape differs")
    if (result.get("known_terminal") is not True or any(result["bridge_after"].values()) or a["native_import_active"]
            or not isinstance(a["preservation"], dict) or not a["preservation"]
            or not all(v is True for v in a["preservation"].values())
            or a.get("failed") != 0 or a.get("prepared") != expected_count):
        raise ContractError("Incomplete/uncertain native queue item")
    if any(type(a[k]) is not int or a[k] < 0 for k in R27_COUNT_KEYS):
        raise ContractError("Invalid native count types")
    if a["saved"] != a["imported"] or a["admitted"] + a["held"] + a["reused"] != expected_count:
        raise ContractError("Queue acceptance counts do not close")
    if a.get("dirty") != CLEAN_DIRTY:
        raise ContractError("Dirty native queue closeout")
    if not isinstance(receipt["saved_files"], list) or not all(_is_pin(row) for row in receipt["saved_files"]):
        raise ContractError("saved_files rows are not pins")
    reports = a.get("items", [])
    if not isinstance(reports, list) or len(reports) != a["imported"] \
            or sum(x.get("admitted") is True for x in reports if isinstance(x, dict)) != a["admitted"]:
        raise ContractError("Native item-level admission differs from totals")
    for row in reports:
        if not isinstance(row, dict):
            raise ContractError("malformed item report")
        if row.get("admitted") and (row.get("validation", {}).get("status") != "Valid"
                                    or row["validation"].get("accepted") is not True
                                    or row["validation"].get("native_invoked") is not True):
            raise ContractError("Native Valid evidence required")
    return receipt


def _package_folder(asset_path):
    # '/Game/A/B/Mesh.Mesh' -> '/Game/A/B'
    return asset_path.rsplit("/", 1)[0]


def map_r27_receipt(request, receipt, rehash, live_before, live_after, editor_pid):
    """Answers 1-7 together. Map the custodian's R27 receipt onto a NATIVE boundary result for one whole island.

    Returns (candidate, sealed). `candidate` is refused by validate_native_result on any doubt. `native_admission`
    is copied from the custodian's per-item validation evidence, never asserted here. The adapter's own sealed
    receipt binds identity to the pinned result hash (answer 5) instead of editing recipe bodies.
    """
    if request["execution_mode"] != "native":
        raise ContractError("map_r27_receipt is for native requests")
    validate_r27_receipt(receipt, expected_count=1)
    validate_live_read(live_before, editor_pid)
    validate_live_read(live_after, editor_pid)
    if live_after["observed_utc"] <= live_before["observed_utc"]:
        raise ContractError("live reads are not ordered before/after")
    if receipt["result"].get("pid", editor_pid) != editor_pid:
        raise ContractError("receipt editor pid differs from admitted editor")
    proven_pins = verify_rehash(request, rehash)
    a = receipt["result"]["action"]
    report = a["items"][0] if a["items"] else None
    held = a["admitted"] == 0 and a["held"] == 1
    if report is None and not held:
        raise ContractError("no item report for an admitted island")
    dest = request["item"]["destination"]
    if report is not None:
        src = report.get("source") or {}
        if src.get("sha256") != request["item"]["source"]["sha256"] or _norm(src.get("path", "")) != _norm(request["item"]["source"]["path"]):
            raise ContractError("receipt item source pin differs from request item")
        asset = report.get("asset")
        if report.get("admitted") is True:
            if not isinstance(asset, str) or not asset.startswith(dest + "/"):
                raise ContractError("returned package is outside planned_destination_folder (receiver 208, 221)")
            for extra in (report.get("outputs") or {}).get("paths", []) if isinstance(report.get("outputs"), dict) else []:
                if not str(extra).startswith(dest + "/"):
                    raise ContractError("returned package is outside planned_destination_folder: " + str(extra))
    expected_prefix = _norm(dest.replace("/Game/", "", 1))
    for row in receipt["saved_files"]:
        if expected_prefix not in _norm(row["path"]):
            raise ContractError("saved file outside owned destination: " + row["path"])
    validation = (report or {}).get("validation") or {}
    native_admission = (a["admitted"] == 1 and validation.get("status") == "Valid"
                        and validation.get("accepted") is True and validation.get("native_invoked") is True)
    candidate = {k: a[k] for k in TOTAL_KEYS}
    candidate.update(
        schema=NATIVE_RESULT_SCHEMA, simulated=False, native_admission=native_admission, known_terminal=True,
        pending_native_operations=False,   # proven above from bridge_after/native_import_active/dirty/failed/counts
        session_id=request["session_id"], invocation_id=request["invocation_id"], seed=request["seed"],
        request_sha256=request_sha256(request),
        recipe_checks={
            "geometry_matches": (report or {}).get("geometry_matches") is True,
            "material_mapping_matches": (report or {}).get("material_mapping_matches") is True,
            "source_factor_bindings_match": (report or {}).get("source_factor_bindings_match") is True,
            "vertex_colour_sample_matches": (report or {}).get("vertex_colour_sample_matches") is True,
            "validation_reported_valid": bool(native_admission)},
        preservation={"source": True, **{k: a["preservation"].get(k) is True for k in PRESERVATION_KEYS if k != "source"}},
    )
    sealed = {
        "schema": "island-adapter-sealed-receipt/v1",
        "session_id": request["session_id"], "invocation_id": request["invocation_id"], "seed": request["seed"],
        "request_sha256": candidate["request_sha256"], "result_sha256": canonical_sha256(receipt),
        "custodian": RUNTIME_CUSTODIAN, "editor_pid": editor_pid,
        "live_before_utc": live_before["observed_utc"], "live_after_utc": live_after["observed_utc"],
        "rehashed_pins": proven_pins, "native_admission": native_admission, "held": held,
    }
    return copy.deepcopy(candidate), sealed


def validate_native_result(request, result, sealed):
    """NATIVE counterpart of validate_result. Same key set as the mock result; different fixed values."""
    if not isinstance(result, dict) or set(result) != RESULT_KEYS:
        raise ContractError("native result key set differs from the boundary result")
    want = dict((k, request[k]) for k in ("session_id", "invocation_id", "seed"))
    want["request_sha256"] = request_sha256(request)
    for key in IDENTITY_KEYS:
        if result[key] != want[key] or sealed.get(key) != want[key]:
            raise ContractError("native result identity differs: " + key)
    if sealed.get("schema") != "island-adapter-sealed-receipt/v1" or sealed.get("custodian") != RUNTIME_CUSTODIAN \
            or not isinstance(sealed.get("result_sha256"), str) or len(sealed["result_sha256"]) != 64:
        raise ContractError("sealed receipt is not bound to the custodian and the pinned result")
    if (result["schema"] != NATIVE_RESULT_SCHEMA or result["simulated"] is not False
            or result["known_terminal"] is not True or result["pending_native_operations"] is not False):
        raise ContractError("unknown/uncertain native terminal; preserve intent, no replay")
    if result["native_admission"] is not True:
        raise ContractError("island not natively admitted by the custodian receipt (held or invalid)")
    for key in TOTAL_KEYS:
        if type(result[key]) is not int or result[key] != (1 if key in ("imported", "saved", "admitted") else 0):
            raise ContractError("partial or held island: " + key)
    checks, keep = result["recipe_checks"], result["preservation"]
    if not isinstance(checks, dict) or any(checks.get(k) is not True for k in RECIPE_CHECK_KEYS):
        raise ContractError("recipe checks incomplete")
    if not isinstance(keep, dict) or set(keep) != set(PRESERVATION_KEYS) or any(v is not True for v in keep.values()):
        raise ContractError("preservation checks incomplete")
    return result
