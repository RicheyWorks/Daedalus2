# SPDX-License-Identifier: MIT
"""Python consumer for the DataValidation native result snapshot (stdlib only).

Parses the JSON envelope emitted by ``native_validation_result_snapshot.h``
(``daedalus::validation_snapshot::Serialize``), checks it against output caps,
and returns a typed aggregate. Pure data: no endpoint, transport, editor or
runtime call. Pinned to PR #187 branch grok/native-validation-snapshot head
77e2e0e8542d864dd62612a53794ff811bf5accc. That head defines no output caps of
its own yet, so ``OutputCaps`` holds conservative consumer-side defaults; align
them with the producer caps once those land.

Faithful like the producer: impossible values are reported as problems, never
clamped or defaulted to passing. ``native_runtime_qualified`` is always False.

    python tools/unreal_mcp/native_validation_snapshot_consumer.py snapshot.json
"""
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

PINNED_PR187_HEAD = "77e2e0e8542d864dd62612a53794ff811bf5accc"
SNAPSHOT_KIND = "explicit_native_members_not_mcp_schema"
RESULT_NAMES = ("NotValidated", "Invalid", "Valid")
COUNT_KEYS = ("NumRequested", "NumExternalObjects", "NumChecked", "NumValid", "NumInvalid",
              "NumSkipped", "NumWarnings", "NumUnableToValidate")
SETTINGS_BOOL_KEYS = ("bSkipExcludedDirectories", "bShowIfNoFailures", "bCollectPerAssetDetails",
                      "bLoadAssetsForValidation", "bUnloadAssetsLoadedForValidation",
                      "bLoadExternalObjectsForValidation", "bCaptureAssetLoadLogs",
                      "bCaptureLogsDuringValidation", "bCaptureWarningsDuringValidationAsErrors",
                      "bValidateReferencersOfDeletedAssets", "bSilent")
INT32_MAX = 2147483647


class SnapshotError(ValueError):
    """Malformed snapshot: wrong JSON, shape or types."""


@dataclass(frozen=True)
class OutputCaps:
    max_bytes: int = 8 * 1024 * 1024
    max_requested_assets: int = 4096
    max_details: int = 4096
    max_messages_per_list: int = 1024
    max_string_chars: int = 16384
    max_total_messages: int = 65536


@dataclass(frozen=True)
class Message:
    severity: str
    text: str


@dataclass(frozen=True)
class ExternalObject:
    package_name: str
    asset_name: str


@dataclass(frozen=True)
class AssetDetail:
    object_path: str
    package_name: str
    asset_name: str
    result: str
    validation_errors: Tuple[str, ...]
    validation_warnings: Tuple[str, ...]
    validation_messages: Tuple[Message, ...]
    external_objects: Tuple[ExternalObject, ...]


@dataclass(frozen=True)
class SnapshotResults:
    counts: Dict[str, int]
    asset_limit_reached: bool
    details: Tuple[AssetDetail, ...]
    validator_messages: Tuple[Message, ...]


@dataclass(frozen=True)
class SnapshotSettings:
    flags: Dict[str, bool]
    validation_usecase: str
    max_assets_to_validate: int


@dataclass(frozen=True)
class Provenance:
    fresh_out_results: str
    native_invocation: str
    captured_at_utc: str


@dataclass(frozen=True)
class NativeValidationSnapshot:
    requested_assets: Tuple[str, ...]
    native_return: int
    results: SnapshotResults
    settings: SnapshotSettings
    provenance: Provenance
    native_runtime_qualified: bool
    unknowns: Tuple[str, ...]


@dataclass
class ConsumerResult:
    """Typed aggregate. ``accepted`` needs zero cap violations and zero problems."""
    snapshot: NativeValidationSnapshot
    cap_violations: List[str] = field(default_factory=list)
    problems: List[str] = field(default_factory=list)
    pinned_head: str = PINNED_PR187_HEAD

    @property
    def accepted(self):
        return not self.cap_violations and not self.problems

    def to_dict(self):
        s = self.snapshot
        return {"accepted": self.accepted, "pinned_head": self.pinned_head,
                "requested": len(s.requested_assets), "native_return": s.native_return,
                "counts": dict(s.results.counts), "cap_violations": list(self.cap_violations),
                "problems": list(self.problems), "unknowns": list(s.unknowns),
                "native_runtime_qualified": s.native_runtime_qualified}


def _need(cond, msg):
    if not cond:
        raise SnapshotError(msg)


def _obj(v, where):
    _need(isinstance(v, dict), "%s must be an object" % where)
    return v


