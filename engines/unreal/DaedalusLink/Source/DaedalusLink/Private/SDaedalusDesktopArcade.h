// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "DaedalusDesktopArcade.h"
#include "Widgets/Input/SComboBox.h"
#include "Widgets/SCompoundWidget.h"

/** Standalone presentation/input host. The actor owns the portable Driver, persistence and pause lease. */
class SDaedalusDesktopArcade : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SDaedalusDesktopArcade) {}
		SLATE_ARGUMENT(TWeakObjectPtr<ADaedalusDesktopArcade>, Game)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);
	/** Foreground viewport host, clipped and hit-tested for the opening local player. */
	static TSharedRef<SWidget> MakeForegroundHost(ULocalPlayer* Player, UGameViewportClient* Viewport, const TSharedRef<SWidget>& Content);
	virtual ~SDaedalusDesktopArcade() override;
	virtual bool SupportsKeyboardFocus() const override { return true; }
	virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
	virtual FReply OnKeyUp(const FGeometry& Geometry, const FKeyEvent& Event) override;
	virtual FReply OnAnalogValueChanged(const FGeometry& Geometry, const FAnalogInputEvent& Event) override;
	virtual FReply OnMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event) override;
	virtual FNavigationReply OnNavigation(const FGeometry& Geometry, const FNavigationEvent& Event) override;
	virtual void OnFocusLost(const FFocusEvent& Event) override;
	virtual void OnFocusChanging(const FWeakWidgetPath& Previous, const FWidgetPath& Next, const FFocusEvent& Event) override;
	void ResetHeldInput();
	bool OwnsUserFocus(int32 UserIndex) const;

private:
	bool CoreTick(float DeltaSeconds);
	void PushInput(const FKey& PressedKey = FKey());
	void SuspendForFocusLoss();
	void SyncSelection();
	void ResetCatalogChoice();
	bool CanSwitchGame() const;
	FReply BrowseCatalog();
	FReply SwitchGame();
	FReply KeepPlaying();
	void FocusGame();
	FReply FocusReply();
	FText CurrentTitle() const;
	FText CatalogTitle() const;
	FText CatalogNoticeText() const;
	FText StatusText() const;
	FText ControlText() const;
	FText LeaderboardText() const;
	EVisibility StarVisibility() const;
	EVisibility MinesweeperVisibility() const;
	EVisibility LeaderboardVisibility() const;
	TSharedRef<SWidget> MakeGameRow(TSharedPtr<FString> Item) const;
	void SelectCatalogChoice(TSharedPtr<FString> Item, ESelectInfo::Type Selection);
	TSharedRef<SWidget> MakeAction(const TCHAR* Label, FSimpleDelegate Action, bool bReplacesRun = false, bool bFocusable = false);

	TWeakObjectPtr<ADaedalusDesktopArcade> Game;
	FTSTicker::FDelegateHandle CoreTickHandle;
	TSharedPtr<SComboBox<TSharedPtr<FString>>> CatalogSelector;
	TArray<TSharedPtr<FString>> GameItems;
	TSet<FKey> HeldKeys;
	FDaedalusDesktopArcadeInput PreviousInput;
	FString LastGameId;
	FString CatalogChoiceId;
	FString CatalogError;
	float StickX = 0.f;
	float StickY = 0.f;
	float RightTrigger = 0.f;
	bool bHadFocus = true;
};
