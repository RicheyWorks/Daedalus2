// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"

#if WITH_EDITOR
struct FValidateAssetsSettings;
struct FValidateAssetsResults;

enum class EDaedalusNativeValidationStatus : uint8
{
    Rejected, Cancelled, Error, Incomplete, Invalid, NotValidated, Skipped, Warnings, Valid
};

struct DAEDALUSLINK_API FDaedalusNativeValidationRequest
{
    TArray<FString> AssetObjectPaths;
    // Exact owner-approved subtree, e.g. /Game/CodexToolEvaluation/MyRun; not /Game.
    FString AllowedPackageRoot;
    bool bCancelRequested = false;
};

struct DAEDALUSLINK_API FDaedalusNativeValidationReply
{
    EDaedalusNativeValidationStatus Status = EDaedalusNativeValidationStatus::Rejected;
    bool bNativeInvoked = false;
    bool bAccepted = false;
    bool bCancellationObserved = false;
    int32 NativeReturn = -1;
    FString Diagnostic;
    // Exact canonical serializer output, never partial JSON. Empty before invocation
    // or on output refusal; the envelope below still carries the actionable outcome.
    FString SnapshotJson;
};

/**
 * Editor-only synchronous binding. Sole native owner supplies reflected wrappers,
 * editor-only DataValidation/UnrealEd dependencies and the canonical serializer include.
 * No endpoint, module/startup hook, scan, direct load/save or validator registration.
 * Only 1..16 explicit loaded, registered, clean, non-map assets are eligible.
 * Engine validators/delegates can perform their own work; this is not a hard timeout,
 * a sandbox for arbitrary validators, or a guarantee of globally side-effect-free work.
 * Caller owns the explicit fixture namespace, resource admission and preservation.
 * Native compilation/automation remain authored and UNRUN in this source delivery.
 */
class DAEDALUSLINK_API FDaedalusNativeValidationBridge
{
public:
    static constexpr int32 MaxNamedAssets = 16;
    static constexpr int32 MaxPathChars = 1024;

    static FDaedalusNativeValidationReply ValidateNamedAssets(
        const FDaedalusNativeValidationRequest& Request);

    // Envelope keys: status, native_invoked, accepted, cancellation_observed,
    // native_return (null before invocation), diagnostic, snapshot_json.
    // snapshot_json is an unchanged string for the existing snapshot consumer.
    static FString SerializeReply(const FDaedalusNativeValidationReply& Reply);

    static bool CheckRequest(const FDaedalusNativeValidationRequest& Request, FString& Why);

    // Checked before and after the synchronous call; cannot preempt a validator.
    // Callback must be read-only and is never retained. Nested calls are refused.
    static FDaedalusNativeValidationReply ValidateWithCancellation(
        const FDaedalusNativeValidationRequest& Request, TFunctionRef<bool()> ShouldCancel);

    // Native-struct projection for automation. It does NOT attest a real invocation:
    // bNativeInvoked/bAccepted stay false; only ValidateWithCancellation sets them.
    static FDaedalusNativeValidationReply ProjectNativeResult(
        const TArray<FString>& RequestedPaths, const FValidateAssetsSettings& Settings,
        int32 NativeReturn, const FValidateAssetsResults& Results, bool bCancelled);
};
#endif // WITH_EDITOR
