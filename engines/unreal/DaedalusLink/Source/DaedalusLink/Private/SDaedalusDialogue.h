// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "DaedalusDialogueCore.h"
#include "Widgets/SCompoundWidget.h"

class SBox;

/**
 * The dialogue box of the 3D realms (Richey, 2026-10-13: "new school does too, like Animal Crossing"): a rounded
 * bubble low on the screen in the realm's theme, a bouncing name tag, text that types itself with a blip per
 * letter in the speaker's voice, a blinking arrow when more waits, choices at the end. The 8-bit realm keeps its
 * Final Fantasy window. The behaviour is daedalus::dlg::Dialogue (core-test/dialogue_core_test.cpp); this draws it.
 *   A / Enter / Space   finish the page, next page, pick the choice
 *   B / Backspace       skip to the end of the text; in a choice, land on the last answer
 *   up / down           the choices
 */
class SDaedalusDialogue : public SCompoundWidget
{
public:
	DECLARE_DELEGATE_OneParam(FOnOutcome, const daedalus::dlg::Outcome&);
	DECLARE_DELEGATE_OneParam(FOnSfx, const FString&);

	SLATE_BEGIN_ARGS(SDaedalusDialogue) {}
		SLATE_EVENT(FOnOutcome, OnOutcome)
		SLATE_EVENT(FOnSfx, OnSfx)
		SLATE_ARGUMENT(FString, Theme)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

	void Say(const FString& Speaker, const FString& Text, const TArray<FString>& Choices);
	bool IsOpen() const { return Model.Open(); }

	virtual bool SupportsKeyboardFocus() const override { return true; }
	virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
	virtual void Tick(const FGeometry& Geometry, const double CurrentTime, const float DeltaTime) override;

	/** For the harness: a b up down tick:<seconds> state. Returns the model's line. */
	FString Input(const FString& Command);
	FString Describe() const { return UTF8_TO_TCHAR(Model.Describe().c_str()); }

private:
	void Rebuild();
	void Press(daedalus::dlg::Button B);
	void Advance(double Dt);
	FLinearColor Col(uint32 Rgb, float Alpha = 1.f) const;
	FSlateFontInfo Font(const char* Weight, int32 Size) const;

	daedalus::dlg::Dialogue Model;
	FOnOutcome OnOutcome;
	FOnSfx OnSfx;
	TSharedPtr<SBox> Body;
	FString LastVisible;   // the text drawn last frame: rebuild only when it changes
	bool bLastArrow = false;
	int32 LastCursor = -1;
};
