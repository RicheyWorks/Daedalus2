// SPDX-License-Identifier: MIT
#include "DaedalusSkyDirector.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/SkyLight.h"
#include "EngineUtils.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialParameterCollection.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Particles/ParticleSystemComponent.h"

static FLinearColor LerpC(const FLinearColor& A, const FLinearColor& B, float T) { return A + (B - A) * T; }

FDaedalusWeatherLook FDaedalusWeatherLook::Lerp(const FDaedalusWeatherLook& A, const FDaedalusWeatherLook& B, float T)
{
	FDaedalusWeatherLook R;
	R.SunScale = FMath::Lerp(A.SunScale, B.SunScale, T);
	R.SkyLightScale = FMath::Lerp(A.SkyLightScale, B.SkyLightScale, T);
	R.FogDensity = FMath::Lerp(A.FogDensity, B.FogDensity, T);
	R.CloudBottomKm = FMath::Lerp(A.CloudBottomKm, B.CloudBottomKm, T);
	R.CloudThicknessKm = FMath::Lerp(A.CloudThicknessKm, B.CloudThicknessKm, T);
	R.Rain = FMath::Lerp(A.Rain, B.Rain, T);
	R.Desaturate = LerpC(A.Desaturate, B.Desaturate, T);
	R.Wind = FMath::Lerp(A.Wind, B.Wind, T);
	R.LightningPerMinute = FMath::Lerp(A.LightningPerMinute, B.LightningPerMinute, T);
	return R;
}

FDaedalusWeatherLook FDaedalusWeatherLook::Default(EDaedalusWeather W)
{
	auto Make = [](float Sun, float Sky, float Fog, float Bottom, float Thick, float Rain, FLinearColor Tint)
	{
		FDaedalusWeatherLook R;
		R.SunScale = Sun; R.SkyLightScale = Sky; R.FogDensity = Fog; R.CloudBottomKm = Bottom;
		R.CloudThicknessKm = Thick; R.Rain = Rain; R.Desaturate = Tint;
		R.Wind = 0.2f + 0.8f * Rain; R.LightningPerMinute = Rain >= 1.f ? 4.f : 0.f;
		return R;
	};
	FDaedalusWeatherLook L;
	switch (W)
	{
	case EDaedalusWeather::Clear: L = Make(1.0f, 1.0f, 0.010f, 5.0f, 6.0f, 0.0f, FLinearColor::White); break;
	case EDaedalusWeather::Overcast: L = Make(0.35f, 0.8f, 0.025f, 2.5f, 9.0f, 0.0f, FLinearColor(0.85f, 0.88f, 0.92f)); break;
	case EDaedalusWeather::Rain: L = Make(0.18f, 0.6f, 0.045f, 1.5f, 10.0f, 0.7f, FLinearColor(0.7f, 0.75f, 0.85f)); break;
	case EDaedalusWeather::Storm: L = Make(0.06f, 0.35f, 0.07f, 0.9f, 12.0f, 1.0f, FLinearColor(0.55f, 0.6f, 0.75f)); break;
	case EDaedalusWeather::Fog: L = Make(0.45f, 0.9f, 0.25f, 3.0f, 6.0f, 0.0f, FLinearColor(0.9f, 0.92f, 0.95f)); break;
	}
	return L;
}

FDaedalusLightMood FDaedalusLightMood::Lerp(const FDaedalusLightMood& A, const FDaedalusLightMood& B, float T)
{
	FDaedalusLightMood R = T < 0.5f ? A : B;
	R.SunColor = LerpC(A.SunColor, B.SunColor, T);
	R.SunIntensity = FMath::Lerp(A.SunIntensity, B.SunIntensity, T);
	R.SkyColor = LerpC(A.SkyColor, B.SkyColor, T);
	R.SkyLightIntensity = FMath::Lerp(A.SkyLightIntensity, B.SkyLightIntensity, T);
	R.FogColor = LerpC(A.FogColor, B.FogColor, T);
	R.FogMultiplier = FMath::Lerp(A.FogMultiplier, B.FogMultiplier, T);
	R.FogHeightFalloff = FMath::Lerp(A.FogHeightFalloff, B.FogHeightFalloff, T);
	R.FogStartDistance = FMath::Lerp(A.FogStartDistance, B.FogStartDistance, T);
	return R;
}

/** Tiny HUD clock: "Day 3  14:05  Rain". */
class SDaedalusSkyClock : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SDaedalusSkyClock) {}
	SLATE_ARGUMENT(TWeakObjectPtr<ADaedalusSkyDirector>, Director)
	SLATE_END_ARGS()
	void Construct(const FArguments& Args)
	{
		Director = Args._Director;
		ChildSlot.HAlign(HAlign_Right).VAlign(VAlign_Top).Padding(16.f)
		[
			SNew(SBorder).Padding(FMargin(10.f, 4.f)).BorderBackgroundColor(FLinearColor(0.f, 0.f, 0.f, 0.45f))
			[ SNew(STextBlock).Text(this, &SDaedalusSkyClock::Label).ColorAndOpacity(FLinearColor::White) ]
		];
	}
private:
	FText Label() const
	{
		const ADaedalusSkyDirector* D = Director.Get();
		if (!D) return FText::GetEmpty();
		const float H = D->GetHour();
		const int32 Hh = FMath::FloorToInt(H), Mm = FMath::FloorToInt((H - Hh) * 60.f);
		const UEnum* E = StaticEnum<EDaedalusWeather>();
		return FText::FromString(FString::Printf(TEXT("Day %d  %02d:%02d  %s"), D->GetDay(), Hh, Mm,
			*E->GetDisplayNameTextByValue(static_cast<int64>(D->Weather)).ToString()));
	}
	TWeakObjectPtr<ADaedalusSkyDirector> Director;
};

float ADaedalusSkyDirector::DaylightForPitch(float Pitch)
{
	return FMath::SmoothStep(0.f, 0.25f, FMath::Sin(FMath::DegreesToRadians(-Pitch)));
}

FLinearColor ADaedalusSkyDirector::GradeForDaylight(float D, FLinearColor Noon)
{
	const FLinearColor Ember(1.f, 0.38f, 0.18f), Golden(1.f, 0.62f, 0.34f);
	if (D < 0.3f) return LerpC(Ember, Golden, D / 0.3f);
	return LerpC(Golden, Noon, FMath::SmoothStep(0.3f, 0.7f, D));
}

ADaedalusSkyDirector* ADaedalusSkyDirector::Find(const UObject* Ctx)
{
	UWorld* W = GEngine ? GEngine->GetWorldFromContextObject(Ctx, EGetWorldErrorMode::ReturnNull) : nullptr;
	if (!W) return nullptr;
	for (TActorIterator<ADaedalusSkyDirector> It(W); It; ++It) return *It;
	return nullptr;
}

FDaedalusSkyState ADaedalusSkyDirector::SaveState() const
{
	FDaedalusSkyState S;
	S.TimeOfDay = TimeOfDay; S.Day = Day; S.Weather = Weather; S.Mood = Mood; S.Wetness = Wetness;
	return S;
}

void ADaedalusSkyDirector::RestoreState(const FDaedalusSkyState& S)
{
	Day = FMath::Max(1, S.Day); Wetness = FMath::Clamp(S.Wetness, 0.f, 1.f);
	TimeOfDay = FMath::Fmod(FMath::Max(0.f, S.TimeOfDay), 24.f);
	LastHour = FMath::FloorToInt(TimeOfDay);
	if (!S.Mood.IsNone()) SetMood(S.Mood, true);
	SetWeather(S.Weather, true);
}

void ADaedalusSkyDirector::SetQuality(EDaedalusSkyQuality Q)
{
	Quality = Q;
	SetActorTickInterval(Q == EDaedalusSkyQuality::Low ? 0.25f : Q == EDaedalusSkyQuality::Medium ? 0.066f : 0.f);
	if (Clouds)
		if (UVolumetricCloudComponent* C = Clouds->FindComponentByClass<UVolumetricCloudComponent>())
		{
			const float S = Q == EDaedalusSkyQuality::Low ? 0.5f : Q == EDaedalusSkyQuality::Medium ? 0.75f : 1.f;
			C->SetViewSampleCountScale(S);
			C->SetReflectionSampleCountScale(S);
		}
	ApplyNow();
}

void ADaedalusSkyDirector::PlayGateCue(float Seconds)
{
	if (GateLeft <= 0.f) WeatherBeforeGate = Weather;
	GateTotal = GateLeft = FMath::Max(0.5f, Seconds);
	SetWeather(EDaedalusWeather::Clear);
}

void ADaedalusSkyDirector::Flash(float Strength)
{
	FlashStrength = Strength; FlashLeft = 0.18f;
	SetParam(TEXT("Lightning"), Strength);
	OnLightning.Broadcast(Strength);
}

