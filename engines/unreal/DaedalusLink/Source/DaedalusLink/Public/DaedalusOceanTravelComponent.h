#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameFramework/Pawn.h"
#include "DaedalusOceanTravelCore.h"
#include "DaedalusOceanTravelComponent.generated.h"

class UStaticMeshComponent;

UENUM(BlueprintType, meta=(ScriptName="OceanVesselKind"))
enum class EDaedalusOceanVessel : uint8 { Boat, Submarine };

/** Server-owned travel identity for a possessed boat or submarine pawn. */
UCLASS()
class DAEDALUSLINK_API ADaedalusOceanVessel : public APawn
{
    GENERATED_BODY()
public:
    ADaedalusOceanVessel();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Ocean")
    TObjectPtr<UStaticMeshComponent> VesselMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Daedalus|Ocean")
    EDaedalusOceanVessel VesselType = EDaedalusOceanVessel::Boat;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Daedalus|Ocean")
    FString CurrentRealm;
};

USTRUCT(BlueprintType)
struct FDaedalusOceanDock
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Id;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Realm;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString ArrivalAnchor;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bUnderwater = false;
    // Authoritative world-space boarding position, in Unreal centimetres.
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FVector BoardingLocation = FVector::ZeroVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FVector ExitLocation = FVector::ZeroVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) double BoardingRadiusCm = 500.0;
};

USTRUCT(BlueprintType)
struct FDaedalusOceanConnection
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString DepartureId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString DestinationId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bBoats = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bSubmarines = false;
};

/** Server-side eligibility only. The realm loader consumes the returned route. */
UCLASS(ClassGroup=(Daedalus), meta=(BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusOceanTravelComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Daedalus|Ocean")
    bool BoardAtDock(AController* Player, ADaedalusOceanVessel* Vessel, const FString& DockId);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Ocean")
    bool DisembarkAtDock(AController* Player, ADaedalusOceanVessel* Vessel, const FString& DockId);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Ocean")
    bool ConfigureHost(const TArray<FString>& RegisteredRealms,
                       const TArray<FDaedalusOceanDock>& Docks,
                       const TArray<FDaedalusOceanConnection>& Connections);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Ocean")
    bool ResolveForPlayer(AController* Player, ADaedalusOceanVessel* Vessel,
                          const FString& DepartureId, const FString& DestinationId,
                          FString& DestinationRealm, FString& ArrivalAnchor) const;
private:
    DaedalusOceanTravel::DockRegistry Registry;
    UPROPERTY() TArray<FDaedalusOceanDock> ActiveDocks;
    TMap<TWeakObjectPtr<AController>, TWeakObjectPtr<APawn>> BoardingAvatars;
    bool IsHost() const;
};
