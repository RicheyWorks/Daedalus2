// SPDX-License-Identifier: MIT
#include "DaedalusEditorAcceptanceLibrary.h"

#if WITH_EDITOR
#include "DaedalusNativeValidationBridge.h"
#include "DaedalusSlateAcceptanceBridge.h"
#include "DaedalusLegacyHlodClosure.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Misc/DataValidation.h"
#include "Editor.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "Framework/Docking/TabManager.h"
#include "HAL/PlatformProcess.h"
#include "LevelEditor.h"
#include "Modules/ModuleManager.h"
#include "SlateInspectorToolsetRefCache.h"
#include "Widgets/Docking/SDockTab.h"

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

FString UDaedalusEditorAcceptanceLibrary::BindExistingDetailsPanel()
{
#if WITH_EDITOR
	const auto Reject = [](const TCHAR* Why)
	{
		TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
		Json->SetStringField(TEXT("scope"), TEXT("existing_primary_level_editor_details"));
		Json->SetStringField(TEXT("status"), TEXT("Rejected"));
		Json->SetBoolField(TEXT("bound"), false);
		Json->SetStringField(TEXT("approved_ref"), TEXT(""));
		Json->SetStringField(TEXT("diagnostic"), Why);
		FString Text;
		FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text));
		return Text;
	};
	if (!IsInGameThread() || !GEditor || GEditor->PlayWorld
		|| !GEditor->GetEditorWorldContext().World() || !FSlateApplication::IsInitialized())
	{
		return Reject(TEXT("Requires the current editor game thread, editor world and no PIE."));
	}
	FLevelEditorModule* LevelEditor = FModuleManager::GetModulePtr<FLevelEditorModule>(TEXT("LevelEditor"));
	if (!LevelEditor || !FModuleManager::Get().IsModuleLoaded(TEXT("SlateInspectorToolset")))
	{
		return Reject(TEXT("Required existing LevelEditor/SlateInspectorToolset modules are not loaded; no fallback load."));
	}
	const TSharedPtr<FTabManager> Manager = LevelEditor->GetLevelEditorTabManager();
	if (!Manager.IsValid())
	{
		return Reject(TEXT("The owning level-editor tab manager is unavailable."));
	}
	const TSharedPtr<SDockTab> Tab = Manager->FindExistingLiveTab(FTabId(LevelEditorTabIds::LevelEditorSelectionDetails));
	const TSharedPtr<SDockTab> Owner = Manager->GetOwnerTab();
	if (!Tab.IsValid() || !Owner.IsValid() || Owner != LevelEditor->GetLevelEditorTab()
		|| Tab->GetTabManagerPtr() != Manager
		|| Tab->GetLayoutIdentifier().TabType != LevelEditorTabIds::LevelEditorSelectionDetails)
	{
		return Reject(TEXT("The exact existing primary Details tab and owning manager could not be verified."));
	}
	const TSharedRef<SWidget> Panel = Tab->GetContent();
	FSlateApplication& App = FSlateApplication::Get();
	const TSharedPtr<SWindow> PanelWindow = App.FindWidgetWindow(Panel);
	const TSharedPtr<SWindow> OwnerWindow = App.FindWidgetWindow(Owner.ToSharedRef());
	// FindExistingLiveTab can also return retained hidden drawer/sidebar tabs,
	// and IsForeground is true without a tab-well parent. Admit a normal docked
	// panel only, then verify its entire live parent chain to the owning window.
	if (!Tab->GetParent().IsValid() || !Tab->GetParentDockTabStack().IsValid() || Tab->IsInSidebar()
		|| !Tab->IsForeground() || !Tab->GetVisibility().IsVisible() || !Panel->GetVisibility().IsVisible()
		|| !Panel->GetParentWidget().IsValid() || !PanelWindow.IsValid()
		|| PanelWindow != OwnerWindow || !PanelWindow->IsVisible())
	{
		return Reject(TEXT("The exact Details content must already be visible and foreground in its owning editor window."));
	}
	TSharedPtr<SWidget> Ancestor = Panel;
	bool bReachedOwnWindow = false;
	for (int32 Depth = 0; Depth < 64 && Ancestor.IsValid(); ++Depth)
	{
		if (!Ancestor->GetVisibility().IsVisible())
		{
			return Reject(TEXT("The Details content has a hidden or collapsed ancestor."));
		}
		if (Ancestor == PanelWindow)
		{
			bReachedOwnWindow = true;
			break;
		}
		Ancestor = Ancestor->GetParentWidget();
	}
	const auto PanelSize = Panel->GetCachedGeometry().GetLocalSize();
	if (!bReachedOwnWindow || !FMath::IsFinite(PanelSize.X) || !FMath::IsFinite(PanelSize.Y)
		|| PanelSize.X <= 0 || PanelSize.Y <= 0)
	{
		return Reject(TEXT("The Details panel has no bounded visible ancestor path and positive laid-out area."));
	}
	const TSharedPtr<SWidget> KeyboardFocus = App.GetKeyboardFocusedWidget();
	const TSharedPtr<SWindow> ActiveWindow = App.GetActiveTopLevelWindow();
	// This exported accessor is the same singleton used by official Snapshot's
	// ResolveRefOrWarn. Never instantiate/copy/reset a private cache or traverse
	// another panel to bootstrap a ref.
	FSlateInspectorToolsetRefCache& Cache = FSlateInspectorToolsetRefCache::Get();
	const bool bPreexisting = !Cache.FindRef(Panel).IsEmpty();
	const FString Ref = Cache.GetOrAssignRef(Panel, TEXT("panel"));
	if (Ref.IsEmpty() || Cache.ResolveRef(Ref) != Panel
		|| App.GetKeyboardFocusedWidget() != KeyboardFocus || App.GetActiveTopLevelWindow() != ActiveWindow)
	{
		return Reject(TEXT("Shared-cache identity or untouched focus/window readback failed."));
	}
	TSharedRef<FJsonObject> Json = MakeShared<FJsonObject>();
	Json->SetStringField(TEXT("scope"), TEXT("existing_primary_level_editor_details"));
	Json->SetStringField(TEXT("status"), TEXT("Bound"));
	Json->SetBoolField(TEXT("bound"), true);
	Json->SetStringField(TEXT("approved_ref"), Ref);
	Json->SetNumberField(TEXT("process_id"), FPlatformProcess::GetCurrentProcessId());
	Json->SetStringField(TEXT("world"), GEditor->GetEditorWorldContext().World()->GetPathName());
	Json->SetStringField(TEXT("tab_id"), LevelEditorTabIds::LevelEditorSelectionDetails.ToString());
	Json->SetStringField(TEXT("tab_label"), Tab->GetTabLabel().ToString());
	Json->SetStringField(TEXT("panel_type"), Panel->GetTypeAsString());
	Json->SetStringField(TEXT("window_title"), PanelWindow->GetTitle().ToString());
	for (const TCHAR* Field : {TEXT("owning_manager_agrees"), TEXT("window_identity_agrees"),
		TEXT("panel_visible"), TEXT("tab_foreground"), TEXT("window_visible"),
		TEXT("cache_roundtrip"), TEXT("keyboard_focus_preserved"), TEXT("active_window_preserved")})
	{
		Json->SetBoolField(Field, true);
	}
	Json->SetBoolField(TEXT("ref_preexisting"), bPreexisting);
	Json->SetStringField(TEXT("diagnostic"), TEXT(""));
	FString Text;
	if (!FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Text)))
	{
		return Reject(TEXT("Binding receipt serialization failed."));
	}
	return Text;
#else
	return TEXT("{\"scope\":\"existing_primary_level_editor_details\",\"status\":\"Rejected\",\"bound\":false,\"approved_ref\":\"\",\"diagnostic\":\"Editor only\"}");
#endif
}


FString UDaedalusEditorAcceptanceLibrary::ReadLegacyHlodClosure(const FString& LodActorObjectPath)
{
#if WITH_EDITOR
    UWorld* CurrentWorld = nullptr;
    if (IsInGameThread() && GEditor && !GEditor->PlayWorld)
        CurrentWorld = GEditor->GetEditorWorldContext().World();
    return DaedalusLegacyHlod::ReadLoadedClosureJson(CurrentWorld, LodActorObjectPath);
#else
    return TEXT("{\"schema\":\"daedalus.legacy_hlod_closure.v1\",\"state\":\"HELD\",\"reason\":\"Editor-only closure read\",\"read_only\":true,\"loaded_inventory_complete\":false,\"build_admitted\":false,\"serialization_complete\":false,\"truncated\":false}");
#endif
}
