// SPDX-License-Identifier: MIT
// Daedalus2 tools/unreal_mcp/test_native_validation_result_snapshot.cpp
// Unreal automation tests for native_validation_result_snapshot.h.
// Status: AUTHORED_UNRUN. Needs an editor target with DataValidation + Json;
// that dependency closure, compilation and execution are separately pending.
// Exercises the actual typed serializer; never invokes validation.

#include "CoreMinimal.h"
#include "Misc/AutomationTest.h"
#include "native_validation_result_snapshot.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace
{
	using namespace DaedalusNativeValidationSnapshot;

	FValidateAssetsDetails CleanDetail(const TCHAR* Package, const TCHAR* Asset)
	{
		FValidateAssetsDetails D;
		D.PackageName = FName(Package);
		D.AssetName = FName(Asset);
		D.Result = EDataValidationResult::Valid;
		return D;
	}

	FValidateAssetsSettings CleanSettings(int32 MaxAssets)
	{
		FValidateAssetsSettings S;
		S.bLoadAssetsForValidation = true;
		S.bLoadExternalObjectsForValidation = false;
		S.bCollectPerAssetDetails = true;
		S.bCaptureAssetLoadLogs = true;
		S.bCaptureLogsDuringValidation = true;
		S.MaxAssetsToValidate = MaxAssets;
		return S;
	}

	FValidateAssetsResults CleanResults(const FString& Path)
	{
		FValidateAssetsResults R;
		R.NumRequested = 1;
		R.NumChecked = 1;
		R.NumValid = 1;
		R.AssetsDetails.Add(Path, CleanDetail(TEXT("/Game/Probe/BP_Probe"), TEXT("BP_Probe")));
		return R;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusValSnapCleanShape, "Daedalus.NativeValidationSnapshot.CleanShape",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusValSnapCleanShape::RunTest(const FString&)
{
	const FString Path = TEXT("/Game/Probe/BP_Probe.BP_Probe");
	TSharedPtr<FJsonObject> Snap; FString Error;
	TestTrue(TEXT("built"), BuildSnapshot({Path}, 0, CleanResults(Path), CleanSettings(2), FSnapshotBudget(), Snap, Error));
	if (!Snap.IsValid()) { return false; }
	TestEqual(TEXT("exactly four top-level members"), Snap->Values.Num(), 4);
	TestTrue(TEXT("requested_assets"), Snap->HasTypedField<EJson::Array>(TEXT("requested_assets")));
	TestEqual(TEXT("native_return"), static_cast<int32>(Snap->GetNumberField(TEXT("native_return"))), 0);
	const TSharedPtr<FJsonObject> R = Snap->GetObjectField(TEXT("results"));
	for (const TCHAR* F : {TEXT("NumRequested"), TEXT("NumExternalObjects"), TEXT("NumChecked"), TEXT("NumValid"),
		TEXT("NumInvalid"), TEXT("NumSkipped"), TEXT("NumWarnings"), TEXT("NumUnableToValidate")})
	{
		TestTrue(FString(F), R->HasTypedField<EJson::Number>(F));
	}
	TestFalse(TEXT("limit flag"), R->GetBoolField(TEXT("bAssetLimitReached")));
	TestEqual(TEXT("validator-wide messages empty"), R->GetArrayField(TEXT("ValidatorMessages")).Num(), 0);
	const TSharedPtr<FJsonObject> D = R->GetObjectField(TEXT("AssetsDetails"))->GetObjectField(Path);
	TestEqual(TEXT("PackageName"), D->GetStringField(TEXT("PackageName")), FString(TEXT("/Game/Probe/BP_Probe")));
	TestEqual(TEXT("AssetName"), D->GetStringField(TEXT("AssetName")), FString(TEXT("BP_Probe")));
	TestEqual(TEXT("Result"), D->GetStringField(TEXT("Result")), FString(TEXT("Valid")));
	const TSharedPtr<FJsonObject> S = Snap->GetObjectField(TEXT("settings"));
	TestEqual(TEXT("six settings"), S->Values.Num(), 6);
	TestEqual(TEXT("MaxAssets"), static_cast<int32>(S->GetNumberField(TEXT("MaxAssetsToValidate"))), 2);
	FString Json;
	TestTrue(TEXT("json"), ToJsonString(Snap, Json) && Json.StartsWith(TEXT("{")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusValSnapPreservesFailures, "Daedalus.NativeValidationSnapshot.PreservesFailures",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusValSnapPreservesFailures::RunTest(const FString&)
{
	const FString Path = TEXT("/Game/Probe/BP_Probe.BP_Probe");
	FValidateAssetsResults R = CleanResults(Path);
	R.NumValid = 0; R.NumInvalid = 1; R.NumWarnings = 1; R.NumExternalObjects = 1; R.bAssetLimitReached = true;
	FValidateAssetsDetails& D = R.AssetsDetails[Path];
	D.Result = EDataValidationResult::Invalid;
	D.ValidationErrors = {FText::FromString(TEXT("e1")), FText::FromString(TEXT("e2"))};
	D.ValidationWarnings = {FText::FromString(TEXT("w1"))};
	D.ValidationMessages.Add(FTokenizedMessage::Create(EMessageSeverity::Error, FText::FromString(TEXT("m1"))));
	FValidateAssetsExternalObject Ext; Ext.PackageName = FName(TEXT("/Game/__External__/X")); Ext.AssetName = FName(TEXT("X"));
	D.ExternalObjects.Add(Ext);
	R.ValidatorMessages.Add(FTokenizedMessage::Create(EMessageSeverity::Warning, FText::FromString(TEXT("vw"))));

	TSharedPtr<FJsonObject> Snap; FString Error;
	// Native return 2 == warnings + invalid; deliberately preserved, not judged.
	TestTrue(TEXT("built"), BuildSnapshot({Path}, 2, R, CleanSettings(1), FSnapshotBudget(), Snap, Error));
	if (!Snap.IsValid()) { return false; }
	const TSharedPtr<FJsonObject> RO = Snap->GetObjectField(TEXT("results"));
	TestEqual(TEXT("NumInvalid kept"), static_cast<int32>(RO->GetNumberField(TEXT("NumInvalid"))), 1);
	TestTrue(TEXT("limit kept"), RO->GetBoolField(TEXT("bAssetLimitReached")));
	const TSharedPtr<FJsonObject> DO = RO->GetObjectField(TEXT("AssetsDetails"))->GetObjectField(Path);
	TestEqual(TEXT("Result Invalid"), DO->GetStringField(TEXT("Result")), FString(TEXT("Invalid")));
	TestEqual(TEXT("both errors"), DO->GetArrayField(TEXT("ValidationErrors")).Num(), 2);
	TestEqual(TEXT("warning"), DO->GetArrayField(TEXT("ValidationWarnings")).Num(), 1);
	const TSharedPtr<FJsonObject> M = DO->GetArrayField(TEXT("ValidationMessages"))[0]->AsObject();
	TestEqual(TEXT("severity"), M->GetStringField(TEXT("Severity")), FString(TEXT("Error")));
	TestTrue(TEXT("text kept"), M->GetStringField(TEXT("Text")).Contains(TEXT("m1")));
	TestEqual(TEXT("external"), DO->GetArrayField(TEXT("ExternalObjects"))[0]->AsObject()->GetStringField(TEXT("AssetName")), FString(TEXT("X")));
	TestEqual(TEXT("validator-wide"), RO->GetArrayField(TEXT("ValidatorMessages")).Num(), 1);
	TestEqual(TEXT("native_return kept"), static_cast<int32>(Snap->GetNumberField(TEXT("native_return"))), 2);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusValSnapRefusals, "Daedalus.NativeValidationSnapshot.Refusals",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDaedalusValSnapRefusals::RunTest(const FString&)
{
	const FString Path = TEXT("/Game/Probe/BP_Probe.BP_Probe");
	TSharedPtr<FJsonObject> Snap; FString Error;

	FValidateAssetsResults Unknown = CleanResults(Path);
	Unknown.AssetsDetails[Path].Result = static_cast<EDataValidationResult>(0x7F);
	TestFalse(TEXT("unknown enum refused"), BuildSnapshot({Path}, 0, Unknown, CleanSettings(2), FSnapshotBudget(), Snap, Error));
	TestFalse(TEXT("no snapshot on refusal"), Snap.IsValid());

	TestFalse(TEXT("duplicate refused"), BuildSnapshot({Path, Path}, 0, CleanResults(Path), CleanSettings(3), FSnapshotBudget(), Snap, Error));

	FValidateAssetsResults Big = CleanResults(Path);
	for (int32 i = 0; i < 5; ++i) { Big.AssetsDetails[Path].ValidationErrors.Add(FText::FromString(TEXT("e"))); }
	FSnapshotBudget Tight; Tight.MaxDiagnosticItems = 4;
	TestFalse(TEXT("item overflow refused, not truncated"), BuildSnapshot({Path}, 0, Big, CleanSettings(2), Tight, Snap, Error));
	TestTrue(TEXT("overflow reason"), Error.Contains(TEXT("budget")));
	FSnapshotBudget TightChars; TightChars.MaxDiagnosticChars = 3;
	TestFalse(TEXT("char overflow refused"), BuildSnapshot({Path}, 0, Big, CleanSettings(2), TightChars, Snap, Error));
	FSnapshotBudget TightReq; TightReq.MaxRequestedAssets = 0;
	TestFalse(TEXT("request overflow refused"), BuildSnapshot({Path}, 0, CleanResults(Path), CleanSettings(2), TightReq, Snap, Error));
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS
