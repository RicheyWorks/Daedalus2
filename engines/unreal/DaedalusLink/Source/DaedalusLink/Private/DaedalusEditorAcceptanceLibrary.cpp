// SPDX-License-Identifier: MIT
#include "DaedalusEditorAcceptanceLibrary.h"

#if WITH_EDITOR
#include "DaedalusNativeValidationBridge.h"
#include "DaedalusSlateAcceptanceBridge.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Misc/DataValidation.h"

EDataValidationResult UDaedalusAcceptanceValidationFixture::IsDataValid(FDataValidationContext& Context) const
{
	if (!GetPathName().StartsWith(TEXT("/Game/CodexToolEvaluation/EpicIntegrationR1/Validation/")))
	{
		return EDataValidationResult::NotValidated;
	}
	switch (Outcome)
	{
	case EDaedalusAcceptanceValidationOutcome::Valid:
		return EDataValidationResult::Valid;
	case EDaedalusAcceptanceValidationOutcome::Invalid:
		Context.AddError(FText::FromString(TEXT("Owned acceptance fixture intentionally requires repair.")));
		return EDataValidationResult::Invalid;
	default:
		return EDataValidationResult::NotValidated;
	}
}
#endif

FString UDaedalusEditorAcceptanceLibrary::ValidateNamedAssets(
	const TArray<FString>& AssetObjectPaths, const FString& AllowedPackageRoot, bool bCancelRequested)
{
#if WITH_EDITOR
	FDaedalusNativeValidationRequest Request;
	Request.AssetObjectPaths = AssetObjectPaths;
	Request.AllowedPackageRoot = AllowedPackageRoot;
	Request.bCancelRequested = bCancelRequested;
	return FDaedalusNativeValidationBridge::SerializeReply(
		FDaedalusNativeValidationBridge::ValidateNamedAssets(Request));
#else
	return TEXT("{\"status\":\"Rejected\",\"native_invoked\":false,\"accepted\":false,\"cancellation_observed\":false,\"native_return\":null,\"diagnostic\":\"Editor-only acceptance entry point\",\"snapshot_json\":\"\"}");
#endif
}

FString UDaedalusEditorAcceptanceLibrary::RunSlateButtonFixture()
{
#if WITH_EDITOR
	const FDaedalusSlateAcceptanceResult Result = FDaedalusSlateAcceptanceBridge::RunButtonFixture();
	TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
	Json->SetStringField(TEXT("scope"), TEXT("disposable_virtual_slate_button"));
	Json->SetBoolField(TEXT("ran"), Result.bRan);
	Json->SetBoolField(TEXT("detached_widget_rejected"), Result.bDetachedWidgetRejected);
	Json->SetBoolField(TEXT("wrong_button_rejected"), Result.bWrongButtonRejected);
	Json->SetBoolField(TEXT("disabled_button_rejected"), Result.bDisabledButtonRejected);
	Json->SetBoolField(TEXT("enabled_click_handled"), Result.bEnabledClickHandled);
	Json->SetBoolField(TEXT("virtual_focus_preserved"), Result.bVirtualFocusPreserved);
	Json->SetBoolField(TEXT("button_released"), Result.bButtonReleased);
	Json->SetBoolField(TEXT("keyboard_focus_preserved"), Result.bKeyboardFocusPreserved);
	Json->SetBoolField(TEXT("active_window_preserved"), Result.bActiveWindowPreserved);
	Json->SetBoolField(TEXT("virtual_user_released"), Result.bVirtualUserReleased);
	Json->SetBoolField(TEXT("window_unregister_called"), Result.bWindowUnregisterCalled);
	Json->SetBoolField(TEXT("owned_content_detached"), Result.bOwnedContentDetached);
	Json->SetNumberField(TEXT("click_count"), Result.ClickCount);
	Json->SetStringField(TEXT("failure_reason"), Result.FailureReason);
	Json->SetBoolField(TEXT("passed"), Result.Passed());
	Json->SetBoolField(TEXT("production_ui_accepted"), false);
	FString Serialized;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Serialized);
	if (!FJsonSerializer::Serialize(Json, Writer))
	{
		return TEXT("{\"ran\":false,\"passed\":false,\"failure_reason\":\"Receipt serialization failed\"}");
	}
	return Serialized;
#else
	return TEXT("{\"ran\":false,\"passed\":false,\"failure_reason\":\"Editor-only acceptance entry point\"}");
#endif
}
