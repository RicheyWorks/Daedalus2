// SPDX-License-Identifier: MIT
#include "DaedalusNativeValidationBridge.h"

#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Editor.h"
#include "EditorValidatorSubsystem.h"
#include "Logging/TokenizedMessage.h"
#include "Misc/DateTime.h"
#include "Misc/FeedbackContext.h"
#include "Misc/PackageName.h"
#include "Modules/ModuleManager.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Templates/UnrealTemplate.h"
#include "UObject/Package.h"
#include "UObject/SoftObjectPath.h"
#include "UObject/StrongObjectPtr.h"

// Reuse the merged serializer AND its typed native adapter. The integrator supplies
// its canonical include path; neither the schema nor the serializer is reimplemented.
#define DAEDALUS_WITH_UNREAL_DATAVALIDATION 1
#include "native_validation_result_snapshot.h"
#undef DAEDALUS_WITH_UNREAL_DATAVALIDATION

namespace
{
bool GValidationBridgeActive = false; // accessed only on the game thread
constexpr int32 MaxTextChars = 2048;
constexpr int32 MaxMessagesPerList = 32;
constexpr int32 MaxTotalMessages = 128;
constexpr int32 MaxSnapshotBytes = 256 * 1024;

FDaedalusNativeValidationReply Refuse(EDaedalusNativeValidationStatus Status, const TCHAR* Why)
{
    FDaedalusNativeValidationReply Reply;
    Reply.Status = Status;
    Reply.bCancellationObserved = Status == EDaedalusNativeValidationStatus::Cancelled;
    Reply.Diagnostic = Why;
    return Reply;
}

bool IsFailureMessage(const TSharedRef<FTokenizedMessage>& Message)
{
    const auto Severity = Message->GetSeverity();
    return Severity != EMessageSeverity::Info && Severity != EMessageSeverity::Warning &&
           Severity != EMessageSeverity::PerformanceWarning;
}

bool IsWarningMessage(const TSharedRef<FTokenizedMessage>& Message)
{
    return Message->GetSeverity() == EMessageSeverity::Warning ||
           Message->GetSeverity() == EMessageSeverity::PerformanceWarning;
}

// Bound every native list/text BEFORE the canonical native adapter allocates copies.
// These are conservative UTF-16 code-unit bounds, then its exact UTF-8/byte caps apply.
bool FitsCopyBudget(const FValidateAssetsResults& Results)
{
    if (Results.AssetsDetails.Num() > FDaedalusNativeValidationBridge::MaxNamedAssets)
        return false;
    int64 Total = 0;
    auto MessagesFit = [&Total](const TArray<TSharedRef<FTokenizedMessage>>& Messages)
    {
        if (Messages.Num() > MaxMessagesPerList) return false;
        Total += Messages.Num();
        for (const TSharedRef<FTokenizedMessage>& Message : Messages)
            if (Message->ToText().ToString().Len() > MaxTextChars) return false;
        return Total <= MaxTotalMessages;
    };
    auto TextsFit = [&Total](const TArray<FText>& Texts)
    {
        if (Texts.Num() > MaxMessagesPerList) return false;
        Total += Texts.Num();
        for (const FText& Text : Texts)
            if (Text.ToString().Len() > MaxTextChars) return false;
        return Total <= MaxTotalMessages;
    };
    if (!MessagesFit(Results.ValidatorMessages)) return false;
    for (const auto& Pair : Results.AssetsDetails)
    {
        const FValidateAssetsDetails& Detail = Pair.Value;
        if (Pair.Key.Len() > FDaedalusNativeValidationBridge::MaxPathChars ||
            Detail.PackageName.ToString().Len() > FDaedalusNativeValidationBridge::MaxPathChars ||
            Detail.AssetName.ToString().Len() > FDaedalusNativeValidationBridge::MaxPathChars ||
            Detail.ExternalObjects.Num() > FDaedalusNativeValidationBridge::MaxNamedAssets ||
            !TextsFit(Detail.ValidationErrors) || !TextsFit(Detail.ValidationWarnings) ||
            !MessagesFit(Detail.ValidationMessages)) return false;
        for (const FValidateAssetsExternalObject& External : Detail.ExternalObjects)
            if (External.PackageName.ToString().Len() > FDaedalusNativeValidationBridge::MaxPathChars ||
                External.AssetName.ToString().Len() > FDaedalusNativeValidationBridge::MaxPathChars)
                return false;
    }
    return true;
}

EDaedalusNativeValidationStatus Classify(
    const TArray<FString>& Paths, int32 NativeReturn, const FValidateAssetsResults& R,
    bool bCancelled, FString& Why)
{
    using Status = EDaedalusNativeValidationStatus;
    auto Result = [&Why](Status Value, const TCHAR* Text) { Why = Text; return Value; };
    if (bCancelled) return Result(Status::Cancelled, TEXT("Cancellation observed; no acceptance."));
    const int32 Counts[] = {R.NumRequested, R.NumExternalObjects, R.NumChecked, R.NumValid,
        R.NumInvalid, R.NumSkipped, R.NumWarnings, R.NumUnableToValidate};
    for (int32 Count : Counts)
        if (Count < 0) return Result(Status::Error, TEXT("Negative native validation counter."));
    if (R.NumWarnings > R.NumChecked)
        return Result(Status::Error, TEXT("Warning asset count exceeds checked assets."));
    if (NativeReturn < 0 || static_cast<int64>(NativeReturn) !=
        static_cast<int64>(R.NumInvalid) + R.NumWarnings)
        return Result(Status::Error, TEXT("Native return disagrees with invalid/warning counts."));
    if (Paths.IsEmpty() || R.NumRequested != Paths.Num() || R.NumExternalObjects != 0 ||
        R.bAssetLimitReached || static_cast<int64>(R.NumChecked) + R.NumSkipped != Paths.Num() ||
        static_cast<int64>(R.NumValid) + R.NumInvalid + R.NumUnableToValidate != R.NumChecked ||
        R.AssetsDetails.Num() != R.NumChecked)
        return Result(Status::Incomplete, TEXT("Incomplete, expanded or limited validation result."));
    TSet<FString> Expected(Paths);
    int32 Valid = 0, Invalid = 0, NotValidated = 0;
    bool bErrors = false, bWarnings = false;
    for (const auto& Pair : R.AssetsDetails)
    {
        const FValidateAssetsDetails& D = Pair.Value;
        if (!Expected.Contains(Pair.Key) || !D.ExternalObjects.IsEmpty() ||
            D.PackageName.ToString() != FPackageName::ObjectPathToPackageName(Pair.Key) ||
            D.AssetName.ToString() != FPackageName::ObjectPathToObjectName(Pair.Key))
            return Result(Status::Incomplete, TEXT("Unexpected asset identity/external object in result."));
        switch (D.Result)
        {
            case EDataValidationResult::Valid: ++Valid; break;
            case EDataValidationResult::Invalid: ++Invalid; break;
            case EDataValidationResult::NotValidated: ++NotValidated; break;
            default: return Result(Status::Error, TEXT("Unknown native validation enum."));
        }
        bErrors |= !D.ValidationErrors.IsEmpty();
        bWarnings |= !D.ValidationWarnings.IsEmpty();
        for (const auto& Message : D.ValidationMessages)
        {
            bErrors |= IsFailureMessage(Message);
            bWarnings |= IsWarningMessage(Message);
        }
    }
    if (Valid != R.NumValid || Invalid != R.NumInvalid || NotValidated != R.NumUnableToValidate)
        return Result(Status::Error, TEXT("Native per-asset details disagree with counters."));
    for (const auto& Message : R.ValidatorMessages)
    {
        bErrors |= IsFailureMessage(Message);
        bWarnings |= IsWarningMessage(Message);
    }
    if (R.NumInvalid) return Result(Status::Invalid, TEXT("One or more assets are Invalid."));
    if (bErrors) return Result(Status::Error, TEXT("Error diagnostics accompany a non-Invalid result."));
    if (R.NumSkipped) return Result(Status::Skipped, TEXT("Assets were skipped; no full acceptance."));
    if (R.NumUnableToValidate)
        return Result(Status::NotValidated, TEXT("No applicable validation for one or more assets."));
    if (R.NumWarnings || bWarnings) return Result(Status::Warnings, TEXT("Validation produced warnings."));
    return Result(Status::Valid, TEXT("Complete Valid result for every exact requested asset."));
}
} // namespace

bool FDaedalusNativeValidationBridge::CheckRequest(
    const FDaedalusNativeValidationRequest& Request, FString& Why)
{
    Why.Reset();
    const FString& Root = Request.AllowedPackageRoot;
    if (Request.AssetObjectPaths.IsEmpty() || Request.AssetObjectPaths.Num() > MaxNamedAssets)
    { Why = TEXT("Require 1..16 exact object paths."); return false; }
    if (Root.Len() > MaxPathChars || !Root.StartsWith(TEXT("/Game/"), ESearchCase::CaseSensitive) ||
        Root.EndsWith(TEXT("/")) || !FPackageName::IsValidLongPackageName(Root))
    { Why = TEXT("Require a canonical owner-approved /Game subtree, without a trailing slash."); return false; }
    TSet<FString> Seen;
    for (const FString& Path : Request.AssetObjectPaths)
    {
        if (Path.Len() > MaxPathChars || !FPackageName::IsValidObjectPath(Path) ||
            !FSoftObjectPath(Path).GetSubPathString().IsEmpty() ||
            FSoftObjectPath(Path).ToString() != Path ||
            !FPackageName::ObjectPathToPackageName(Path).StartsWith(Root + TEXT("/"), ESearchCase::CaseSensitive))
        { Why = TEXT("Object path is noncanonical, a subobject, or outside the approved subtree."); return false; }
        const FString Folded = Path.ToLower();
        if (Seen.Contains(Folded))
        { Why = TEXT("Duplicate/case-alias object path refused."); return false; }
        Seen.Add(Folded);
    }
    return true;
}

