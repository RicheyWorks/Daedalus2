// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"

/** How a setting is changed: flipped, slid between Min and Max, or stepped through a list of choices. */
enum class EDaedalusSettingKind : uint8
{
	Toggle,
	Slider,
	Choice,
};

/** One row of the settings menu (ADR-041). Value is a number for every kind: 0/1, the slider value, a choice index. */
struct DAEDALUSLINK_API FDaedalusSetting
{
	FName Id;
	FString Tab;
	FString Section;
	FString Label;
	FString Help;
	EDaedalusSettingKind Kind = EDaedalusSettingKind::Toggle;
	float Min = 0.f;
	float Max = 1.f;
	float Step = 1.f;
	float Default = 0.f;
	float Value = 0.f;
	TArray<FString> Choices;
	FString Unit;

	/** The value as the menu shows it: ON/OFF, "5.0", "80", or the choice's name. */
	FString Format() const;
	/** 0..1 along a slider (for its bar). */
	float Fraction() const;
	/** One step left (-1) or right (+1); toggles flip, choices wrap. Returns whether the value changed. */
	bool Nudge(int32 Dir);
	/** What A / Enter does: flip a toggle, next choice; sliders don't change. */
	bool Activate();
};

/**
 * The player's settings: the menu's rows, their saved values (Saved/Config/DaedalusSettings.json), and the console
 * variables they drive (daedalus.InvertY, daedalus.StickSensX, ...). The hero reads the console variables every
 * frame and applies camera and deadzone settings when they change.
 */
class DAEDALUSLINK_API FDaedalusSettings
{
public:
	static FDaedalusSettings& Get();

	TArray<FString> Tabs;
	TArray<FDaedalusSetting> All;

	FDaedalusSetting* Find(FName Id);
	float V(FName Id) const;
	bool Set(FName Id, float Value);
	/** The rows on one tab, in order. */
	TArray<int32> RowsOn(const FString& Tab) const;
	void ResetTab(const FString& Tab);

	void Load();
	void Save() const;
	/** Write every setting to its console variable. */
	void PushCVars() const;

	static FString Path();

private:
	FDaedalusSettings();
	void Add(FName Id, const TCHAR* Tab, const TCHAR* Section, const TCHAR* Label, const TCHAR* Help, EDaedalusSettingKind Kind,
	         float Default, float Min = 0.f, float Max = 1.f, float Step = 1.f, const TCHAR* Unit = TEXT(""),
	         TArray<FString> Choices = {});
};
