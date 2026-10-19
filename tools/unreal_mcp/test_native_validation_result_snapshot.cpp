// SPDX-License-Identifier: MIT
// test_native_validation_result_snapshot.cpp
//
// Standalone, standard-library-only tests for native_validation_result_snapshot.h.
// No Unreal headers, no DataValidation plugin, no invocation, no I/O beyond stdout.
// STATUS: stdlib tests compiled and run offline (MSVC cl /std:c++17 /EHsc /W4
// /permissive-); the DAEDALUS_WITH_UNREAL_DATAVALIDATION native case is
// authored and skipped without the engine. Command (from tools/unreal_mcp):
//   g++ -std=c++17 -Wall -Wextra -o test_nvrs test_native_validation_result_snapshot.cpp && ./test_nvrs
// (MSVC: cl /std:c++17 /EHsc test_native_validation_result_snapshot.cpp)
// The JSON produced by MakePassing() is the shape evaluate_native_validation()
// in validation_result_contract.py expects; a Python-side cross-check is a
// separate, later step and is not claimed here.
#include "native_validation_result_snapshot.h"

#include <cstdio>
#include <limits>
#include <string>

using namespace daedalus::validation_snapshot;

static int g_failures = 0;
static int g_checks = 0;

#define CHECK(cond) do { ++g_checks; if (!(cond)) { ++g_failures; \
    std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); } } while (0)

static bool Contains(const std::string& hay, const std::string& needle) {
    return hay.find(needle) != std::string::npos;
}

static FValidationSnapshot MakePassing() {
    FValidationSnapshot s;
    s.RequestedAssets = {"/Game/Isolated/SM_Crate.SM_Crate"};
    s.NativeReturn = 0;
    s.Results.NumRequested = 1;
    s.Results.NumChecked = 1;
    s.Results.NumValid = 1;
    FDetailSnapshot d;
    d.PackageName = "/Game/Isolated/SM_Crate";
    d.AssetName = "SM_Crate";
    d.Result = EResult::Valid;
    s.Results.AssetsDetails["/Game/Isolated/SM_Crate.SM_Crate"] = d;
    s.Settings.bCollectPerAssetDetails = true;
    s.Settings.MaxAssetsToValidate = 2;
    return s;
}

static void TestEightCountsAndLimitPreserved() {
    FValidationSnapshot s = MakePassing();
    s.Results.NumExternalObjects = 3;
    s.Results.NumInvalid = 4;
    s.Results.NumSkipped = 5;
    s.Results.NumWarnings = 6;
    s.Results.NumUnableToValidate = 7;
    s.Results.bAssetLimitReached = true;
    const std::string r = SerializeResults(s.Results);
    CHECK(Contains(r, "\"NumRequested\": 1"));
    CHECK(Contains(r, "\"NumExternalObjects\": 3"));
    CHECK(Contains(r, "\"NumChecked\": 1"));
    CHECK(Contains(r, "\"NumValid\": 1"));
    CHECK(Contains(r, "\"NumInvalid\": 4"));
    CHECK(Contains(r, "\"NumSkipped\": 5"));
    CHECK(Contains(r, "\"NumWarnings\": 6"));
    CHECK(Contains(r, "\"NumUnableToValidate\": 7"));
    CHECK(Contains(r, "\"bAssetLimitReached\": true"));
}

static void TestNativeReturnIsIntNotBool() {
    FValidationSnapshot s = MakePassing();
    s.NativeReturn = 1;
    const std::string j = Serialize(s);
    CHECK(Contains(j, "\"native_return\": 1"));
    CHECK(!Contains(j, "\"native_return\": true"));
}

static void TestImpossibleValuesCopiedNotClamped() {
    FValidationSnapshot s = MakePassing();
    s.Results.NumChecked = -1;
    s.NativeReturn = 4294967296LL;
    s.Settings.MaxAssetsToValidate = 0;
    const std::string j = Serialize(s);
    CHECK(Contains(j, "\"NumChecked\": -1"));
    CHECK(Contains(j, "\"native_return\": 4294967296"));
    CHECK(Contains(j, "\"MaxAssetsToValidate\": 0"));
}

