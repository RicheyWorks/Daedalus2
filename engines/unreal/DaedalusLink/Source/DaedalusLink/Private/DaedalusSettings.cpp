// SPDX-License-Identifier: MIT

#include "DaedalusSettings.h"

#include "Dom/JsonObject.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

FString FDaedalusSetting::Format() const
{
	switch (Kind)
	{
	case EDaedalusSettingKind::Toggle:
		return Value > 0.5f ? TEXT("ON") : TEXT("OFF");
	case EDaedalusSettingKind::Choice:
		return Choices.IsValidIndex(FMath::RoundToInt(Value)) ? Choices[FMath::RoundToInt(Value)] : TEXT("?");
	default:
		break;
	}
	const bool bWhole = FMath::IsNearlyEqual(Step, FMath::RoundToFloat(Step)) && Step >= 1.f;
	return (bWhole ? FString::Printf(TEXT("%d"), FMath::RoundToInt(Value)) : FString::Printf(TEXT("%.1f"), Value)) + Unit;
}

float FDaedalusSetting::Fraction() const
{
	return Max > Min ? FMath::Clamp((Value - Min) / (Max - Min), 0.f, 1.f) : 0.f;
}

bool FDaedalusSetting::Nudge(int32 Dir)
{
	const float Before = Value;
	switch (Kind)
	{
	case EDaedalusSettingKind::Toggle:
		Value = Value > 0.5f ? 0.f : 1.f;
		break;
	case EDaedalusSettingKind::Choice:
		if (Choices.Num() > 0)
		{
			Value = static_cast<float>((FMath::RoundToInt(Value) + Dir + Choices.Num()) % Choices.Num());
		}
		break;
	default:
		Value = FMath::Clamp(FMath::GridSnap(Value + Dir * Step, Step), Min, Max);
		break;
	}
	return !FMath::IsNearlyEqual(Before, Value);
}

bool FDaedalusSetting::Activate()
{
	return Kind == EDaedalusSettingKind::Slider ? false : Nudge(+1);
}

FDaedalusSettings& FDaedalusSettings::Get()
{
	static FDaedalusSettings Instance;
	return Instance;
}

FString FDaedalusSettings::Path()
{
	return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Config"), TEXT("DaedalusSettings.json"));
}

void FDaedalusSettings::Add(FName Id, const TCHAR* Tab, const TCHAR* Section, const TCHAR* Label, const TCHAR* Help, EDaedalusSettingKind Kind,
                            float Default, float Min, float Max, float Step, const TCHAR* Unit, TArray<FString> Choices)
{
	FDaedalusSetting S;
	S.Id = Id;
	S.Tab = Tab;
	S.Section = Section;
	S.Label = Label;
	S.Help = Help;
	S.Kind = Kind;
	S.Default = Default;
	S.Value = Default;
	S.Min = Min;
	S.Max = Max;
	S.Step = Step;
	S.Unit = Unit;
	S.Choices = MoveTemp(Choices);
	All.Add(MoveTemp(S));
}

