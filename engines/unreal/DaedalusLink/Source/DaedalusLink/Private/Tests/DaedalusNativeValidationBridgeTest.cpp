// SPDX-License-Identifier: MIT
#include "DaedalusNativeValidationBridge.h"

#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "Dom/JsonObject.h"
#include "EditorValidatorSubsystem.h"
#include "Logging/TokenizedMessage.h"
#include "Misc/AutomationTest.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace
{
const FString FixtureRoot(TEXT("/Game/CodexToolEvaluation/NativeValidation"));
const FString FixturePath(FixtureRoot + TEXT("/A.A"));

FValidateAssetsSettings SettingsForTest()
{
    FValidateAssetsSettings Settings;
    Settings.bCollectPerAssetDetails = true;
    Settings.bLoadExternalObjectsForValidation = true;
    Settings.MaxAssetsToValidate = 2;
    return Settings;
}

FValidateAssetsResults OneResult(EDataValidationResult Result)
{
    FValidateAssetsResults Out;
    Out.NumRequested = 1;
    Out.NumChecked = 1;
    Out.NumValid = Result == EDataValidationResult::Valid ? 1 : 0;
    Out.NumInvalid = Result == EDataValidationResult::Invalid ? 1 : 0;
    Out.NumUnableToValidate = Result == EDataValidationResult::NotValidated ? 1 : 0;
    FValidateAssetsDetails& Detail = Out.AssetsDetails.Add(FixturePath);
    Detail.PackageName = FName(*(FixtureRoot + TEXT("/A")));
    Detail.AssetName = FName(TEXT("A"));
    Detail.Result = Result;
    return Out;
}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusValidationPolicyTest,
    "Daedalus.Editor.Validation.Policy",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDaedalusValidationPolicyTest::RunTest(const FString& Parameters)
{
    FDaedalusNativeValidationRequest Request;
    Request.AllowedPackageRoot = FixtureRoot;
    Request.AssetObjectPaths = {FixturePath};
    FString Why;
    TestTrue(TEXT("Canonical explicit request"), FDaedalusNativeValidationBridge::CheckRequest(Request, Why));
    auto Refused = [&](const TCHAR* Label, const TArray<FString>& Paths, const FString& Root)
    {
        auto Copy = Request; Copy.AssetObjectPaths = Paths; Copy.AllowedPackageRoot = Root;
        TestFalse(Label, FDaedalusNativeValidationBridge::CheckRequest(Copy, Why));
        TestFalse(TEXT("Actionable rejection"), Why.IsEmpty());
    };
    Refused(TEXT("Empty"), {}, FixtureRoot);
    Refused(TEXT("Broad root"), {FixturePath}, TEXT("/Game"));
    Refused(TEXT("Trailing slash"), {FixturePath}, FixtureRoot + TEXT("/"));
    Refused(TEXT("Sibling prefix"), {FixtureRoot + TEXT("Else/A.A")}, FixtureRoot);
    Refused(TEXT("Subobject"), {FixturePath + TEXT(":Child")}, FixtureRoot);
    Refused(TEXT("Duplicate"), {FixturePath, FixturePath}, FixtureRoot);
    Refused(TEXT("Case alias"), {FixturePath, FixturePath.LeftChop(1) + TEXT("a")}, FixtureRoot);
    TArray<FString> TooMany;
    for (int32 Index = 0; Index <= FDaedalusNativeValidationBridge::MaxNamedAssets; ++Index)
        TooMany.Add(FString::Printf(TEXT("%s/A%d.A%d"), *FixtureRoot, Index, Index));
    Refused(TEXT("Work cap"), TooMany, FixtureRoot);
    Request.bCancelRequested = true;
    const auto Cancelled = FDaedalusNativeValidationBridge::ValidateWithCancellation(Request, [] { return false; });
    TestEqual(TEXT("Explicit pre-call cancellation"), Cancelled.Status, EDaedalusNativeValidationStatus::Cancelled);
    TestFalse(TEXT("Cancelled request did not invoke engine"), Cancelled.bNativeInvoked);
    TestFalse(TEXT("Cancelled request not accepted"), Cancelled.bAccepted);
    TestTrue(TEXT("No fabricated snapshot"), Cancelled.SnapshotJson.IsEmpty());
    TestTrue(TEXT("Cancellation is retained independently"), Cancelled.bCancellationObserved);
    Request.bCancelRequested = false;
    const auto Again = FDaedalusNativeValidationBridge::ValidateWithCancellation(Request, [] { return true; });
    TestEqual(TEXT("RAII guard released after cancellation"), Again.Status, EDaedalusNativeValidationStatus::Cancelled);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusValidationProjectionTest,
    "Daedalus.Editor.Validation.NativeProjection",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDaedalusValidationProjectionTest::RunTest(const FString& Parameters)
{
    using Status = EDaedalusNativeValidationStatus;
    const auto Settings = SettingsForTest();
    auto Project = [&](const FValidateAssetsResults& Result, int32 NativeReturn = 0, bool Cancelled = false)
    { return FDaedalusNativeValidationBridge::ProjectNativeResult({FixturePath}, Settings, NativeReturn, Result, Cancelled); };
    auto Native = OneResult(EDataValidationResult::Valid);
    auto Reply = Project(Native);
    TestEqual(TEXT("Complete valid projection"), Reply.Status, Status::Valid);
    TestFalse(TEXT("Projection never fabricates invocation"), Reply.bNativeInvoked);
    TestFalse(TEXT("Projection alone is never acceptance"), Reply.bAccepted);
    TSharedPtr<FJsonObject> Json;
    TestTrue(TEXT("Real adapter emits canonical JSON"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Reply.SnapshotJson), Json));
    if (Json.IsValid())
    {
        TestTrue(TEXT("Existing consumer requested-assets key"), Json->HasField(TEXT("requested_assets")));
        TestTrue(TEXT("Existing consumer settings key"), Json->HasField(TEXT("settings")));
        TestTrue(TEXT("Existing consumer results key"), Json->HasField(TEXT("results")));
    }
    TSharedPtr<FJsonObject> Envelope;
    const FString EnvelopeText = FDaedalusNativeValidationBridge::SerializeReply(Reply);
    TestTrue(TEXT("Envelope parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(EnvelopeText), Envelope));
    if (Envelope.IsValid())
    {
        TestEqual(TEXT("Canonical payload is byte-for-byte unchanged as text"), Envelope->GetStringField(TEXT("snapshot_json")), Reply.SnapshotJson);
        TestFalse(TEXT("Projection envelope never accepts"), Envelope->GetBoolField(TEXT("accepted")));
        const auto Return = Envelope->TryGetField(TEXT("native_return"));
        TestTrue(TEXT("Uninvoked native return is null"), Return.IsValid() && Return->IsNull());
    }
    TestEqual(TEXT("Invalid is not pass"), Project(OneResult(EDataValidationResult::Invalid), 1).Status, Status::Invalid);
    TestEqual(TEXT("No validator is not pass"), Project(OneResult(EDataValidationResult::NotValidated)).Status, Status::NotValidated);
    Native = {}; Native.NumRequested = 1; Native.NumSkipped = 1;
    TestEqual(TEXT("Skipped remains distinct"), Project(Native).Status, Status::Skipped);
    Native = OneResult(EDataValidationResult::Valid); Native.NumWarnings = 1;
    TestEqual(TEXT("Warnings are not clean acceptance"), Project(Native, 1).Status, Status::Warnings);
    Native = OneResult(EDataValidationResult::Valid); Native.bAssetLimitReached = true;
    TestEqual(TEXT("Native limit never pass"), Project(Native).Status, Status::Incomplete);
    Native = OneResult(EDataValidationResult::Valid); Native.AssetsDetails.Empty();
    TestEqual(TEXT("Missing details never pass"), Project(Native).Status, Status::Incomplete);
    Native = OneResult(EDataValidationResult::Valid); Native.NumChecked = 0;
    TestEqual(TEXT("Partial counts never pass"), Project(Native).Status, Status::Incomplete);
    Native = OneResult(EDataValidationResult::Valid); Native.NumRequested = -1;
    TestEqual(TEXT("Negative counters are errors"), Project(Native).Status, Status::Error);
    Native = OneResult(EDataValidationResult::Valid);
    TestEqual(TEXT("Return disagreement is error"), Project(Native, 1).Status, Status::Error);
    TestEqual(TEXT("Cancelled completed work not pass"), Project(Native, 0, true).Status, Status::Cancelled);
    Native.ValidatorMessages.Add(FTokenizedMessage::Create(EMessageSeverity::Error, FText::FromString(TEXT("Native global error"))));
    TestEqual(TEXT("Global error cannot hide behind valid counts"), Project(Native).Status, Status::Error);
    Native = OneResult(EDataValidationResult::Valid);
    Native.ValidatorMessages.Add(FTokenizedMessage::Create(EMessageSeverity::PerformanceWarning, FText::FromString(TEXT("Native performance warning"))));
    TestEqual(TEXT("Performance warning is actionable"), Project(Native).Status, Status::Warnings);
    Native = OneResult(EDataValidationResult::Valid);
    Native.AssetsDetails[FixturePath].AssetName = TEXT("Wrong");
    TestEqual(TEXT("Identity mismatch"), Project(Native).Status, Status::Incomplete);
    Native = OneResult(EDataValidationResult::Valid);
    Native.AssetsDetails[FixturePath].ValidationErrors.Add(FText::FromString(TEXT("evidence\n\"quoted\" \u03bb")));
    TestEqual(TEXT("Error text cannot pass with Valid enum"), Project(Native).Status, Status::Error);
    Native.AssetsDetails[FixturePath].ValidationErrors[0] = FText::FromString(FString::ChrN(2049, TEXT('x')));
    Reply = Project(Native);
    TestEqual(TEXT("Oversize native text refused"), Reply.Status, Status::Error);
    TestTrue(TEXT("Refusal does not truncate JSON"), Reply.SnapshotJson.IsEmpty());
    auto BadSettings = Settings;
    BadSettings.bCaptureLogsDuringValidation = false;
    TestEqual(TEXT("Consumer-required settings cannot be weakened"),
        FDaedalusNativeValidationBridge::ProjectNativeResult({FixturePath}, BadSettings, 0,
            OneResult(EDataValidationResult::Valid), false).Status, Status::Incomplete);
    FDaedalusNativeValidationReply TooLarge;
    TooLarge.bNativeInvoked = true;
    TooLarge.NativeReturn = 7;
    TooLarge.Diagnostic = FString::ChrN(2049, TEXT('x'));
    TSharedPtr<FJsonObject> Refusal;
    TestTrue(TEXT("Output refusal is complete JSON"), FJsonSerializer::Deserialize(
        TJsonReaderFactory<>::Create(FDaedalusNativeValidationBridge::SerializeReply(TooLarge)), Refusal));
    if (Refusal.IsValid())
    {
        TestTrue(TEXT("Output failure retains actual invocation"), Refusal->GetBoolField(TEXT("native_invoked")));
        TestEqual(TEXT("Output failure retains return"), Refusal->GetNumberField(TEXT("native_return")), 7.0);
        TestFalse(TEXT("Output failure cannot pass"), Refusal->GetBoolField(TEXT("accepted")));
    }
    return true;
}

// REAL native calls, only for explicit, already-loaded owner fixtures. The sole operator
// supplies all four command-line values before running this exact test, e.g.
// -DaedalusValidationFixtureRoot=/Game/CodexToolEvaluation/NativeValidation/Run123
// -DaedalusValidationValid=<objectpath> -DaedalusValidationInvalid=<objectpath>
// -DaedalusValidationNotValidated=<objectpath>
// No guessed assets, world scan, fixture creation, load/save, validator registration or
// cleanup of someone else's work. Operator owns fixture setup and final preservation.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusValidationNamedFixturesTest,
    "Daedalus.Editor.Validation.NamedFixtures",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDaedalusValidationNamedFixturesTest::RunTest(const FString& Parameters)
{
    FString Root, Valid, Invalid, NotValidated;
    const TCHAR* Args = FCommandLine::Get();
    if (!FParse::Value(Args, TEXT("DaedalusValidationFixtureRoot="), Root) ||
        !FParse::Value(Args, TEXT("DaedalusValidationValid="), Valid) ||
        !FParse::Value(Args, TEXT("DaedalusValidationInvalid="), Invalid) ||
        !FParse::Value(Args, TEXT("DaedalusValidationNotValidated="), NotValidated))
    {
        AddError(TEXT("Explicit owner fixture root/Valid/Invalid/NotValidated arguments required; no fallback/native call made."));
        return false;
    }
    FDaedalusNativeValidationRequest Request;
    Request.AllowedPackageRoot = Root;
    const FString Paths[] = {Valid, Invalid, NotValidated};
    Request.AssetObjectPaths = {Valid, Invalid, NotValidated};
    FString Why;
    if (!FDaedalusNativeValidationBridge::CheckRequest(Request, Why))
    {
        AddError(TEXT("All three fixture names must be distinct and inside the approved root before any native call: ") + Why);
        return false;
    }
    const EDaedalusNativeValidationStatus Expected[] = {EDaedalusNativeValidationStatus::Valid,
        EDaedalusNativeValidationStatus::Invalid, EDaedalusNativeValidationStatus::NotValidated};
    for (int32 Index = 0; Index < 3; ++Index)
    {
        Request.AssetObjectPaths = {Paths[Index]};
        const auto Reply = FDaedalusNativeValidationBridge::ValidateNamedAssets(Request);
        TestTrue(*FString::Printf(TEXT("Actual native invocation %d: %s"), Index, *Reply.Diagnostic), Reply.bNativeInvoked);
        TestEqual(TEXT("Actual engine classification"), Reply.Status, Expected[Index]);
        TestEqual(TEXT("Only fully valid invocation accepted"), Reply.bAccepted, Index == 0);
        TestFalse(TEXT("Actual result snapshot retained"), Reply.SnapshotJson.IsEmpty());
    }
    return true;
}
#endif