static void TestDetailShapeMatchesConsumer() {
    const std::string r = SerializeResults(MakePassing().Results);
    CHECK(Contains(r, "\"AssetsDetails\": {\"/Game/Isolated/SM_Crate.SM_Crate\": {"));
    CHECK(Contains(r, "\"PackageName\": \"/Game/Isolated/SM_Crate\""));
    CHECK(Contains(r, "\"AssetName\": \"SM_Crate\""));
    CHECK(Contains(r, "\"Result\": \"Valid\""));
    CHECK(Contains(r, "\"ValidationErrors\": []"));
    CHECK(Contains(r, "\"ValidationWarnings\": []"));
    CHECK(Contains(r, "\"ValidationMessages\": []"));
    CHECK(Contains(r, "\"ExternalObjects\": []"));
    CHECK(Contains(r, "\"ValidatorMessages\": []"));
}

static void TestDetailResultNeverDefaultsToValid() {
    FDetailSnapshot d;
    CHECK(d.Result == EResult::NotValidated);
    CHECK(std::string(ResultName(EResult::Invalid)) == "Invalid");
    CHECK(std::string(ResultName(EResult::NotValidated)) == "NotValidated");
}

static void TestExternalsAndMessagesPreserved() {
    FValidationSnapshot s = MakePassing();
    auto& d = s.Results.AssetsDetails["/Game/Isolated/SM_Crate.SM_Crate"];
    d.ExternalObjects.push_back({"/Game/__ExternalActors__/X", "A1"});
    d.ValidationWarnings.push_back("warn");
    s.Results.ValidatorMessages.push_back({"Warning", "validator-wide"});
    const std::string r = SerializeResults(s.Results);
    CHECK(Contains(r, "\"ExternalObjects\": [{\"PackageName\": \"/Game/__ExternalActors__/X\", \"AssetName\": \"A1\"}]"));
    CHECK(Contains(r, "\"ValidationWarnings\": [\"warn\"]"));
    CHECK(Contains(r, "\"ValidatorMessages\": [{\"Severity\": \"Warning\", \"Text\": \"validator-wide\"}]"));
}

static void TestSettingsExplicit() {
    const std::string st = SerializeSettings(MakePassing().Settings);
    CHECK(Contains(st, "\"bLoadAssetsForValidation\": true"));
    CHECK(Contains(st, "\"bLoadExternalObjectsForValidation\": true"));
    CHECK(Contains(st, "\"bCollectPerAssetDetails\": true"));
    CHECK(Contains(st, "\"bCaptureAssetLoadLogs\": true"));
    CHECK(Contains(st, "\"bCaptureLogsDuringValidation\": true"));
    CHECK(Contains(st, "\"MaxAssetsToValidate\": 2"));
    CHECK(Contains(st, "\"ValidationUsecase\": \"None\""));
}

static void TestRequestedOrderAndDetailSortDeterministic() {
    FValidationSnapshot s = MakePassing();
    s.RequestedAssets = {"/Game/B.B", "/Game/A.A"};
    const std::string j = Serialize(s);
    CHECK(Contains(j, "\"requested_assets\": [\"/Game/B.B\", \"/Game/A.A\"]"));
    CHECK(Serialize(s) == j);
}

static void TestEscaping() {
    FValidationSnapshot s = MakePassing();
    s.Results.ValidatorMessages.push_back({"Error", "q\"b\\n\nt\tc\x01"});
    const std::string r = SerializeResults(s.Results);
    CHECK(Contains(r, "q\\\"b\\\\n\\nt\\tc\\u0001"));
}

static void TestHonestUnknownsByDefault() {
    const std::string j = Serialize(MakePassing());
    CHECK(Contains(j, "\"fresh_out_results_unproven\""));
    CHECK(Contains(j, "\"native_invocation_unproven\""));
    CHECK(Contains(j, "\"native_runtime_unqualified\""));
    CHECK(Contains(j, "\"validator_statistics_not_captured\""));
    CHECK(Contains(j, "\"native_runtime_qualified\": false"));
    CHECK(Contains(j, "\"snapshot_kind\": \"explicit_native_members_not_mcp_schema\""));
}

static void TestAttestationOnlyRemovesWhatWasAttested() {
    FValidationSnapshot s = MakePassing();
    s.Provenance.FreshOutResults = "attested";
    const std::string j = Serialize(s);
    CHECK(!Contains(j, "\"fresh_out_results_unproven\""));
    CHECK(Contains(j, "\"native_invocation_unproven\""));
    CHECK(Contains(j, "\"native_runtime_unqualified\""));
}