namespace
{
FDaedalusNativeValidationReply ProjectResult(
    const TArray<FString>& Paths, const FValidateAssetsSettings& Settings,
    int32 NativeReturn, const FValidateAssetsResults& Results, bool bCancelled, bool bAttestInvocation)
{
    using namespace daedalus::validation_snapshot;
    constexpr int32 MaxNamedAssets = FDaedalusNativeValidationBridge::MaxNamedAssets;
    constexpr int32 MaxPathChars = FDaedalusNativeValidationBridge::MaxPathChars;
    if (Paths.IsEmpty() || Paths.Num() > MaxNamedAssets || !FitsCopyBudget(Results))
        return Refuse(EDaedalusNativeValidationStatus::Error, TEXT("Native snapshot exceeds bounded copy policy."));
    FValidationSnapshot Snapshot;
    for (const FString& Path : Paths)
    {
        if (Path.Len() > MaxPathChars)
            return Refuse(EDaedalusNativeValidationStatus::Error, TEXT("Requested path exceeds snapshot cap."));
        Snapshot.RequestedAssets.push_back(unreal_adapter::ToUtf8(Path));
    }
    Snapshot.NativeReturn = NativeReturn;
    Snapshot.Settings = unreal_adapter::FromNative(Settings);
    if (bAttestInvocation)
    {
        Snapshot.Provenance.FreshOutResults = "attested";
        Snapshot.Provenance.NativeInvocation = "attested";
        Snapshot.Provenance.CapturedAtUtc = unreal_adapter::ToUtf8(FDateTime::UtcNow().ToIso8601());
    }
    FSnapshotLimits Limits;
    Limits.MaxBytes = MaxSnapshotBytes;
    Limits.MaxRequestedAssets = MaxNamedAssets;
    Limits.MaxDetails = MaxNamedAssets;
    Limits.MaxMessagesPerList = MaxMessagesPerList;
    Limits.MaxStringChars = MaxTextChars;
    Limits.MaxTotalMessages = MaxTotalMessages;
    const ESnapshotStatus CopyStatus = unreal_adapter::TryFromNative(Results, Limits, Snapshot.Results);
    if (CopyStatus != ESnapshotStatus::Ok)
        return Refuse(EDaedalusNativeValidationStatus::Error, TEXT("Canonical native snapshot adapter refused output."));
    const FSnapshotOutcome Serialized = TrySerialize(Snapshot, Limits);
    if (Serialized.Status != ESnapshotStatus::Ok)
        return Refuse(EDaedalusNativeValidationStatus::Error, TEXT("Canonical serializer refused output; nothing truncated."));
    FDaedalusNativeValidationReply Reply;
    Reply.NativeReturn = NativeReturn;
    Reply.bCancellationObserved = bCancelled;
    Reply.Status = Classify(Paths, NativeReturn, Results, bCancelled, Reply.Diagnostic);
    if (Reply.Status == EDaedalusNativeValidationStatus::Valid &&
        (!Settings.bCollectPerAssetDetails || !Settings.bLoadAssetsForValidation ||
         !Settings.bLoadExternalObjectsForValidation || !Settings.bCaptureAssetLoadLogs ||
         !Settings.bCaptureLogsDuringValidation || Settings.MaxAssetsToValidate <= Paths.Num()))
    {
        Reply.Status = EDaedalusNativeValidationStatus::Incomplete;
        Reply.Diagnostic = TEXT("Settings do not satisfy the unchanged canonical consumer acceptance contract.");
    }
    const FUTF8ToTCHAR Converted(Serialized.Json.data(), static_cast<int32>(Serialized.Json.size()));
    Reply.SnapshotJson = FString(Converted.Length(), Converted.Get());
    return Reply;
}
} // namespace

