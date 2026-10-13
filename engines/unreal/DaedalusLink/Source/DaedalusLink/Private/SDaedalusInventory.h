// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "DaedalusInventoryCore.h"
#include "Widgets/SCompoundWidget.h"

class SBox;

/**
 * The tabbed inventory (hub 28570/28573/28574): the same panel in every realm, drawn in the realm's theme.
 *   LB / RB, Q / E      tabs (wrap; each tab keeps its cursor)
 *   d-pad / arrows      the item grid
 *   A / Enter           the item's actions, then the action
 *   B / Backspace / I   back: actions first, then close
 * The behaviour lives in daedalus::inv::Tabs (headless, core-test/inventory_core_test.cpp); this widget only draws
 * what the model says and hands its Intents to the host through OnIntent. Nothing here changes a quantity.
 */
class SDaedalusInventory : public SCompoundWidget
{
public:
	DECLARE_DELEGATE_OneParam(FOnIntent, const daedalus::inv::Intent&);

	SLATE_BEGIN_ARGS(SDaedalusInventory) {}
		SLATE_EVENT(FSimpleDelegate, OnClose)
		SLATE_EVENT(FOnIntent, OnIntent)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	/** Open on a catalog with the bag's counts and what is worn (slot -> item id). The catalog must outlive the widget. */
	void Open(const daedalus::inv::Catalog& Catalog, const TMap<FString, int32>& Bag, const TMap<FString, FString>& Worn);
	/** The host ran an intent: new counts, same place. */
	void Refresh(const TMap<FString, int32>& Bag, const TMap<FString, FString>& Worn);

	virtual bool SupportsKeyboardFocus() const override { return true; }
	virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
	virtual FNavigationReply OnNavigation(const FGeometry& Geometry, const FNavigationEvent& Event) override;

	/** For the harness: tab+ tab- up down left right accept back. Returns the model's line. */
	FString Input(const FString& Command);
	FString Describe() const { return UTF8_TO_TCHAR(Model.Describe().c_str()); }
	const daedalus::inv::Tabs& GetModel() const { return Model; }

private:
	void Rebuild();
	TSharedRef<SWidget> BuildTabs() const;
	TSharedRef<SWidget> BuildGrid() const;
	TSharedRef<SWidget> BuildDetails() const;
	FLinearColor Col(uint32 Rgb, float Alpha = 1.f) const;
	FSlateFontInfo Font(const char* Weight, int32 Size) const;
	static std::map<std::string, int> ToCounts(const TMap<FString, int32>& Bag);
	static std::map<std::string, std::string> ToWorn(const TMap<FString, FString>& Worn);

	daedalus::inv::Tabs Model;
	FSimpleDelegate OnClose;
	FOnIntent OnIntent;
	TSharedPtr<SBox> Body;
};