// Regression (stdlib half, AUTHORED_UNRUN): an embedded NUL inside diagnostic
// text survives the serializer as \u0000 with the bytes after it intact. The
// native half (FString "A\0B" through unreal_adapter::ToUtf8) is authored below
// under DAEDALUS_WITH_UNREAL_DATAVALIDATION and has NOT been compiled or run.
static void TestEmbeddedNulPreserved() {
    FValidationSnapshot s = MakePassing();
    s.RequestedAssets = {std::string("A\0B", 3)};
    const std::string j = Serialize(s);
    CHECK(Contains(j, "\"requested_assets\": [\"A\\u0000B\"]"));
    CHECK(!Contains(j, "\"requested_assets\": [\"A\"]"));
}

// ---- Output caps (TrySerialize / FSnapshotLimits) ----

static const size_t kSizeMax = std::numeric_limits<size_t>::max();

static bool Refused(const FSnapshotOutcome& o, ESnapshotStatus want) {
    return o.Status == want && o.Json.empty();
}

// Defaults are the consumer's OutputCaps values (native_validation_snapshot_consumer.py).
static void TestCapDefaultsMatchConsumer() {
    const FSnapshotLimits l;
    CHECK(l.MaxBytes == 8u * 1024u * 1024u);
    CHECK(l.MaxRequestedAssets == 4096);
    CHECK(l.MaxDetails == 4096);
    CHECK(l.MaxMessagesPerList == 1024);
    CHECK(l.MaxStringChars == 16384);
    CHECK(l.MaxTotalMessages == 65536);
    const FSnapshotOutcome blank;
    CHECK(blank.Status != ESnapshotStatus::Ok);
    const FSnapshotOutcome o = TrySerialize(MakePassing());
    CHECK(o.Status == ESnapshotStatus::Ok);
    CHECK(o.Json == Serialize(MakePassing()));
    CHECK(o.Bytes == o.Json.size());
}

// Exact boundary passes, cap-1 (equivalently output of cap+1) refuses whole,
// and the refusal happens before the output buffer is reserved.
static void TestByteCapExactBoundaryAndPlusOne() {
    const FValidationSnapshot s = MakePassing();
    const size_t n = Serialize(s).size();
    FSnapshotLimits l;
    l.MaxBytes = n;
    const FSnapshotOutcome at = TrySerialize(s, l);
    CHECK(at.Status == ESnapshotStatus::Ok);
    CHECK(at.Bytes == n);
    CHECK(at.Json == Serialize(s));
    l.MaxBytes = n - 1;
    const FSnapshotOutcome over = TrySerialize(s, l);
    CHECK(Refused(over, ESnapshotStatus::BytesCapExceeded));
    CHECK(over.Bytes == n);
    CHECK(over.Json.capacity() < 64);  // nothing near n was reserved
    FValidationSnapshot grown = s;     // cap+1 input against the exact cap
    grown.RequestedAssets[0] += "X";
    l.MaxBytes = n;
    const FSnapshotOutcome plus1 = TrySerialize(grown, l);
    CHECK(Refused(plus1, ESnapshotStatus::BytesCapExceeded));
    CHECK(plus1.Bytes == n + 1);
}

static void TestEscapingCountsTowardBytes() {
    const FValidationSnapshot base = MakePassing();
    FValidationSnapshot s = base;
    s.Results.ValidatorMessages.push_back({"E", std::string(10, '\x01')});
    const size_t b0 = TrySerialize(base).Bytes;
    const FSnapshotOutcome o = TrySerialize(s);
    CHECK(o.Status == ESnapshotStatus::Ok);
    CHECK(o.Bytes == o.Json.size());
    CHECK(o.Bytes - b0 == std::string("{\"Severity\": \"E\", \"Text\": \"").size() + 60 + 2);
    FSnapshotLimits l;
    l.MaxBytes = o.Bytes - 1;  // still far above the raw (unescaped) payload size
    CHECK(Refused(TrySerialize(s, l), ESnapshotStatus::BytesCapExceeded));
    FValidationSnapshot nul = base;  // embedded NUL costs 6 bytes, not 1
    nul.RequestedAssets[0] = std::string("A\0B", 3);
    FValidationSnapshot plain = base;
    plain.RequestedAssets[0] = "AXB";
    CHECK(TrySerialize(nul).Bytes == TrySerialize(plain).Bytes + 5);
}

