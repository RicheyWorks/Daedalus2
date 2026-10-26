// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"

class ADaedalusHero;
class SBox;

/**
 * The field menu (ADR-041), a modern console game's Campaign Menu: the View button (two boxes), Tab or M opens it over the
 * game. LB / RB switch tabs:
 *   MAP       the TacMap: every island seen from above, the hero as a marker that turns with him
 *   HERO      the hero's record (swings, down-thrust bounces, respawns, where he last stood)
 *   CONTROLS  the layout for keyboard/mouse and controller
 *   SOCIAL    friends and party: arrives with online play (Epic Online Services / the Daedalus server)
 * B, View, Tab or M closes it.
 */
class SDaedalusFieldMenu : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SDaedalusFieldMenu) {}
		SLATE_EVENT(FSimpleDelegate, OnClose)
		SLATE_ARGUMENT(TWeakObjectPtr<ADaedalusHero>, Hero)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	virtual bool SupportsKeyboardFocus() const override { return true; }
	virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
	virtual FNavigationReply OnNavigation(const FGeometry& Geometry, const FNavigationEvent& Event) override;

	int32 GetTab() const { return Tab; }
	void SelectTab(int32 NewTab);
	/** For the harness: how many islands the map drew. */
	int32 MapIslands() const { return Islands.Num(); }

private:
	TSharedRef<SWidget> BuildMap();
	TSharedRef<SWidget> BuildHero();
	TSharedRef<SWidget> BuildControls();
	TSharedRef<SWidget> BuildSocial();
	FVector2D ToMap(const FVector& World) const;

	FSimpleDelegate OnClose;
	TWeakObjectPtr<ADaedalusHero> Hero;
	int32 Tab = 0;
	TArray<FBox2D> Islands;   // chunk footprints, world units
	FBox2D Bounds;
	static constexpr float MapSize = 620.f;
};