def _str(v, where):
    _need(isinstance(v, str), "%s must be a string" % where)
    return v


def _int(v, where):
    _need(type(v) is int, "%s must be an integer" % where)  # bool rejected on purpose
    return v


def _bool(v, where):
    _need(type(v) is bool, "%s must be a boolean" % where)
    return v


def _list(v, where):
    _need(isinstance(v, list), "%s must be an array" % where)
    return v


def _messages(v, where):
    out = []
    for i, m in enumerate(_list(v, where)):
        m = _obj(m, "%s[%d]" % (where, i))
        out.append(Message(_str(m.get("Severity"), "%s[%d].Severity" % (where, i)),
                           _str(m.get("Text"), "%s[%d].Text" % (where, i))))
    return tuple(out)


def _strings(v, where):
    return tuple(_str(x, "%s[%d]" % (where, i)) for i, x in enumerate(_list(v, where)))


def _reject_constant(name):
    raise SnapshotError("non-finite number %s" % name)


def parse_snapshot(text):
    """Parse the producer's JSON (str or bytes) into a NativeValidationSnapshot, or raise SnapshotError."""
    if isinstance(text, (bytes, bytearray)):
        try:
            text = bytes(text).decode("utf-8")
        except UnicodeDecodeError as e:
            raise SnapshotError("snapshot is not UTF-8: %s" % e)
    try:
        doc = json.loads(text, parse_constant=_reject_constant)
    except json.JSONDecodeError as e:
        raise SnapshotError("invalid JSON: %s" % e)
    return snapshot_from_dict(doc)


def snapshot_from_dict(doc):
    doc = _obj(doc, "snapshot")
    _need(doc.get("snapshot_kind") == SNAPSHOT_KIND, "unexpected snapshot_kind")
    requested = _strings(doc.get("requested_assets"), "requested_assets")
    native_return = _int(doc.get("native_return"), "native_return")
    r = _obj(doc.get("results"), "results")
    counts = {k: _int(r.get(k), "results.%s" % k) for k in COUNT_KEYS}
    details = []
    for path, d in _obj(r.get("AssetsDetails"), "results.AssetsDetails").items():
        w = "AssetsDetails[%r]" % path
        d = _obj(d, w)
        result = _str(d.get("Result"), w + ".Result")
        _need(result in RESULT_NAMES, "%s.Result unknown: %r" % (w, result))
        exts = []
        for i, e in enumerate(_list(d.get("ExternalObjects"), w + ".ExternalObjects")):
            e = _obj(e, "%s.ExternalObjects[%d]" % (w, i))
            exts.append(ExternalObject(_str(e.get("PackageName"), w + ".ExternalObjects.PackageName"),
                                       _str(e.get("AssetName"), w + ".ExternalObjects.AssetName")))
        details.append(AssetDetail(path, _str(d.get("PackageName"), w + ".PackageName"),
                                   _str(d.get("AssetName"), w + ".AssetName"), result,
                                   _strings(d.get("ValidationErrors"), w + ".ValidationErrors"),
                                   _strings(d.get("ValidationWarnings"), w + ".ValidationWarnings"),
                                   _messages(d.get("ValidationMessages"), w + ".ValidationMessages"),
                                   tuple(exts)))
    results = SnapshotResults(counts, _bool(r.get("bAssetLimitReached"), "results.bAssetLimitReached"),
                              tuple(details), _messages(r.get("ValidatorMessages"), "results.ValidatorMessages"))
    s = _obj(doc.get("settings"), "settings")
    settings = SnapshotSettings({k: _bool(s.get(k), "settings.%s" % k) for k in SETTINGS_BOOL_KEYS},
                                _str(s.get("ValidationUsecase"), "settings.ValidationUsecase"),
                                _int(s.get("MaxAssetsToValidate"), "settings.MaxAssetsToValidate"))
    p = _obj(doc.get("provenance"), "provenance")
    prov = Provenance(_str(p.get("fresh_out_results"), "provenance.fresh_out_results"),
                      _str(p.get("native_invocation"), "provenance.native_invocation"),
                      _str(p.get("captured_at_utc"), "provenance.captured_at_utc"))
    return NativeValidationSnapshot(requested, native_return, results, settings, prov,
                                    _bool(doc.get("native_runtime_qualified"), "native_runtime_qualified"),
                                    _strings(doc.get("unknowns"), "unknowns"))