static void TestRowCapsExactBoundaryAndPlusOne() {
    FValidationSnapshot s = MakePassing();
    FSnapshotLimits l;
    l.MaxRequestedAssets = 1;
    l.MaxDetails = 1;
    CHECK(TrySerialize(s, l).Status == ESnapshotStatus::Ok);
    FValidationSnapshot r = s;
    r.RequestedAssets.push_back("/Game/Isolated/SM_Two.SM_Two");
    const FSnapshotOutcome ro = TrySerialize(r, l);
    CHECK(Refused(ro, ESnapshotStatus::RequestedAssetsCapExceeded));
    CHECK(ro.Bytes == 0);  // refused before the measuring pass
    FValidationSnapshot d = s;
    d.Results.AssetsDetails["/Game/Isolated/SM_Two.SM_Two"] = FDetailSnapshot();
    CHECK(Refused(TrySerialize(d, l), ESnapshotStatus::DetailsCapExceeded));

    FSnapshotLimits m;
    m.MaxMessagesPerList = 2;
    m.MaxTotalMessages = 3;
    FValidationSnapshot t = s;
    auto& det = t.Results.AssetsDetails["/Game/Isolated/SM_Crate.SM_Crate"];
    det.ValidationErrors = {"e1", "e2"};
    det.ValidationWarnings = {"w1"};
    const FSnapshotOutcome atTotal = TrySerialize(t, m);
    CHECK(atTotal.Status == ESnapshotStatus::Ok);
    CHECK(atTotal.TotalMessages == 3);
    FValidationSnapshot perList = t;
    perList.Results.AssetsDetails["/Game/Isolated/SM_Crate.SM_Crate"].ValidationErrors.push_back("e3");
    CHECK(Refused(TrySerialize(perList, m), ESnapshotStatus::MessagesPerListCapExceeded));
    FValidationSnapshot vm = s;
    vm.Results.ValidatorMessages = {{"Info", "a"}, {"Info", "b"}, {"Info", "c"}};
    CHECK(Refused(TrySerialize(vm, m), ESnapshotStatus::MessagesPerListCapExceeded));
    FValidationSnapshot total = t;  // every list within 2, cumulative 4 > 3
    total.Results.ValidatorMessages = {{"Info", "v"}};
    const FSnapshotOutcome to = TrySerialize(total, m);
    CHECK(Refused(to, ESnapshotStatus::TotalMessagesCapExceeded));
    CHECK(to.TotalMessages == 4);
    FValidationSnapshot ext = s;  // ExternalObjects are not message rows
    ext.Results.AssetsDetails["/Game/Isolated/SM_Crate.SM_Crate"].ExternalObjects.assign(5, {"/Game/X", "A"});
    FSnapshotLimits zeroMsgs;
    zeroMsgs.MaxTotalMessages = 0;
    CHECK(TrySerialize(ext, zeroMsgs).Status == ESnapshotStatus::Ok);
}

static void TestStringCharsCapCodePointsExactBoundaryAndPlusOne() {
    FSnapshotLimits l;
    l.MaxStringChars = 8;
    FValidationSnapshot s;  // empty: no requested assets or details
    s.RequestedAssets = {"12345678"};
    CHECK(TrySerialize(s, l).Status == ESnapshotStatus::Ok);
    s.RequestedAssets = {"123456789"};
    CHECK(Refused(TrySerialize(s, l), ESnapshotStatus::StringCharsCapExceeded));
    std::string e8;
    for (int i = 0; i < 8; ++i) e8 += "\xC3\xA9";  // 8 code points, 16 bytes
    s.RequestedAssets = {e8};
    CHECK(TrySerialize(s, l).Status == ESnapshotStatus::Ok);
    s.RequestedAssets = {e8 + "\xC3\xA9"};
    CHECK(Refused(TrySerialize(s, l), ESnapshotStatus::StringCharsCapExceeded));
    FValidationSnapshot msg;
    msg.Results.ValidatorMessages = {{"Error", "123456789"}};
    CHECK(Refused(TrySerialize(msg, l), ESnapshotStatus::StringCharsCapExceeded));
    FValidationSnapshot ext;
    FDetailSnapshot d;
    d.ExternalObjects.push_back({"/Game/X", "123456789"});
    ext.Results.AssetsDetails["/G.A"] = d;
    CHECK(Refused(TrySerialize(ext, l), ESnapshotStatus::StringCharsCapExceeded));
    FValidationSnapshot key;
    key.Results.AssetsDetails["/Game/A.A123"] = FDetailSnapshot();
    CHECK(Refused(TrySerialize(key, l), ESnapshotStatus::StringCharsCapExceeded));
}

