// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DaedalusSolReachJournal.generated.h"

class ADaedalusSkyDirector;

UENUM(BlueprintType)
enum class EDaedalusSolStage : uint8 { RestoreWaterworks, DiscoverRing, FeedKeeper, PortalReady };
UENUM(BlueprintType)
enum class EDaedalusSolKeeperPlace : uint8 { Well, Garden, Kitchen, Home };
UENUM(BlueprintType)
enum class EDaedalusSolSupply : uint8 { CleanWater, DirtyWater, Egg, Milk, Dawnleaf, Rillprism, Cinderbud, Stillmoss, Stridefern, Clearbell };

USTRUCT(BlueprintType)
struct FDaedalusSolSnapshot
{
    GENERATED_BODY()
    // This key must come from the existing authenticated deed service; it grants no ownership.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) FString DeedJournalKey;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) int32 Schema = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) int32 CleanWater = 20;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) int32 DirtyWater = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) int32 Eggs = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) int32 Milk = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) TArray<int32> Herbs = {3,3,3,3,3,3};
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) int32 Facts = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) int32 Discoveries = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) int32 KeeperMeals = 0;
};

USTRUCT(BlueprintType)
struct FDaedalusSolEffect
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName Id;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) double DurationSeconds = 0;
};

USTRUCT(BlueprintType)
struct FDaedalusSolBrewResult
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) bool bSuccess = false;
    UPROPERTY(BlueprintReadOnly) FName Effect;
    UPROPERTY(BlueprintReadOnly) double DurationSeconds = 0;
    UPROPERTY(BlueprintReadOnly) bool bDoubled = false;
    UPROPERTY(BlueprintReadOnly) FString Failure;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusSolJournalChanged, FDaedalusSolSnapshot, Snapshot);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusSolEnvironmentChanged, bool, bClueVisible, EDaedalusSolKeeperPlace, KeeperPlace);

/** Unique recipe/journal ledger only. Shared homestead owns thirst, animals and production.
 * Server Blueprint bindings deposit actual water/OnProduced outputs into this component.
 * No client RPC grants resources; ownership and disk persistence remain existing services.
 */
UCLASS(ClassGroup=(Daedalus), meta=(BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusSolReachJournal : public UActorComponent
{
    GENERATED_BODY()
public:
    UDaedalusSolReachJournal();
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Sol") TObjectPtr<ADaedalusSkyDirector> SkyDirector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Sol") TObjectPtr<AActor> HiddenStairMarker;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Sol", meta=(ClampMin="1")) float DiscoveryReachCm = 180.f;
    // Indices Dawnleaf, Rillprism, Cinderbud, Stillmoss, Stridefern, Clearbell. Empty ID refuses a centre.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Sol") TArray<FDaedalusSolEffect> Effects;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, ReplicatedUsing=OnRepSnapshot, SaveGame, Category="Daedalus|Sol") FDaedalusSolSnapshot Snapshot;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|Sol") FDaedalusSolJournalChanged OnJournalChanged;
    // Bind marker visibility/materials and keeper AI routes; fires only when the world-derived result changes.
    UPROPERTY(BlueprintAssignable, Category="Daedalus|Sol") FDaedalusSolEnvironmentChanged OnEnvironmentChanged;

    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Sol") bool Deposit(EDaedalusSolSupply Supply, int32 Amount);
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Sol") bool FilterWellWater();
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Sol") FDaedalusSolBrewResult BrewRing(const TArray<FName>& OrderedHerbs);
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Sol") bool CookAndShareCustard();
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Sol") bool DiscoverHiddenCistern();
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Sol") bool RestoreJournal(const FDaedalusSolSnapshot& Saved);
    UFUNCTION(BlueprintPure, Category="Daedalus|Sol") EDaedalusSolStage GetAdventureStage() const;
    UFUNCTION(BlueprintPure, Category="Daedalus|Sol") EDaedalusSolKeeperPlace GetKeeperPlace() const;
    UFUNCTION(BlueprintPure, Category="Daedalus|Sol") FString GetKeeperLine() const;
    UFUNCTION(BlueprintPure, Category="Daedalus|Sol") bool IsCisternClueVisible() const;
private:
    bool CanMutate() const;
    void Changed();
    void SampleEnvironment();
    bool bSampledEnvironment = false;
    bool bLastClueVisible = false;
    EDaedalusSolKeeperPlace LastKeeperPlace = EDaedalusSolKeeperPlace::Home;
    UFUNCTION() void OnRepSnapshot();
};
