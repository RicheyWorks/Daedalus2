// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"

class SScrollBox;
class SVerticalBox;
class SHorizontalBox;

/**
 * The pause menu and its settings (ADR-041), laid out like Halo Infinite's. Pausing shows only a short list
 * (Resume, Settings, Respawn); choosing Settings opens the settings page: a tab ribbon across the top (LB / RB or Q / E),
 * a scrolling list of rows (up / down), each adjusted in place (left / right, A to flip), a panel on the right that
 * explains the selected row, and button hints along the bottom. Every change is applied and saved at once.
 * Works with a controller, the keyboard, and the mouse (click tabs, rows and arrows; wheel scrolls).
 */
class SDaedalusSettingsMenu : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SDaedalusSettingsMenu) {}
		SLATE_EVENT(FSimpleDelegate, OnClose)
		SLATE_EVENT(FSimpleDelegate, OnChanged)
		SLATE_EVENT(FSimpleDelegate, OnRespawn)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	virtual bool SupportsKeyboardFocus() const override { return true; }
	virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
	virtual FNavigationReply OnNavigation(const FGeometry& Geometry, const FNavigationEvent& Event) override;

	/** For the harness: which tab and row are selected. */
	int32 GetTab() const { return Tab; }
	bool InSettings() const { return bInSettings; }
	void OpenSettings();
	void Back();
	int32 GetRow() const { return Row; }
	void SelectTab(int32 NewTab);
	void MoveRow(int32 Dir);
	void Adjust(int32 Dir);
	void Accept();
	void ResetTab();

private:
	void RebuildRows();
	void RebuildTabs();
	void Changed();
	int32 SettingIndex() const;

	FSimpleDelegate OnClose;
	FSimpleDelegate OnChanged;
	FSimpleDelegate OnRespawn;
	bool bInSettings = false;
	int32 PauseRow = 0;
	void PauseSelect();
	int32 Tab = 0;   // opens on CONTROLLER, as Halo Infinite does on a pad
	int32 Row = 0;
	TArray<int32> Rows;
	TArray<TSharedPtr<SWidget>> RowWidgets;
	TSharedPtr<SHorizontalBox> TabBar;
	TSharedPtr<SVerticalBox> List;
	TSharedPtr<SScrollBox> Scroll;
};
