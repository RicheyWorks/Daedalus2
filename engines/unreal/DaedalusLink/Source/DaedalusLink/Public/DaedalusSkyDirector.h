// SPDX-License-Identifier: MIT
// Day/night + weather + per-biome lighting mood for any Daedalus level (board #11, Team Grok Wild Biomes).
// One actor drives the level's existing sun, sky light, height fog, volumetric cloud and an optional rain FX actor.
// It never creates lights itself: it finds them (import_world_package.ensure_sky already adds them), so it
// composes with every level. Blueprint-friendly: SetWeather / SetMood / SetTimeOfDay, OnHourChanged for audio.
#pragma once

#include "CoreMinimal.h"
#include "Engine/DataTable.h"
#include "GameFramework/Actor.h"
#include "DaedalusSkyDirector.generated.h"

UENUM(BlueprintType)
enum class EDaedalusWeather : uint8 { Clear, Overcast, Rain, Storm, Fog };

/** How a weather state looks, as multipliers/targets the director blends between. */
USTRUCT(BlueprintType)
struct FDaedalusWeatherLook
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float SunScale = 1.f;       // x mood sun intensity
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float SkyLightScale = 1.f;  // x mood sky light
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float FogDensity = 0.02f;   // absolute, x mood fog multiplier
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float CloudBottomKm = 5.f;  // lower = heavier sky
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float CloudThicknessKm = 10.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float Rain = 0.f;           // 0..1 rain FX intensity
	UPROPERTY(EditAnywhere, BlueprintReadWrite) FLinearColor Desaturate = FLinearColor::White; // tints the sun

	static FDaedalusWeatherLook Lerp(const FDaedalusWeatherLook& A, const FDaedalusWeatherLook& B, float T);
	static FDaedalusWeatherLook Default(EDaedalusWeather W);
};

/** A biome's lighting mood. Row of a DataTable (row name = biome id, e.g. young_meadow). */
USTRUCT(BlueprintType)
struct FDaedalusLightMood : public FTableRowBase
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite) FLinearColor SunColor = FLinearColor(1.f, 0.96f, 0.9f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float SunIntensity = 10.f;   // lux at noon
	UPROPERTY(EditAnywhere, BlueprintReadWrite) FLinearColor SkyColor = FLinearColor::White;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float SkyLightIntensity = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) FLinearColor FogColor = FLinearColor(0.45f, 0.55f, 0.7f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float FogMultiplier = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) EDaedalusWeather DefaultWeather = EDaedalusWeather::Clear;

	static FDaedalusLightMood Lerp(const FDaedalusLightMood& A, const FDaedalusLightMood& B, float T);
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusHourChanged, int32, Hour);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusWeatherChanged, EDaedalusWeather, From, EDaedalusWeather, To);

UCLASS(BlueprintType, Blueprintable, ClassGroup = Daedalus, meta = (DisplayName = "Daedalus Sky Director"))
class DAEDALUSLINK_API ADaedalusSkyDirector : public AActor
{
	GENERATED_BODY()
public:
	ADaedalusSkyDirector();

	// --- The level actors it drives (auto-found by class on BeginPlay when empty) ---
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Sky") TObjectPtr<AActor> Sun;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Sky") TObjectPtr<AActor> SkyLight;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Sky") TObjectPtr<AActor> HeightFog;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Sky") TObjectPtr<AActor> Clouds;
	/** Optional: any actor with a Niagara/Cascade component; gets float param RainParam and is hidden when dry. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Sky") TObjectPtr<AActor> RainFx;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Sky") FName RainParam = TEXT("Intensity");

	// --- Clock ---
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Time", meta = (ClampMin = 0, ClampMax = 24)) float TimeOfDay = 9.f;
	/** Real minutes per in-game day. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Time", meta = (ClampMin = 0.1)) float DayLengthMinutes = 20.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Time") bool bClockRunning = true;
	/** Compass yaw of the sun's path. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Time") float SunYaw = -60.f;
	/** Moonlight floor so nights stay readable (fraction of mood sun intensity). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Time") float NightFloor = 0.03f;

	// --- Weather ---
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Weather") EDaedalusWeather Weather = EDaedalusWeather::Clear;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Weather") float BlendSeconds = 8.f;
	/** Override looks per state; missing states use FDaedalusWeatherLook::Default. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Weather") TMap<EDaedalusWeather, FDaedalusWeatherLook> Looks;
	/** Random weather changes every N in-game hours (0 = off). Deterministic from Seed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Weather") float AutoWeatherHours = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Weather") int32 Seed = 7;

	// --- Mood ---
	/** Rows of FDaedalusLightMood; row name = biome id. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Mood") TObjectPtr<UDataTable> MoodTable;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Mood") FName Mood = TEXT("young_meadow");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Mood") FDaedalusLightMood FallbackMood;

	UPROPERTY(BlueprintAssignable, Category = "Daedalus") FDaedalusHourChanged OnHourChanged;
	UPROPERTY(BlueprintAssignable, Category = "Daedalus") FDaedalusWeatherChanged OnWeatherChanged;

	UFUNCTION(BlueprintCallable, Category = "Daedalus") void SetWeather(EDaedalusWeather NewWeather, bool bInstant = false);
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void SetMood(FName Biome, bool bInstant = false);
	UFUNCTION(BlueprintCallable, Category = "Daedalus") void SetTimeOfDay(float Hours);
	UFUNCTION(BlueprintPure, Category = "Daedalus") bool IsNight() const;
	/** Sun pitch in degrees for an hour: -90 at noon (overhead), +90 at midnight. Pure, testable. */
	UFUNCTION(BlueprintPure, Category = "Daedalus") static float SunPitchForHour(float Hours);
	/** Find the level's sky actors by class. Returns how many slots were filled. */
	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Daedalus") int32 FindSkyActors();
	/** Push the current state to the level right now (also works in the editor). */
	UFUNCTION(BlueprintCallable, CallInEditor, Category = "Daedalus") void ApplyNow();

	virtual void Tick(float DeltaSeconds) override;
	virtual bool ShouldTickIfViewportsOnly() const override { return bPreviewInEditor; }
	UPROPERTY(EditAnywhere, Category = "Daedalus|Time") bool bPreviewInEditor = false;

protected:
	virtual void BeginPlay() override;
	virtual void OnConstruction(const FTransform& Transform) override;

private:
	FDaedalusWeatherLook LookFor(EDaedalusWeather W) const;
	FDaedalusLightMood MoodFor(FName Biome) const;
	void Apply(const FDaedalusWeatherLook& Look, const FDaedalusLightMood& M);

	FDaedalusWeatherLook FromLook, CurrentLook;
	FDaedalusLightMood FromMood, CurrentMood;
	float WeatherT = 1.f, MoodT = 1.f, HoursSinceWeather = 0.f;
	int32 LastHour = -1;
	FRandomStream Rng;
};
