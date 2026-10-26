// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "Engine/Texture2D.h"
#include "UObject/StrongObjectPtr.h"
#include "Widgets/SCompoundWidget.h"

THIRD_PARTY_INCLUDES_START
#include "DaedalusRealmCore.h"
THIRD_PARTY_INCLUDES_END

class UTexture2D;
struct FSlateBrush;

/**
 * The 8-bit realm behind a portal (ADR-052), on screen. Wraps the engine-free core (DaedalusRealmCore.h): copies its
 * 256x240 frame into a texture drawn with nearest-pixel filtering and scaled to fit (black bars, square pixels),
 * feeds it the keyboard and the pad, plays its music cues through the jukebox, and closes when the party walks back
 * through the portal.
 *
 * Keys: arrows / WASD / d-pad walk; Enter, Space, Z or A (pad) is A; Backspace, X or B (pad) is B; Tab or Menu
 * (pad) is Start. Holding a direction keeps walking.
 */
class SDaedalusRealm : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SDaedalusRealm) {}
		SLATE_EVENT(FSimpleDelegate, OnExit)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);
	virtual ~SDaedalusRealm() override;

	/** Hand the realm its spec (the Java engines' DRR 1 text). False with a reason if the core refuses it. */
	bool LoadSpec(const FString& Spec, FString& Error);
	/** Sol's pixel art (DSP 1): monsters, party members and NPCs drawn from the pack instead of the procedural shapes. */
	bool LoadSprites(const FString& Pack, FString& Error);
	int32 SpriteCount() const;
	/** Bring back a saved party (DRS 1); harmless when empty. */
	void RestoreSave(const FString& Save);
	FString SaveText() const;

	daedalus::realm::Realm& Game() { return Core; }
	const daedalus::realm::Realm& Game() const { return Core; }

	/** Push the current frame into the texture now (the harness calls this before a capture). */
	void Refresh();
	/** Write what is on the realm's screen to a PNG, scaled up. */
	bool CapturePng(const FString& Path, int32 Scale = 3);

	virtual void Tick(const FGeometry& AllottedGeometry, const double InCurrentTime, const float InDeltaTime) override;
	virtual bool SupportsKeyboardFocus() const override { return true; }
	virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
	virtual FReply OnKeyUp(const FGeometry& Geometry, const FKeyEvent& Event) override;
	virtual FNavigationReply OnNavigation(const FGeometry& Geometry, const FNavigationEvent& Event) override;
	virtual FReply OnAnalogValueChanged(const FGeometry& Geometry, const FAnalogInputEvent& Event) override;

private:
	static bool MapKey(const FKey& Key, daedalus::realm::Button& Out);
	void Jukebox();
	bool CoreTick(float DeltaTime);
	FTSTicker::FDelegateHandle CoreTickHandle;

	daedalus::realm::Realm Core;
	FSimpleDelegate OnExit;
	TStrongObjectPtr<UTexture2D> Texture;
	TSharedPtr<FSlateBrush> Brush;
	TArray<FColor> Pixels;
	FString LastCue;
	bool bExitSent = false;
	int32 StickDir = -1;   // which direction the left stick holds, or -1
	float StickX = 0.f, StickY = 0.f;
};