FDaedalusNativeValidationReply FDaedalusNativeValidationBridge::ProjectNativeResult(
    const TArray<FString>& Paths, const FValidateAssetsSettings& Settings,
    int32 NativeReturn, const FValidateAssetsResults& Results, bool bCancelled)
{
    FDaedalusNativeValidationReply Reply = ProjectResult(Paths, Settings, NativeReturn, Results, bCancelled, false);
    Reply.bCancellationObserved = bCancelled;
    return Reply;
}

FDaedalusNativeValidationReply FDaedalusNativeValidationBridge::ValidateWithCancellation(
    const FDaedalusNativeValidationRequest& Request, TFunctionRef<bool()> ShouldCancel)
{
    using Status = EDaedalusNativeValidationStatus;
    if (!IsInGameThread()) return Refuse(Status::Rejected, TEXT("Validation requires the editor game thread."));
    if (GValidationBridgeActive) return Refuse(Status::Rejected, TEXT("Reentrant validation refused."));
    TGuardValue<bool> Guard(GValidationBridgeActive, true);
    FString Why;
    if (!CheckRequest(Request, Why))
    {
        FDaedalusNativeValidationReply Reply = Refuse(Status::Rejected, TEXT("Invalid request."));
        Reply.Diagnostic = Why;
        return Reply;
    }
    const FDaedalusNativeValidationRequest Frozen = Request;
    if (Frozen.bCancelRequested || ShouldCancel())
        return Refuse(Status::Cancelled, TEXT("Cancelled before asset/subsystem access."));
    if (!GIsEditor || !GEditor || GEditor->PlayWorld)
        return Refuse(Status::Rejected, TEXT("Require an editor with no PIE session."));
    if (FAssetCompilingManager::Get().GetNumRemainingAssets() != 0)
        return Refuse(Status::Rejected, TEXT("Asset compilation is active; validation was not dispatched."));
    auto* RegistryModule = FModuleManager::GetModulePtr<FAssetRegistryModule>(TEXT("AssetRegistry"));
    auto* Subsystem = GEditor->GetEditorSubsystem<UEditorValidatorSubsystem>();
    if (!RegistryModule || !Subsystem)
        return Refuse(Status::Error, TEXT("AssetRegistry/DataValidation subsystem is not loaded; no fallback load."));
    IAssetRegistry& Registry = RegistryModule->Get();
    if (Registry.IsLoadingAssets())
        return Refuse(Status::Rejected, TEXT("Asset registry discovery is active; no scan or wait added."));
    TArray<FAssetData> Assets;
    TArray<TStrongObjectPtr<UObject>> HeldAssets;
    for (const FString& Path : Frozen.AssetObjectPaths)
    {
        const FSoftObjectPath SoftPath(Path);
        UObject* Object = SoftPath.ResolveObject(); // never TryLoad/GetAsset
        const FAssetData Asset = Registry.GetAssetByObjectPath(SoftPath);
        if (!Object || !Object->IsAsset() || !Asset.IsValid() || Asset.IsRedirector() ||
            Asset.GetObjectPathString() != Path || Object->GetPathName() != Path ||
            !Asset.GetOptionalOuterPathName().IsNone() ||
            Object->GetOutermost()->HasAnyPackageFlags(PKG_ContainsMap) || Object->GetOutermost()->IsDirty())
            return Refuse(Status::Rejected, TEXT("Require exact loaded, registered, clean, non-map assets without redirectors/external objects."));
        Assets.Add(Asset);
        HeldAssets.Emplace(Object);
    }
    if (ShouldCancel()) return Refuse(Status::Cancelled, TEXT("Cancelled before native validation."));
    FValidateAssetsSettings Settings;
    Settings.bCollectPerAssetDetails = true;
    // Required by the accepted consumer. Preflight has already refused unloaded/map/
    // external-object inputs. Do not silently relax that consumer to make tests pass.
    Settings.bLoadAssetsForValidation = true;
    Settings.bUnloadAssetsLoadedForValidation = false;
    Settings.bLoadExternalObjectsForValidation = true;
    Settings.bCaptureAssetLoadLogs = true;
    Settings.bCaptureLogsDuringValidation = true;
    Settings.bCaptureWarningsDuringValidationAsErrors = false;
    Settings.bSkipExcludedDirectories = false;
    Settings.bShowIfNoFailures = false;
    Settings.bValidateReferencersOfDeletedAssets = false;
    Settings.ValidationUsecase = EDataValidationUsecase::Script;
    Settings.MaxAssetsToValidate = Frozen.AssetObjectPaths.Num() + 1; // native equality also marks limit reached
    Settings.bSilent = true;
    Settings.ShowMessageLogSeverity.Reset(); // no automatic message-log window activation
    FValidateAssetsResults Results; // fresh for precisely this invocation
    const int32 NativeReturn = Subsystem->ValidateAssetsWithSettings(Assets, Settings, Results);
    const bool bCancelled = ShouldCancel();
    FDaedalusNativeValidationReply Reply = ProjectResult(
        Frozen.AssetObjectPaths, Settings, NativeReturn, Results, bCancelled, true);
    Reply.bNativeInvoked = true;
    Reply.NativeReturn = NativeReturn;
    Reply.bCancellationObserved = bCancelled;
    for (const auto& Held : HeldAssets)
    {
        if (Held->GetOutermost()->IsDirty())
        {
            Reply.Status = Status::Error;
            Reply.Diagnostic = TEXT("A validator dirtied a requested package; owner must reconcile, no save/rollback attempted.");
            break;
        }
    }
    Reply.bAccepted = Reply.Status == Status::Valid && !Reply.SnapshotJson.IsEmpty();
    return Reply;
}