FDaedalusSettings::FDaedalusSettings()
{
	using K = EDaedalusSettingKind;
	// Tabs and sections follow a modern console game's settings (Controller, Keyboard/Mouse, Video, Gameplay, Accessibility).
	Tabs = {TEXT("CONTROLLER"), TEXT("KEYBOARD/MOUSE"), TEXT("VIDEO"), TEXT("GAMEPLAY"), TEXT("ACCESSIBILITY")};
	const TCHAR* Pad = TEXT("CONTROLLER");
	const TCHAR* Kbm = TEXT("KEYBOARD/MOUSE");

	Add("InvertLookY", Pad, TEXT("Movement & Aiming"), TEXT("Invert Look (Vertical)"), TEXT("Push the right stick up to look down, like a flight stick."), K::Toggle, 0);
	Add("InvertLookX", Pad, TEXT("Movement & Aiming"), TEXT("Invert Look (Horizontal)"), TEXT("Push the right stick right to turn left."), K::Toggle, 0);
	Add("ButtonLayout", Pad, TEXT("Layouts"), TEXT("Button Layout"), TEXT("Which buttons do what. Bumper Jumper puts jump on LB so your thumb never leaves the look stick; Boxer puts melee on the left trigger; Recon puts melee on Y. The Field Menu's Controls tab shows the result."), K::Choice, 0, 0, 5, 1, TEXT(""), {TEXT("DEFAULT"), TEXT("BUMPER JUMPER"), TEXT("BUMPER NINJA"), TEXT("BOXER"), TEXT("GREEN THUMB"), TEXT("RECON")});
	Add("ThumbstickLayout", Pad, TEXT("Layouts"), TEXT("Thumbstick Layout"), TEXT("Southpaw swaps the sticks. Legacy moves forward and back and turns on the left stick, strafes and looks up and down on the right."), K::Choice, 0, 0, 3, 1, TEXT(""), {TEXT("DEFAULT"), TEXT("SOUTHPAW"), TEXT("LEGACY"), TEXT("LEGACY SOUTHPAW")});
	Add("Vibration", Pad, TEXT("General"), TEXT("Vibration"), TEXT("Rumble on sword swings, down-thrust bounces, hard landings and respawns."), K::Toggle, 1);
	Add("VibrationStrength", Pad, TEXT("General"), TEXT("Vibration Strength"), TEXT("How strong the rumble is."), K::Slider, 100, 0, 100, 5, TEXT("%"));
	Add("LookAccel", Pad, TEXT("Sensitivity & Acceleration"), TEXT("Look Acceleration"), TEXT("Holding the right stick all the way speeds the turn up over half a second. 0 turns it off."), K::Slider, 3, 0, 10, 1);
	Add("LookSensH", Pad, TEXT("Sensitivity & Acceleration"), TEXT("Look Sensitivity (Horizontal)"), TEXT("How fast the right stick turns the camera left and right. 5 is the default turn rate."), K::Slider, 5, 1, 10, 0.5f);
	Add("LookSensV", Pad, TEXT("Sensitivity & Acceleration"), TEXT("Look Sensitivity (Vertical)"), TEXT("How fast the right stick tilts the camera up and down."), K::Slider, 5, 1, 10, 0.5f);
	Add("LeftDeadzone", Pad, TEXT("Move Thumbstick"), TEXT("Center Dead Zone"), TEXT("How far the left stick must move before the hero walks. Raise it if the hero drifts."), K::Slider, 15, 0, 40, 1, TEXT("%"));
	Add("RightDeadzone", Pad, TEXT("Look Thumbstick"), TEXT("Center Dead Zone"), TEXT("How far the right stick must move before the camera turns. Raise it if the camera drifts."), K::Slider, 15, 0, 40, 1, TEXT("%"));

	Add("InvertMouseY", Kbm, TEXT("Movement & Aiming"), TEXT("Invert Look (Vertical)"), TEXT("Move the mouse forward to look down."), K::Toggle, 0);
	Add("MouseSensH", Kbm, TEXT("Sensitivity"), TEXT("Mouse Sensitivity (Horizontal)"), TEXT("Camera turn per mouse count, on a 1-10 scale. Look is raw and unsmoothed, so high-polling mice (Razer 8K) track exactly."), K::Slider, 5, 0.5f, 10, 0.1f);
	Add("MouseSensV", Kbm, TEXT("Sensitivity"), TEXT("Mouse Sensitivity (Vertical)"), TEXT("The same for up and down."), K::Slider, 5, 0.5f, 10, 0.1f);

	Add("CameraView", TEXT("VIDEO"), TEXT("Camera"), TEXT("Camera View"), TEXT("First Person sees through the hero's eyes with a centred reticle, like a modern console shooter. Over the Shoulder sits behind one shoulder; a third-person view. Classic follows from behind. R3, D-pad up or V switches in play."), K::Choice, 1, 0, 2, 1, TEXT(""), {TEXT("FIRST PERSON"), TEXT("OVER THE SHOULDER"), TEXT("CLASSIC")});
	Add("Shoulder", TEXT("VIDEO"), TEXT("Camera"), TEXT("Shoulder"), TEXT("Which shoulder the camera sits behind in Over the Shoulder. LB, D-pad down or C swaps it in play."), K::Choice, 0, 0, 1, 1, TEXT(""), {TEXT("RIGHT"), TEXT("LEFT")});
	Add("Reticle", TEXT("VIDEO"), TEXT("Camera"), TEXT("Reticle"), TEXT("The centred aiming reticle in First Person and Over the Shoulder, and with the blaster in any view."), K::Toggle, 1);
	Add("FieldOfView", TEXT("VIDEO"), TEXT("Camera"), TEXT("Field of View"), TEXT("How wide the camera sees. Wider shows more of the islands; narrower feels closer to the hero."), K::Slider, 80, 70, 110, 1, TEXT("°"));
	Add("CameraDistance", TEXT("VIDEO"), TEXT("Camera"), TEXT("Camera Distance"), TEXT("How far behind the hero the camera sits."), K::Slider, 650, 300, 1200, 25);

	Add("ShieldMode", TEXT("GAMEPLAY"), TEXT("Combat"), TEXT("Shield"), TEXT("Hold: the shield is up while the button is held. Toggle: press once to raise it, again to lower it."), K::Choice, 0, 0, 1, 1, TEXT(""), {TEXT("HOLD"), TEXT("TOGGLE")});

	Add("CameraLag", TEXT("ACCESSIBILITY"), TEXT("Camera"), TEXT("Camera Smoothing"), TEXT("The camera trails the hero slightly. Turn it off for a camera locked to the hero."), K::Toggle, 1);
	Load();
}