static void TestSizeOverflowRefusedNotWrapped() {
    size_t sum = 7;
    CHECK(!detail::CheckedAdd(kSizeMax, 1, &sum));
    CHECK(sum == 7);
    CHECK(detail::CheckedAdd(kSizeMax - 1, 1, &sum));
    CHECK(sum == kSizeMax);
    detail::FByteCounter c;
    c.Count = kSizeMax - 3;
    detail::AppendEscaped(c, std::string("abc"));  // 5 bytes with quotes
    CHECK(c.Overflow);
    c.push_back('x');
    CHECK(c.Overflow);  // latched, never wraps back to a small count
    detail::FByteCounter whole;
    whole.Count = kSizeMax - 10;
    detail::AppendSnapshot(whole, MakePassing());  // same writer TrySerialize measures with
    CHECK(whole.Overflow);
    FSnapshotLimits huge;
    huge.MaxBytes = huge.MaxRequestedAssets = huge.MaxDetails = kSizeMax;
    huge.MaxMessagesPerList = huge.MaxStringChars = huge.MaxTotalMessages = kSizeMax;
    CHECK(TrySerialize(MakePassing(), huge).Status == ESnapshotStatus::Ok);
}

static void TestZeroCaps() {
    FSnapshotLimits zero;
    zero.MaxRequestedAssets = zero.MaxDetails = zero.MaxMessagesPerList = 0;
    zero.MaxStringChars = zero.MaxTotalMessages = 0;
    const FValidationSnapshot empty;
    CHECK(TrySerialize(empty, zero).Status == ESnapshotStatus::Ok);  // 0 rows == cap 0
    CHECK(Refused(TrySerialize(MakePassing(), zero), ESnapshotStatus::RequestedAssetsCapExceeded));
    FSnapshotLimits noBytes;
    noBytes.MaxBytes = 0;
    CHECK(Refused(TrySerialize(empty, noBytes), ESnapshotStatus::BytesCapExceeded));
    CHECK(std::string(SnapshotStatusName(ESnapshotStatus::BytesCapExceeded)) == "BytesCapExceeded");
}

#if defined(DAEDALUS_WITH_UNREAL_DATAVALIDATION)
static void TestNativeToUtf8EmbeddedNul() {
    const TCHAR Raw[] = {TEXT('A'), TEXT('\0'), TEXT('B')};
    const FString S(3, Raw);
    const std::string U = daedalus::validation_snapshot::unreal_adapter::ToUtf8(S);
    CHECK(U.size() == 3);
    CHECK(U == std::string("A\0B", 3));
}
#endif

int main() {
    TestEightCountsAndLimitPreserved();
    TestNativeReturnIsIntNotBool();
    TestImpossibleValuesCopiedNotClamped();
    TestDetailShapeMatchesConsumer();
    TestDetailResultNeverDefaultsToValid();
    TestExternalsAndMessagesPreserved();
    TestSettingsExplicit();
    TestRequestedOrderAndDetailSortDeterministic();
    TestEscaping();
    TestHonestUnknownsByDefault();
    TestAttestationOnlyRemovesWhatWasAttested();
    TestEmbeddedNulPreserved();
    TestCapDefaultsMatchConsumer();
    TestByteCapExactBoundaryAndPlusOne();
    TestEscapingCountsTowardBytes();
    TestRowCapsExactBoundaryAndPlusOne();
    TestStringCharsCapCodePointsExactBoundaryAndPlusOne();
    TestSizeOverflowRefusedNotWrapped();
    TestZeroCaps();
#if defined(DAEDALUS_WITH_UNREAL_DATAVALIDATION)
    TestNativeToUtf8EmbeddedNul();
#endif
    std::printf("%d checks, %d failures\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
