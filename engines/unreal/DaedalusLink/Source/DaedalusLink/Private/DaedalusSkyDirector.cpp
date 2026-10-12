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
	return R;
}

FDaedalusWeatherLook FDaedalusWeatherLook::Default(EDaedalusWeather W)
{
	auto Make = [](float Sun, float Sky, float Fog, float Bottom, float Thick, float Rain, FLinearColor Tint)
	{
		FDaedalusWeatherLook R;
		R.SunScale = Sun; R.SkyLightScale = Sky; R.FogDensity = Fog; R.CloudBottomKm = Bottom;
		R.CloudThicknessKm = Thick; R.Rain = Rain; R.Desaturate = Tint;
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
	return R;
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
		if (!Sun && A->FindComponentByClass<UDirectionalLightComponent>()) { Sun = A; ++Found; }
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
	ApplyNow();
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
	if (Hour != LastHour) { LastHour = Hour; OnHourChanged.Broadcast(Hour); }
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
	const float Day = FMath::SmoothStep(0.f, 0.25f, FMath::Sin(FMath::DegreesToRadians(-Pitch)));
	// Warmer near the horizon.
	const FLinearColor Golden(1.f, 0.55f, 0.3f);
	const FLinearColor SunTint = LerpC(Golden, M.SunColor, FMath::SmoothStep(0.f, 0.5f, Day)) * L.Desaturate;

	if (Sun)
	{
		Sun->SetActorRotation(FRotator(Pitch, SunYaw, 0.f));
		if (UDirectionalLightComponent* C = Sun->FindComponentByClass<UDirectionalLightComponent>())
		{
			C->SetIntensity(M.SunIntensity * L.SunScale * FMath::Max(Day, NightFloor));
			C->SetLightColor(Day > 0.f ? SunTint : FLinearColor(0.55f, 0.65f, 1.f)); // moonlight blue
		}
	}
	if (SkyLight)
		if (USkyLightComponent* C = SkyLight->FindComponentByClass<USkyLightComponent>())
		{
			C->SetIntensity(M.SkyLightIntensity * L.SkyLightScale * FMath::Max(Day, 0.08f));
			C->SetLightColor(M.SkyColor * L.Desaturate);
			if (!C->bRealTimeCapture) C->RecaptureSky();
		}
	if (HeightFog)
		if (UExponentialHeightFogComponent* C = HeightFog->FindComponentByClass<UExponentialHeightFogComponent>())
		{
			C->SetFogDensity(L.FogDensity * M.FogMultiplier);
			C->SetFogInscatteringColor(M.FogColor * L.Desaturate * FMath::Max(Day, 0.1f));
			C->SetVolumetricFog(L.FogDensity > 0.04f);
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