void ADaedalusSkyDirector::SetParam(FName Name, float Value) const
{
	if (SkyParams && GetWorld()) UKismetMaterialLibrary::SetScalarParameterValue(GetWorld(), SkyParams, Name, Value);
}

void ADaedalusSkyDirector::EndPlay(const EEndPlayReason::Type Reason)
{
	if (Clock.IsValid() && GEngine && GEngine->GameViewport) GEngine->GameViewport->RemoveViewportWidgetContent(Clock.ToSharedRef());
	Clock.Reset();
	Super::EndPlay(Reason);
}

ADaedalusSkyDirector::ADaedalusSkyDirector()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

float ADaedalusSkyDirector::SunPitchForHour(float Hours)
{
		// 0h -> +90 (underfoot), 6h -> 0 (sunrise), 12h -> -90 (overhead), 18h -> -180 (sunset, far side).
	return 90.f - FMath::Fmod(FMath::Fmod(Hours, 24.f) + 24.f, 24.f) * 15.f;
}

bool ADaedalusSkyDirector::IsNight() const { return TimeOfDay < 6.f || TimeOfDay >= 18.f; }

int32 ADaedalusSkyDirector::FindSkyActors()
{
	UWorld* W = GetWorld();
	if (!W) return 0;
	int32 Found = 0;
	for (TActorIterator<AActor> It(W); It; ++It)
	{
		AActor* A = *It;
		if (!Sun && A != Moon && A->FindComponentByClass<UDirectionalLightComponent>()) { Sun = A; ++Found; }
		else if (!SkyLight && A->FindComponentByClass<USkyLightComponent>()) { SkyLight = A; ++Found; }
		else if (!HeightFog && A->FindComponentByClass<UExponentialHeightFogComponent>()) { HeightFog = A; ++Found; }
		else if (!Clouds && A->FindComponentByClass<UVolumetricCloudComponent>()) { Clouds = A; ++Found; }
	}
	return Found;
}

FDaedalusWeatherLook ADaedalusSkyDirector::LookFor(EDaedalusWeather W) const
{
	if (const FDaedalusWeatherLook* L = Looks.Find(W)) return *L;
	return FDaedalusWeatherLook::Default(W);
}

FDaedalusLightMood ADaedalusSkyDirector::MoodFor(FName Biome) const
{
	if (MoodTable)
		if (const FDaedalusLightMood* Row = MoodTable->FindRow<FDaedalusLightMood>(Biome, TEXT("SkyDirector"), false)) return *Row;
	return FallbackMood;
}

void ADaedalusSkyDirector::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	CurrentLook = FromLook = LookFor(Weather);
	CurrentMood = FromMood = MoodFor(Mood);
}

void ADaedalusSkyDirector::BeginPlay()
{
	Super::BeginPlay();
	FindSkyActors();
	Rng.Initialize(Seed);
	CurrentLook = FromLook = LookFor(Weather);
	CurrentMood = FromMood = MoodFor(Mood);
	WeatherT = MoodT = 1.f;
	LastHour = FMath::FloorToInt(TimeOfDay);
	SetQuality(Quality);
	if (bShowClock && GEngine && GEngine->GameViewport && GetWorld()->IsGameWorld())
	{
		Clock = SNew(SDaedalusSkyClock).Director(this);
		GEngine->GameViewport->AddViewportWidgetContent(Clock.ToSharedRef(), 10);
	}
}

void ADaedalusSkyDirector::SetWeather(EDaedalusWeather NewWeather, bool bInstant)
{
	const EDaedalusWeather Old = Weather;
	FromLook = CurrentLook;
	Weather = NewWeather;
	WeatherT = (bInstant || BlendSeconds <= 0.f) ? 1.f : 0.f;
	HoursSinceWeather = 0.f;
	if (WeatherT >= 1.f) { CurrentLook = LookFor(Weather); ApplyNow(); }
	if (Old != NewWeather) OnWeatherChanged.Broadcast(Old, NewWeather);
}

void ADaedalusSkyDirector::SetMood(FName Biome, bool bInstant)
{
	FromMood = CurrentMood;
	Mood = Biome;
	MoodT = (bInstant || BlendSeconds <= 0.f) ? 1.f : 0.f;
	if (MoodT >= 1.f) { CurrentMood = MoodFor(Mood); ApplyNow(); }
}

void ADaedalusSkyDirector::SetTimeOfDay(float Hours)
{
	TimeOfDay = FMath::Fmod(FMath::Fmod(Hours, 24.f) + 24.f, 24.f);
	ApplyNow();
}

