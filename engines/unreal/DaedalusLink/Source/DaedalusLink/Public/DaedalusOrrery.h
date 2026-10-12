// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Subsystems/WorldSubsystem.h"
#include "DaedalusOrrery.generated.h"

class ADaedalusHero;
class UPointLightComponent;
class UStaticMeshComponent;
class UTextRenderComponent;

/**
 * The Orrery Reach (docs/realms/OrreryReach.md): Claude Island's own game, Starbloom Steeping, and its adventure,
 * the Keeper's Logbook.
 *
 * - Every one of the 24 starbloom herbs blooms at its own sky hour (the Sky Director's clock, or the island's own
 *   when there is no Sky Director), and can only be harvested then.
 * - Herbs belong to 12 constellations, a day bloom and a night bloom each. At a steeping kettle with clean water:
 *   one herb makes its tea, a constellation's two herbs its brew, and a day and a night bloom from different
 *   constellations an eclipse brew.
 * - The Keeper's Logbook leads from the dock through clean water, the first chart, the bloom hours and the kettle to
 *   all twelve charts, an eclipse brew and the great telescope.
 */
UCLASS()
class DAEDALUSLINK_API UDaedalusOrrery : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	struct FHerb { const TCHAR* Name; int32 Hour; const TCHAR* Constellation; };
	static const TArray<FHerb>& Herbs();
	static const FHerb* Herb(const FString& Name);
	static const TArray<FString>& Constellations();
	static bool IsDay(int32 Hour) { return Hour >= 6 && Hour < 18; }

	static UDaedalusOrrery* Get(const UObject* WorldContext);

	/** The sky hour, 0..24: the Sky Director's when there is one, else one island hour per SecondsPerHour. */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Orrery") float Hour() const;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Orrery") float SecondsPerHour = 30.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Orrery") float StartHour = 17.f;

	// The player's progress (the harness reads these).
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Orrery") TArray<FString> Satchel;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Orrery") TArray<FString> Brews;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Orrery") TArray<FString> Charts;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Orrery") int32 Step = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Orrery") bool bCleanWater = false;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Orrery") int32 Harvests = 0;

	/** Steep what's in the satchel: the last two herbs if they make a brew, otherwise the last one as a tea. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Orrery") FString Steep(ADaedalusHero* Hero);
	/** The brew two herbs make ("" if none): "<Constellation> Brew", "Eclipse Brew: <Name>" or "". */
	static FString BrewOf(const FString& A, const FString& B);

	void Say(const FString& Line);
	void Advance(int32 ToStep);
	/** One line each for the HUD. */
	FString MessageLine() const;
	FString QuestLine() const;
	FString SatchelLine() const;
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Orrery") FString State() const;

private:
	FString Message;
	double MessageAt = -100.0;
};

/** Anything on the island the hero can use with Interact (E / X). */
UCLASS(Abstract)
class DAEDALUSLINK_API ADaedalusUsable : public AActor
{
	GENERATED_BODY()

public:
	ADaedalusUsable();
	virtual FString Prompt(const ADaedalusHero* Hero) const { return TEXT("Use"); }
	virtual bool Use(ADaedalusHero* Hero) { return false; }
	/** The nearest usable thing within Reach of the hero, or null. */
	static ADaedalusUsable* Nearest(const ADaedalusHero* Hero, float Reach);

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<UStaticMeshComponent> Body;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<UPointLightComponent> Glow;

protected:
	/** Load /Game/Daedalus/Art/<Kind>/<Asset>/<Asset>/StaticMeshes/<Asset> into Body, if it shipped. */
	bool SetArt(const FString& Kind, const FString& Asset, float Scale = 1.f);
};

/** A starbloom plant: a bud until its sky hour, then it glows and can be harvested once a day. */
UCLASS()
class DAEDALUSLINK_API ADaedalusStarbloom : public ADaedalusUsable
{
	GENERATED_BODY()

public:
	ADaedalusStarbloom();
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Orrery") FString Species = TEXT("Duskmallow");
	UFUNCTION(BlueprintPure, Category = "Daedalus|Orrery") bool IsBlooming() const;
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;
	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;

private:
	bool bShownBloom = false;
	float LastHarvestHour = -100.f;   // in absolute island hours, so a bloom regrows the next day
	float AbsoluteHour() const;
};

/** The steeping kettle: clean water and herbs from the satchel make teas, brews and eclipse brews. */
UCLASS()
class DAEDALUSLINK_API ADaedalusKettle : public ADaedalusUsable
{
	GENERATED_BODY()

public:
	ADaedalusKettle();
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;

protected:
	virtual void BeginPlay() override;
};

/** The aqueduct's sand filter, clogged by the Long Storm until the hero reseats it. */
UCLASS()
class DAEDALUSLINK_API ADaedalusWaterFilter : public ADaedalusUsable
{
	GENERATED_BODY()

public:
	ADaedalusWaterFilter();
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;

protected:
	virtual void BeginPlay() override;
};

/** One of the twelve star charts the Long Storm scattered over the rim. */
UCLASS()
class DAEDALUSLINK_API ADaedalusStarChart : public ADaedalusUsable
{
	GENERATED_BODY()

public:
	ADaedalusStarChart();
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Orrery") FString Constellation = TEXT("Lantern");
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;
	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;
};

/** The Keeper of the Orrery: talks the hero through the logbook, one objective at a time. */
UCLASS()
class DAEDALUSLINK_API ADaedalusKeeper : public ADaedalusUsable
{
	GENERATED_BODY()

public:
	ADaedalusKeeper();
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<UTextRenderComponent> Name;

protected:
	virtual void BeginPlay() override;

private:
	int32 Talks = 0;
};