def _all_strings(snap):
    yield from snap.requested_assets
    for d in snap.results.details:
        yield from (d.object_path, d.package_name, d.asset_name)
        yield from d.validation_errors
        yield from d.validation_warnings
        for m in d.validation_messages:
            yield m.text
        for e in d.external_objects:
            yield from (e.package_name, e.asset_name)
    for m in snap.results.validator_messages:
        yield m.text


def check_caps(snap, caps=OutputCaps(), raw_size=None):
    v = []
    if raw_size is not None and raw_size > caps.max_bytes:
        v.append("bytes %d > %d" % (raw_size, caps.max_bytes))
    if len(snap.requested_assets) > caps.max_requested_assets:
        v.append("requested_assets %d > %d" % (len(snap.requested_assets), caps.max_requested_assets))
    if len(snap.results.details) > caps.max_details:
        v.append("details %d > %d" % (len(snap.results.details), caps.max_details))
    lists = [("ValidatorMessages", snap.results.validator_messages)]
    for d in snap.results.details:
        lists += [(d.object_path + ".ValidationErrors", d.validation_errors),
                  (d.object_path + ".ValidationWarnings", d.validation_warnings),
                  (d.object_path + ".ValidationMessages", d.validation_messages)]
    total = 0
    for name, items in lists:
        total += len(items)
        if len(items) > caps.max_messages_per_list:
            v.append("%s %d > %d" % (name, len(items), caps.max_messages_per_list))
    if total > caps.max_total_messages:
        v.append("total messages %d > %d" % (total, caps.max_total_messages))
    longest = max((len(x) for x in _all_strings(snap)), default=0)
    if longest > caps.max_string_chars:
        v.append("string length %d > %d" % (longest, caps.max_string_chars))
    return v


def check_consistency(snap):
    """Acceptance problems (not malformed input): mirrors the PR #187 contract's intent."""
    p = []
    c = snap.results.counts
    n = len(snap.requested_assets)
    if any(val < 0 for val in c.values()):
        p.append("negative_count")
    if snap.native_return < -2 ** 31 or snap.native_return > INT32_MAX:
        p.append("native_return_out_of_int32")
    if snap.native_return != 0:
        p.append("native_return_nonzero")
    if len(set(snap.requested_assets)) != n:
        p.append("duplicate_requested_assets")
    if c["NumRequested"] != n:
        p.append("num_requested_mismatch")
    if c["NumChecked"] != n or c["NumValid"] != n:
        p.append("not_all_requested_checked_valid")
    if c["NumInvalid"] or c["NumSkipped"] or c["NumWarnings"] or c["NumUnableToValidate"]:
        p.append("invalid_skipped_warning_or_unable")
    if c["NumValid"] + c["NumInvalid"] > c["NumChecked"]:
        p.append("counts_inconsistent")
    m = snap.settings.max_assets_to_validate
    if snap.results.asset_limit_reached or m <= n or m > INT32_MAX:
        p.append("asset_limit_reached_or_insufficient_headroom")
    f = snap.settings.flags
    if not all(f[k] for k in ("bCollectPerAssetDetails", "bLoadAssetsForValidation",
                              "bLoadExternalObjectsForValidation", "bCaptureAssetLoadLogs",
                              "bCaptureLogsDuringValidation")):
        p.append("loading_details_or_log_capture_disabled")
    paths = {d.object_path: d for d in snap.results.details}
    if set(paths) != set(snap.requested_assets):
        p.append("details_identity_mismatch")
    for d in snap.results.details:
        if d.result != "Valid" or d.validation_errors or d.validation_warnings:
            p.append("detail_not_valid:" + d.object_path)
    if any(m.severity in ("Error", "Warning", "PerformanceWarning") for m in snap.results.validator_messages):
        p.append("validator_error_or_warning_message")
    if snap.native_runtime_qualified:
        p.append("native_runtime_qualified_claimed_unexpectedly")
    return p


def consume(text, caps=OutputCaps()):
    """Parse + cap check + consistency. Raises SnapshotError only for malformed input."""
    raw = text.encode("utf-8") if isinstance(text, str) else bytes(text)
    if len(raw) > caps.max_bytes:
        raise SnapshotError("snapshot exceeds max_bytes before parse: %d > %d" % (len(raw), caps.max_bytes))
    snap = parse_snapshot(raw)
    return ConsumerResult(snap, check_caps(snap, caps, len(raw)), check_consistency(snap))


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    with open(argv[1], "rb") as fh:
        data = fh.read()
    try:
        res = consume(data)
    except SnapshotError as e:
        print(json.dumps({"accepted": False, "malformed": str(e)}, indent=2))
        return 1
    print(json.dumps(res.to_dict(), indent=2))
    return 0 if res.accepted else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
