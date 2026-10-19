// SPDX-License-Identifier: MIT
// Daedalus2 tools/unreal_mcp/native_validation_result_snapshot.h
//
// Typed, data-only projection of UE 5.8 DataValidation results into the exact
// four-argument snapshot consumed by tools/unreal_mcp/validation_result_contract.py
// (evaluate_native_validation(requested_assets, native_return, results, settings),
// consumer sha256 af87e5319cf0e4ad9404c6b0099bca02c7067ffa38c02079f8d430c6bcd7d69e).
//
// Source read (not compiled here): Engine/Plugins/Editor/DataValidation/Source/
// DataValidation/Public/EditorValidatorSubsystem.h, sha256
// 463558fd5bc145575def4caa75eb22d49a1c06dab7e1e0b927dd9781fc058174.
//
// WHAT THIS IS
//   * An explicit consumer-contract projection. It is NOT a lossless serialization
//     of every native struct member: ValidatorStatistics, bSkipExcludedDirectories,
//     ValidationUsecase, bUnloadAssetsLoadedForValidation,
//     bCaptureWarningsDuringValidationAsErrors, bValidateReferencersOfDeletedAssets,
//     ShowMessageLogSeverity, MessageLog* and bSilent are intentionally omitted.
//   * Reflection note: FValidateAssetsResults::AssetsDetails (the map) IS a
//     UPROPERTY; the FValidateAssetsDetails members and the validator-wide
//     ValidatorMessages are NOT. So this is manual JSON, never reflection-only
//     JsonUtilities.
//   * Tokenized messages are flattened to {Severity, SeverityValue, Text} where
//     Text is FTokenizedMessage::ToText(). No rich-token equivalence is claimed.
//
// WHAT THIS IS NOT
//   * It never invokes validation, never looks up UEditorValidatorSubsystem, never
//     touches GEditor, adds no endpoint/transport, and edits no module.
//   * A syntactically valid snapshot cannot prove fresh OutResults, that a native
//     invocation happened, or runtime qualification. Those stay caller obligations.
//   * Not compiled or run: DataValidation + Json are outside the qualified
//     dependency closure. Status: SOURCE_ONLY, tests AUTHORED_UNRUN.
//
// RULES
//   * Inputs are const typed native structs, the requested object paths, and the
//     actual int32 returned by ValidateAssetsWithSettings. Nothing is normalized:
//     counts, the native return, bAssetLimitReached and every diagnostic item are
//     copied as-is, including non-passing and inconsistent values.
//   * Unknown EDataValidationResult values are refused (never rewritten as Valid).
//   * Budget overflow is refused; diagnostics are never truncated into a snapshot.
#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "EditorValidatorSubsystem.h"
#include "Logging/TokenizedMessage.h"
#include "Misc/DataValidation.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace DaedalusNativeValidationSnapshot
{
	static constexpr const TCHAR* SnapshotKind = TEXT("explicit_native_members_not_mcp_schema");
	static constexpr const TCHAR* ProjectionKind = TEXT("consumer_contract_projection_not_lossless");
	static constexpr const TCHAR* ConsumerSha256 = TEXT("af87e5319cf0e4ad9404c6b0099bca02c7067ffa38c02079f8d430c6bcd7d69e");
	static constexpr const TCHAR* HeaderSha256 = TEXT("463558fd5bc145575def4caa75eb22d49a1c06dab7e1e0b927dd9781fc058174");
	static constexpr bool bNativeRuntimeQualified = false;
	static constexpr bool bTestsRun = false; // AUTHORED_UNRUN

	/** Hard ceilings. Exceeding any of them refuses the whole snapshot. */
	struct FSnapshotBudget
	{
		int32 MaxRequestedAssets = 4096;
		int32 MaxDetails = 4096;
		/** Total diagnostic items: errors + warnings + messages + externals + validator-wide messages. */
		int32 MaxDiagnosticItems = 65536;
		/** Total characters across all diagnostic strings. */
		int64 MaxDiagnosticChars = 8 * 1024 * 1024;
	};

	/** Explicit enum mapping. Returns false for any value outside Valid/Invalid/NotValidated. */
	inline bool ResultName(EDataValidationResult Result, FString& OutName)
	{
		switch (Result)
		{
		case EDataValidationResult::Valid: OutName = TEXT("Valid"); return true;
		case EDataValidationResult::Invalid: OutName = TEXT("Invalid"); return true;
		case EDataValidationResult::NotValidated: OutName = TEXT("NotValidated"); return true;
		default: OutName.Reset(); return false;
		}
	}

	/** Severity names; unknown values stay honest as "Unknown" with the raw value kept. */
	inline FString SeverityName(EMessageSeverity::Type Severity)
	{
		switch (Severity)
		{
		case EMessageSeverity::Error: return TEXT("Error");
		case EMessageSeverity::PerformanceWarning: return TEXT("PerformanceWarning");
		case EMessageSeverity::Warning: return TEXT("Warning");
		case EMessageSeverity::Info: return TEXT("Info");
		default: return TEXT("Unknown");
		}
	}

	namespace Private
	{
		struct FBudgetMeter
		{
			const FSnapshotBudget& Budget;
			int32 Items = 0;
			int64 Chars = 0;
			FString Error;

			bool Spend(const FString& Text)
			{
				++Items;
				Chars += Text.Len();
				if (Items > Budget.MaxDiagnosticItems)
				{
					Error = TEXT("diagnostic item budget exceeded; refusing instead of truncating");
					return false;
				}
				if (Chars > Budget.MaxDiagnosticChars)
				{
					Error = TEXT("diagnostic character budget exceeded; refusing instead of truncating");
					return false;
				}
				return true;
			}
		};

		inline bool AddTexts(const TArray<FText>& Texts, FBudgetMeter& Meter, TArray<TSharedPtr<FJsonValue>>& Out)
		{
			Out.Reset(Texts.Num());
			for (const FText& Text : Texts)
			{
				const FString S = Text.ToString();
				if (!Meter.Spend(S)) { return false; }
				Out.Add(MakeShared<FJsonValueString>(S));
			}
			return true;
		}

		inline bool AddMessages(const TArray<TSharedRef<FTokenizedMessage>>& Messages, FBudgetMeter& Meter, TArray<TSharedPtr<FJsonValue>>& Out)
		{
			Out.Reset(Messages.Num());
			for (const TSharedRef<FTokenizedMessage>& Message : Messages)
			{
				const FString S = Message->ToText().ToString();
				if (!Meter.Spend(S)) { return false; }
				const EMessageSeverity::Type Severity = Message->GetSeverity();
				TSharedRef<FJsonObject> Obj = MakeShared<FJsonObject>();
				Obj->SetStringField(TEXT("Severity"), SeverityName(Severity));
				Obj->SetNumberField(TEXT("SeverityValue"), static_cast<int32>(Severity));
				Obj->SetStringField(TEXT("Text"), S);
				Out.Add(MakeShared<FJsonValueObject>(Obj));
			}
			return true;
		}
	}

	/**
	 * Build the four-member snapshot {requested_assets, native_return, results, settings}.
	 * Returns false (OutSnapshot reset, OutError set) on unknown enum, duplicate or
	 * oversize requests, or budget overflow. Never invokes validation.
	 */
	inline bool BuildSnapshot(
		const TArray<FString>& RequestedAssets,
		const int32 NativeReturn,
		const FValidateAssetsResults& Results,
		const FValidateAssetsSettings& Settings,
		const FSnapshotBudget& Budget,
		TSharedPtr<FJsonObject>& OutSnapshot,
		FString& OutError)
	{
		OutSnapshot.Reset();
		OutError.Reset();

		if (RequestedAssets.Num() > Budget.MaxRequestedAssets)
		{
			OutError = TEXT("requested asset budget exceeded; refusing instead of truncating");
			return false;
		}
		if (Results.AssetsDetails.Num() > Budget.MaxDetails)
		{
			OutError = TEXT("AssetsDetails budget exceeded; refusing instead of truncating");
			return false;
		}

		TSet<FString> Seen;
		TArray<TSharedPtr<FJsonValue>> Requested;
		for (const FString& Path : RequestedAssets)
		{
			bool bAlready = false;
			Seen.Add(Path, &bAlready);
			if (bAlready)
			{
				OutError = FString::Printf(TEXT("duplicate requested asset: %s"), *Path);
				return false;
			}
			Requested.Add(MakeShared<FJsonValueString>(Path));
		}

		Private::FBudgetMeter Meter{Budget};

		TSharedRef<FJsonObject> Details = MakeShared<FJsonObject>();
		for (const TPair<FString, FValidateAssetsDetails>& Pair : Results.AssetsDetails)
		{
			const FValidateAssetsDetails& D = Pair.Value;
			FString Result;
			if (!ResultName(D.Result, Result))
			{
				OutError = FString::Printf(TEXT("unknown EDataValidationResult %d for %s; refusing"), static_cast<int32>(D.Result), *Pair.Key);
				return false;
			}
			TSharedRef<FJsonObject> Obj = MakeShared<FJsonObject>();
			Obj->SetStringField(TEXT("PackageName"), D.PackageName.ToString());
			Obj->SetStringField(TEXT("AssetName"), D.AssetName.ToString());
			Obj->SetStringField(TEXT("Result"), Result);

			TArray<TSharedPtr<FJsonValue>> Errors, Warnings, Messages, Externals;
			if (!Private::AddTexts(D.ValidationErrors, Meter, Errors)
				|| !Private::AddTexts(D.ValidationWarnings, Meter, Warnings)
				|| !Private::AddMessages(D.ValidationMessages, Meter, Messages))
			{
				OutError = Meter.Error;
				return false;
			}
			for (const FValidateAssetsExternalObject& Ext : D.ExternalObjects)
			{
				const FString Package = Ext.PackageName.ToString();
				const FString Asset = Ext.AssetName.ToString();
				if (!Meter.Spend(Package + Asset)) { OutError = Meter.Error; return false; }
				TSharedRef<FJsonObject> E = MakeShared<FJsonObject>();
				E->SetStringField(TEXT("PackageName"), Package);
				E->SetStringField(TEXT("AssetName"), Asset);
				Externals.Add(MakeShared<FJsonValueObject>(E));
			}
			Obj->SetArrayField(TEXT("ValidationErrors"), Errors);
			Obj->SetArrayField(TEXT("ValidationWarnings"), Warnings);
			Obj->SetArrayField(TEXT("ValidationMessages"), Messages);
			Obj->SetArrayField(TEXT("ExternalObjects"), Externals);
			// Exact object-path key from the native map; never substituted.
			Details->SetObjectField(Pair.Key, Obj);
		}

		TArray<TSharedPtr<FJsonValue>> ValidatorMessages;
		if (!Private::AddMessages(Results.ValidatorMessages, Meter, ValidatorMessages))
		{
			OutError = Meter.Error;
			return false;
		}

		TSharedRef<FJsonObject> ResultsObj = MakeShared<FJsonObject>();
		ResultsObj->SetNumberField(TEXT("NumRequested"), Results.NumRequested);
		ResultsObj->SetNumberField(TEXT("NumExternalObjects"), Results.NumExternalObjects);
		ResultsObj->SetNumberField(TEXT("NumChecked"), Results.NumChecked);
		ResultsObj->SetNumberField(TEXT("NumValid"), Results.NumValid);
		ResultsObj->SetNumberField(TEXT("NumInvalid"), Results.NumInvalid);
		ResultsObj->SetNumberField(TEXT("NumSkipped"), Results.NumSkipped);
		ResultsObj->SetNumberField(TEXT("NumWarnings"), Results.NumWarnings);
		ResultsObj->SetNumberField(TEXT("NumUnableToValidate"), Results.NumUnableToValidate);
		ResultsObj->SetBoolField(TEXT("bAssetLimitReached"), Results.bAssetLimitReached);
		ResultsObj->SetObjectField(TEXT("AssetsDetails"), Details);
		ResultsObj->SetArrayField(TEXT("ValidatorMessages"), ValidatorMessages);

		TSharedRef<FJsonObject> SettingsObj = MakeShared<FJsonObject>();
		SettingsObj->SetBoolField(TEXT("bLoadAssetsForValidation"), Settings.bLoadAssetsForValidation);
		SettingsObj->SetBoolField(TEXT("bLoadExternalObjectsForValidation"), Settings.bLoadExternalObjectsForValidation);
		SettingsObj->SetBoolField(TEXT("bCollectPerAssetDetails"), Settings.bCollectPerAssetDetails);
		SettingsObj->SetBoolField(TEXT("bCaptureAssetLoadLogs"), Settings.bCaptureAssetLoadLogs);
		SettingsObj->SetBoolField(TEXT("bCaptureLogsDuringValidation"), Settings.bCaptureLogsDuringValidation);
		SettingsObj->SetNumberField(TEXT("MaxAssetsToValidate"), Settings.MaxAssetsToValidate);

		TSharedRef<FJsonObject> Snapshot = MakeShared<FJsonObject>();
		Snapshot->SetArrayField(TEXT("requested_assets"), Requested);
		Snapshot->SetNumberField(TEXT("native_return"), NativeReturn);
		Snapshot->SetObjectField(TEXT("results"), ResultsObj);
		Snapshot->SetObjectField(TEXT("settings"), SettingsObj);
		OutSnapshot = Snapshot;
		return true;
	}

	/** Condensed JSON text of a built snapshot. */
	inline bool ToJsonString(const TSharedPtr<FJsonObject>& Snapshot, FString& OutJson)
	{
		OutJson.Reset();
		if (!Snapshot.IsValid()) { return false; }
		TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer =
			TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&OutJson);
		return FJsonSerializer::Serialize(Snapshot.ToSharedRef(), Writer);
	}
}
