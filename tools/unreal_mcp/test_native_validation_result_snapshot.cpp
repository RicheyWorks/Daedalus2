// SPDX-License-Identifier: MIT
// test_native_validation_result_snapshot.cpp
//
// Standalone, standard-library-only tests for native_validation_result_snapshot.h.
// No Unreal headers, no DataValidation plugin, no invocation, no I/O beyond stdout.
// STATUS: AUTHORED_UNRUN. Do not run until a fresh serialized resource clear is
// granted. Intended command (one serial process, from tools/unreal_mcp):
//   g++ -std=c++17 -Wall -Wextra -o test_nvrs test_native_validation_result_snapshot.cpp && ./test_nvrs
// (MSVC: cl /std:c++17 /EHsc test_native_validation_result_snapshot.cpp)
// The JSON produced by MakePassing() is the shape evaluate_native_validation()
// in validation_result_contract.py expects; a Python-side cross-check is a
// separate, later step and is not claimed here.
#include "native_validation_result_snapshot.h"

#include <cstdio>
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
    std::printf("%d checks, %d failures\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