void ADaedalusSkyDirector::Tick(float Dt)
{
	Super::Tick(Dt);
	if (bClockRunning && DayLengthMinutes > 0.f)
	{
		const float Hours = Dt * 24.f / (DayLengthMinutes * 60.f);
		TimeOfDay = FMath::Fmod(TimeOfDay + Hours, 24.f);
		HoursSinceWeather += Hours;
		if (AutoWeatherHours > 0.f && HoursSinceWeather >= AutoWeatherHours)
			SetWeather(static_cast<EDaedalusWeather>(Rng.RandRange(0, 4)));
	}
	const float Step = BlendSeconds > 0.f ? Dt / BlendSeconds : 1.f;
	if (WeatherT < 1.f) { WeatherT = FMath::Min(1.f, WeatherT + Step); CurrentLook = FDaedalusWeatherLook::Lerp(FromLook, LookFor(Weather), FMath::SmoothStep(0.f, 1.f, WeatherT)); }
	if (MoodT < 1.f) { MoodT = FMath::Min(1.f, MoodT + Step); CurrentMood = FDaedalusLightMood::Lerp(FromMood, MoodFor(Mood), FMath::SmoothStep(0.f, 1.f, MoodT)); }
	const int32 Hour = FMath::FloorToInt(TimeOfDay);
	if (Hour != LastHour)
	{
		if (Hour < LastHour) { ++Day; OnDayChanged.Broadcast(Day); }
		LastHour = Hour; OnHourChanged.Broadcast(Hour);
		if (Hour == 6) OnDawn.Broadcast(Day);
		if (Hour == 18) OnDusk.Broadcast(Day);
	}
	Wetness = FMath::Clamp(Wetness + (CurrentLook.Rain > 0.05f ? WetRate * CurrentLook.Rain : -DryRate) * Dt, 0.f, 1.f);
	if (CurrentLook.LightningPerMinute > 0.f && Rng.FRand() < CurrentLook.LightningPerMinute / 60.f * Dt) Flash(Rng.FRandRange(0.5f, 1.f));
	if (FlashLeft > 0.f) { FlashLeft -= Dt; if (FlashLeft <= 0.f) { FlashStrength = 0.f; SetParam(TEXT("Lightning"), 0.f); } }
	if (GateLeft > 0.f) { GateLeft -= Dt; if (GateLeft <= 0.f) SetWeather(WeatherBeforeGate); }
	Apply(CurrentLook, CurrentMood);
}

void ADaedalusSkyDirector::ApplyNow()
{
	if (WeatherT >= 1.f) CurrentLook = LookFor(Weather);
	if (MoodT >= 1.f) CurrentMood = MoodFor(Mood);
	Apply(CurrentLook, CurrentMood);
}