FDaedalusNativeValidationReply FDaedalusNativeValidationBridge::ValidateNamedAssets(
    const FDaedalusNativeValidationRequest& Request)
{
    return ValidateWithCancellation(Request, [] { return GWarn && GWarn->ReceivedUserCancel(); });
}

FString FDaedalusNativeValidationBridge::SerializeReply(const FDaedalusNativeValidationReply& Reply)
{
    auto RefusalJson = [&Reply](const TCHAR* Reason)
    {
        const FString NativeReturn = Reply.bNativeInvoked ? FString::FromInt(Reply.NativeReturn) : TEXT("null");
        // Reasons here are source-controlled ASCII literals. Preserve invocation evidence
        // even if output serialization fails, so an automatic retry is never justified.
        return FString::Printf(TEXT("{\"status\":\"Error\",\"native_invoked\":%s,\"accepted\":false,\"cancellation_observed\":%s,\"native_return\":%s,\"diagnostic\":\"%s\",\"snapshot_json\":\"\"}"),
            Reply.bNativeInvoked ? TEXT("true") : TEXT("false"),
            Reply.bCancellationObserved ? TEXT("true") : TEXT("false"), *NativeReturn, Reason);
    };
    if (Reply.Diagnostic.Len() > MaxTextChars || Reply.SnapshotJson.Len() > MaxSnapshotBytes)
        return RefusalJson(TEXT("Reply exceeds envelope limits; canonical snapshot not truncated."));
    const FTCHARToUTF8 SnapshotBytes(*Reply.SnapshotJson, Reply.SnapshotJson.Len());
    if (SnapshotBytes.Length() > MaxSnapshotBytes)
        return RefusalJson(TEXT("Canonical snapshot exceeds byte cap; not truncated."));
    const TCHAR* Name = TEXT("Error");
    switch (Reply.Status)
    {
        case EDaedalusNativeValidationStatus::Rejected: Name = TEXT("Rejected"); break;
        case EDaedalusNativeValidationStatus::Cancelled: Name = TEXT("Cancelled"); break;
        case EDaedalusNativeValidationStatus::Error: break;
        case EDaedalusNativeValidationStatus::Incomplete: Name = TEXT("Incomplete"); break;
        case EDaedalusNativeValidationStatus::Invalid: Name = TEXT("Invalid"); break;
        case EDaedalusNativeValidationStatus::NotValidated: Name = TEXT("NotValidated"); break;
        case EDaedalusNativeValidationStatus::Skipped: Name = TEXT("Skipped"); break;
        case EDaedalusNativeValidationStatus::Warnings: Name = TEXT("Warnings"); break;
        case EDaedalusNativeValidationStatus::Valid: Name = TEXT("Valid"); break;
        default: return RefusalJson(TEXT("Unknown reply status."));
    }
    const TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
    Json->SetStringField(TEXT("status"), Name);
    Json->SetBoolField(TEXT("native_invoked"), Reply.bNativeInvoked);
    Json->SetBoolField(TEXT("accepted"), Reply.bAccepted && Reply.bNativeInvoked &&
        Reply.Status == EDaedalusNativeValidationStatus::Valid && !Reply.bCancellationObserved &&
        Reply.NativeReturn == 0 && !Reply.SnapshotJson.IsEmpty());
    Json->SetBoolField(TEXT("cancellation_observed"), Reply.bCancellationObserved);
    if (Reply.bNativeInvoked) Json->SetNumberField(TEXT("native_return"), Reply.NativeReturn);
    else Json->SetField(TEXT("native_return"), MakeShared<FJsonValueNull>());
    Json->SetStringField(TEXT("diagnostic"), Reply.Diagnostic);
    Json->SetStringField(TEXT("snapshot_json"), Reply.SnapshotJson);
    FString Out;
    if (!FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Out)))
        return RefusalJson(TEXT("Envelope serialization failed after known native state."));
    return Out;
}
#endif // WITH_EDITOR