FDaedalusSetting* FDaedalusSettings::Find(FName Id)
{
	return All.FindByPredicate([Id](const FDaedalusSetting& S) { return S.Id == Id; });
}

float FDaedalusSettings::V(FName Id) const
{
	const FDaedalusSetting* S = All.FindByPredicate([Id](const FDaedalusSetting& X) { return X.Id == Id; });
	return S ? S->Value : 0.f;
}

bool FDaedalusSettings::Set(FName Id, float Value)
{
	FDaedalusSetting* S = Find(Id);
	if (!S)
	{
		return false;
	}
	S->Value = S->Kind == EDaedalusSettingKind::Slider ? FMath::Clamp(Value, S->Min, S->Max) : Value;
	PushCVars();
	return true;
}

TArray<int32> FDaedalusSettings::RowsOn(const FString& Tab) const
{
	TArray<int32> Out;
	for (int32 i = 0; i < All.Num(); ++i)
	{
		if (All[i].Tab == Tab)
		{
			Out.Add(i);
		}
	}
	return Out;
}

void FDaedalusSettings::ResetTab(const FString& Tab)
{
	for (FDaedalusSetting& S : All)
	{
		if (S.Tab == Tab)
		{
			S.Value = S.Default;
		}
	}
	PushCVars();
}

void FDaedalusSettings::Load()
{
	FString Text;
	if (FFileHelper::LoadFileToString(Text, *Path()))
	{
		TSharedPtr<FJsonObject> Root;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
		if (FJsonSerializer::Deserialize(Reader, Root) && Root.IsValid())
		{
			for (FDaedalusSetting& S : All)
			{
				double N = 0.0;
				if (Root->TryGetNumberField(S.Id.ToString(), N))
				{
					S.Value = S.Kind == EDaedalusSettingKind::Slider ? FMath::Clamp(static_cast<float>(N), S.Min, S.Max) : static_cast<float>(N);
				}
			}
		}
	}
	PushCVars();
}

void FDaedalusSettings::Save() const
{
	const TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
	for (const FDaedalusSetting& S : All)
	{
		Root->SetNumberField(S.Id.ToString(), S.Value);
	}
	FString Text;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Text);
	FJsonSerializer::Serialize(Root, Writer);
	FFileHelper::SaveStringToFile(Text, *Path());
}

void FDaedalusSettings::PushCVars() const
{
	auto SetF = [](const TCHAR* Name, float Value)
	{
		if (IConsoleVariable* C = IConsoleManager::Get().FindConsoleVariable(Name))
		{
			C->Set(Value, ECVF_SetByCode);
		}
	};
	SetF(TEXT("daedalus.InvertY"), V("InvertLookY"));
	SetF(TEXT("daedalus.InvertX"), V("InvertLookX"));
	SetF(TEXT("daedalus.StickSensX"), V("LookSensH"));
	SetF(TEXT("daedalus.StickSensY"), V("LookSensV"));
	SetF(TEXT("daedalus.LookAccel"), V("LookAccel"));
	SetF(TEXT("daedalus.Rumble"), V("Vibration"));
	SetF(TEXT("daedalus.RumbleScale"), V("VibrationStrength") / 100.f);
	SetF(TEXT("daedalus.MouseSensitivity"), V("MouseSensH") * 0.06f);
	SetF(TEXT("daedalus.MouseSensitivityY"), V("MouseSensV") * 0.06f);
	SetF(TEXT("daedalus.InvertMouseY"), V("InvertMouseY"));
}