void ADaedalusSkyDirector::Apply(const FDaedalusWeatherLook& L, const FDaedalusLightMood& M)
{
	const float Pitch = SunPitchForHour(TimeOfDay);
	// Daylight factor: 1 overhead, 0 at/below horizon, smoothed through dawn/dusk.
	const float Sun01 = DaylightForPitch(Pitch);
	Daylight = Sun01 * L.SunScale;
	const FLinearColor SunTint = GradeForDaylight(Sun01, M.SunColor) * L.Desaturate;
	const float Glow = GateLeft > 0.f ? FMath::Sin(PI * GateLeft / FMath::Max(GateTotal, 0.01f)) : 0.f;

	if (Sun)
	{
		Sun->SetActorRotation(FRotator(Pitch, SunYaw, 0.f));
		if (UDirectionalLightComponent* C = Sun->FindComponentByClass<UDirectionalLightComponent>())
		{
			C->SetIntensity(M.SunIntensity * (L.SunScale * FMath::Max(Sun01, Moon ? 0.f : NightFloor) + 3.f * FlashStrength + 0.5f * Glow));
			C->SetLightColor(FlashStrength > 0.f ? FLinearColor(0.85f, 0.9f, 1.f)
				: LerpC(Sun01 > 0.f ? SunTint : FLinearColor(0.55f, 0.65f, 1.f), FLinearColor(1.f, 0.8f, 0.4f), Glow));
		}
	}
	if (Moon)
	{
		Moon->SetActorRotation(FRotator(Pitch + 180.f, SunYaw + 20.f, 0.f));
		if (UDirectionalLightComponent* C = Moon->FindComponentByClass<UDirectionalLightComponent>())
		{
			C->SetIntensity(MoonIntensity * (1.f - Sun01) * FMath::Max(L.SunScale, 0.2f));
			C->SetLightColor(FLinearColor(0.6f, 0.7f, 1.f));
		}
	}
	SetParam(TEXT("Night"), 1.f - Sun01);
	SetParam(TEXT("Wetness"), Wetness);
	SetParam(TEXT("WindStrength"), L.Wind);
	SetParam(TEXT("WindDirX"), FMath::Cos(FMath::DegreesToRadians(WindYaw)));
	SetParam(TEXT("WindDirY"), FMath::Sin(FMath::DegreesToRadians(WindYaw)));
	SetParam(TEXT("GateGlow"), Glow);
	if (SkyLight)
		if (USkyLightComponent* C = SkyLight->FindComponentByClass<USkyLightComponent>())
		{
			C->SetIntensity(M.SkyLightIntensity * L.SkyLightScale * FMath::Max(Sun01, 0.08f));
			C->SetLightColor(M.SkyColor * L.Desaturate);
			if (!C->bRealTimeCapture) C->RecaptureSky();
		}
	if (HeightFog)
		if (UExponentialHeightFogComponent* C = HeightFog->FindComponentByClass<UExponentialHeightFogComponent>())
		{
			C->SetFogDensity(L.FogDensity * M.FogMultiplier);
			C->SetFogInscatteringColor(M.FogColor * L.Desaturate * FMath::Max(Sun01, 0.1f));
			C->SetFogHeightFalloff(M.FogHeightFalloff);
			C->SetStartDistance(M.FogStartDistance);
			C->SetVolumetricFog(Quality != EDaedalusSkyQuality::Low && L.FogDensity > 0.04f);
		}
	if (Clouds)
		if (UVolumetricCloudComponent* C = Clouds->FindComponentByClass<UVolumetricCloudComponent>())
		{
			C->SetLayerBottomAltitude(L.CloudBottomKm);
			C->SetLayerHeight(L.CloudThicknessKm);
		}
	if (RainFx)
	{
		RainFx->SetActorHiddenInGame(L.Rain <= 0.01f);
		if (UFXSystemComponent* Fx = RainFx->FindComponentByClass<UFXSystemComponent>())
			Fx->SetFloatParameter(RainParam, L.Rain);
	}
}

// Tester console commands (claim 14): Daedalus.Sky.Time 18.5 | Daedalus.Sky.Weather Storm | Daedalus.Sky.Mood pine_stand
static void SkyCmd(const TArray<FString>& Args, UWorld* World, int32 Which)
{
	ADaedalusSkyDirector* D = ADaedalusSkyDirector::Find(World);
	if (!D || Args.Num() == 0) return;
	if (Which == 0) D->SetTimeOfDay(FCString::Atof(*Args[0]));
	else if (Which == 1)
	{
		const int64 V = StaticEnum<EDaedalusWeather>()->GetValueByNameString(Args[0]);
		if (V != INDEX_NONE) D->SetWeather(static_cast<EDaedalusWeather>(V));
	}
	else if (Which == 2) D->SetMood(FName(*Args[0]));
	else if (Which == 3) D->Flash(1.f);
	else if (Which == 4) D->PlayGateCue(FCString::Atof(*Args[0]));
}
static FAutoConsoleCommandWithWorldAndArgs GSkyTime(TEXT("Daedalus.Sky.Time"), TEXT("Set hour 0-24"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& A, UWorld* W) { SkyCmd(A, W, 0); }));
static FAutoConsoleCommandWithWorldAndArgs GSkyWeather(TEXT("Daedalus.Sky.Weather"), TEXT("Clear|Overcast|Rain|Storm|Fog"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& A, UWorld* W) { SkyCmd(A, W, 1); }));
static FAutoConsoleCommandWithWorldAndArgs GSkyMood(TEXT("Daedalus.Sky.Mood"), TEXT("biome row name"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& A, UWorld* W) { SkyCmd(A, W, 2); }));
static FAutoConsoleCommandWithWorldAndArgs GSkyFlash(TEXT("Daedalus.Sky.Flash"), TEXT("lightning flash"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& A, UWorld* W) { TArray<FString> X{TEXT("1")}; SkyCmd(X, W, 3); }));
static FAutoConsoleCommandWithWorldAndArgs GSkyGate(TEXT("Daedalus.Sky.GateCue"), TEXT("seconds"),
	FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& A, UWorld* W) { TArray<FString> X{A.Num() ? A[0] : FString(TEXT("6"))}; SkyCmd(X, W, 4); }));
