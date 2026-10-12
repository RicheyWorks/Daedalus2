// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameFramework/Actor.h"
#include "DaedalusHomestead.generated.h"

/**
 * Homestead gameplay prototypes (youtube-master island, Team Grok). Data: bot-team art NOTES youtube-master food_water.json.
 * - UDaedalusThirstComponent: thirst drains; at 0 it drains health. Drinking is mandatory.
 * - ADaedalusWaterSource: a placed water prop (tag Drinkable or RawWater). Walk within Reach and press Interact (or call Drink).
 * - ADaedalusBrewBench: Melody Brewing. 3-5 note-herbs IN ORDER -> a tune (contour/steps/cadence) -> a tonic (port of herbcombo.py).
 * - ADaedalusLivestock: fed + watered animals grow Calf->Adult->Elder and produce on a timer.
 */

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusThirstChanged, float, Thirst, float, Health);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FDaedalusMelodyBrewed, const FString&, Melody, const FString&, Tonic, const TArray<int32>&, Notes);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusProduced, const FString&, Species, const FString&, Product);

UCLASS(ClassGroup = (Daedalus), meta = (BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusThirstComponent : public UActorComponent
{
	GENERATED_BODY()
public:
	UDaedalusThirstComponent();
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Thirst") float Thirst = 100.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Thirst") float ThirstMax = 100.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Thirst") float DrainPerMinute = 2.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Thirst") float Health = 100.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Thirst") float HealthDrainPerSecondWhenDry = 1.f;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Thirst") bool bSick = false;
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Thirst") FDaedalusThirstChanged OnThirstChanged;

	/** Quality: "clean" +30, "raw" +20 with 25% sickness, "salt" -10. Returns the new thirst. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Thirst") float Drink(const FString& Quality);
	/** Find (or add) the component on an actor. */
	static UDaedalusThirstComponent* For(AActor* Actor);
private:
	float LastBroadcast = -1.f;
};

UCLASS()
class DAEDALUSLINK_API ADaedalusWaterSource : public AActor
{
	GENERATED_BODY()
public:
	ADaedalusWaterSource();
	virtual void Tick(float DeltaSeconds) override;
	/** clean, raw or salt. Filter/Boiler props set bTreats to turn raw/salt into clean for whoever drinks here. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Water") FString Quality = TEXT("clean");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Water") bool bTreats = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Water") float Reach = 250.f;
	/** Auto-sip when the player stands in reach and is thirsty (MVP stand-in for the Interact key). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Water") bool bAutoSip = true;
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Water") bool Drink(AActor* Drinker);
private:
	float Cooldown = 0.f;
};

USTRUCT(BlueprintType)
struct FDaedalusBrewResult
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Brew") FString Melody;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Brew") FString Tonic;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Brew") FString Effect;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Brew") bool bPurifiesWater = false;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Brew") int32 Tier = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Brew") float Magnitude = 0.f;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Brew") float DurationS = 0.f;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Brew") TArray<int32> Notes;
};

UCLASS()
class DAEDALUSLINK_API ADaedalusBrewBench : public AActor
{
	GENERATED_BODY()
public:
	ADaedalusBrewBench();
	/** Herbs by name (Doleaf..Tisquill) IN THE ORDER ADDED, with stages 1-4. Same rules as herbcombo.py. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Brew") FDaedalusBrewResult Brew(const TArray<FString>& Herbs, const TArray<int32>& Stages);
	static FDaedalusBrewResult BrewStatic(const TArray<FString>& Herbs, const TArray<int32>& Stages);
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Brew") FDaedalusMelodyBrewed OnMelodyBrewed;
};

UCLASS()
class DAEDALUSLINK_API ADaedalusLivestock : public AActor
{
	GENERATED_BODY()
public:
	ADaedalusLivestock();
	virtual void Tick(float DeltaSeconds) override;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Livestock") FString Species = TEXT("Mooncalf");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Livestock") FString Age = TEXT("Calf");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Livestock") FString Product = TEXT("Milk");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Livestock") float ProduceEveryMin = 6.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Livestock") float GrowAdultMin = 20.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Livestock") float GrowElderMin = 180.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Livestock") float StarveAfterMin = 30.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Livestock") float TroughReach = 1500.f;
	/** Speeds the clocks for testing (60 = one game minute per real second). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Livestock") float TimeScale = 1.f;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Livestock") int32 ProducedCount = 0;
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Livestock") FDaedalusProduced OnProduced;
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Livestock") void Feed();
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Livestock") bool HasWater() const;
private:
	float AgeMin = 0.f, SinceFedMin = 0.f, SinceProduceMin = 0.f;
};
