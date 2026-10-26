#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameFramework/Pawn.h"
#include "InputCoreTypes.h"
#include "DaedalusOceanTravelCore.h"
#include "DaedalusOceanTravelComponent.generated.h"

class UStaticMeshComponent;
class UBoxComponent;
class USpringArmComponent;
class UCameraComponent;
class UInputMappingContext;
class UInputAction;
class APlayerController;
class ADaedalusOceanDockControl;
struct FInputActionValue;

UENUM(BlueprintType, meta=(ScriptName="OceanVesselKind"))
enum class EDaedalusOceanVessel : uint8 { Boat, Submarine };

/** Server-owned travel identity for a possessed boat or submarine pawn. */
UCLASS()
class DAEDALUSLINK_API ADaedalusOceanVessel : public APawn
{
    GENERATED_BODY()
public:
    ADaedalusOceanVessel();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual UInputComponent* CreatePlayerInputComponent() override;
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
    virtual void UnPossessed() override;
    virtual void OnRep_Controller() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    UFUNCTION(BlueprintCallable, Category="Daedalus|Ocean")
    bool SetLocalHelmInput(float Forward, float Turn, float Dive);
    UFUNCTION(Server, Unreliable, BlueprintCallable, Category="Daedalus|Ocean")
    void SetHelmInput(float Forward, float Turn, float Dive);
    UFUNCTION(Server,Reliable,BlueprintCallable,Category="Daedalus|Ocean")
    void RequestDockExit(ADaedalusOceanDockControl* Dock);
    /** Host configuration while unoccupied. Refuses a hull that would overlap blocking geometry. */
    UFUNCTION(BlueprintCallable, Category="Daedalus|Ocean")
    bool ConfigureHull(const FVector& HalfExtentCm);
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, ReplicatedUsing=OnRep_HullHalfExtent, Category="Daedalus|Ocean")
    FVector HullHalfExtentCm = FVector(180,80,70);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Replicated, Category="Daedalus|Ocean") float CruiseSpeedCm = 600;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Replicated, Category="Daedalus|Ocean") float SeaLevelCm = 0;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Replicated, Category="Daedalus|Ocean") float MaxDepthCm = 20000;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Ocean")
    TObjectPtr<UStaticMeshComponent> VesselMesh;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Ocean")
    TObjectPtr<UBoxComponent> HullCollision;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Ocean") TObjectPtr<USpringArmComponent> CameraBoom;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|Ocean") TObjectPtr<UCameraComponent> ChaseCamera;
    UPROPERTY(EditAnywhere, Category="Daedalus|Ocean|Controls") FKey ForwardKey = EKeys::W;
    UPROPERTY(EditAnywhere, Category="Daedalus|Ocean|Controls") FKey ReverseKey = EKeys::S;
    UPROPERTY(EditAnywhere, Category="Daedalus|Ocean|Controls") FKey LeftKey = EKeys::A;
    UPROPERTY(EditAnywhere, Category="Daedalus|Ocean|Controls") FKey RightKey = EKeys::D;
    UPROPERTY(EditAnywhere, Category="Daedalus|Ocean|Controls") FKey SurfaceKey = EKeys::SpaceBar;
    UPROPERTY(EditAnywhere, Category="Daedalus|Ocean|Controls") FKey DiveKey = EKeys::LeftControl;
    UPROPERTY(EditAnywhere, Category="Daedalus|Ocean|Controls") FKey InteractKey = EKeys::E;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Replicated, Category="Daedalus|Ocean")
    EDaedalusOceanVessel VesselType = EDaedalusOceanVessel::Boat;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Replicated, Category="Daedalus|Ocean")
    FString CurrentRealm;
private:
    UFUNCTION() void OnRep_HullHalfExtent();
    FVector Helm = FVector::ZeroVector;
    float InputAge = 1;
    float ForwardSpeed = 0;
    FVector LocalHelm = FVector::ZeroVector;
    float LocalAge = 1;
    float SendAge = 0;
    bool bLocalSender = false;
    UPROPERTY() TObjectPtr<UInputMappingContext> HelmMapping;
    UPROPERTY() TObjectPtr<UInputAction> ForwardAction;
    UPROPERTY() TObjectPtr<UInputAction> TurnAction;
    UPROPERTY() TObjectPtr<UInputAction> DiveAction;
    UPROPERTY() TObjectPtr<UInputAction> DockAction;
    TWeakObjectPtr<APlayerController> MappingController;
    void RemoveHelmMapping();
    void InputForward(const FInputActionValue& Value);
    void InputTurn(const FInputActionValue& Value);
    void InputDive(const FInputActionValue& Value);
    void InputDock();
};

USTRUCT(BlueprintType)
struct FDaedalusOceanDock
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Ocean") FString Id;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Ocean") FString Realm;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Ocean") FString ArrivalAnchor;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Ocean") bool bUnderwater = false;
    // Authoritative world-space boarding position, in Unreal centimetres.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Ocean") FVector BoardingLocation = FVector::ZeroVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Ocean") FVector ExitLocation = FVector::ZeroVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Ocean") double BoardingRadiusCm = 500.0;
};

USTRUCT(BlueprintType)
struct FDaedalusOceanConnection
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Ocean") FString DepartureId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Ocean") FString DestinationId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Ocean") bool bBoats = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Ocean") bool bSubmarines = false;
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
    struct BoardingState
    {
        TWeakObjectPtr<APawn> Avatar;
        TWeakObjectPtr<ADaedalusOceanVessel> Vessel;
        bool bCollision = true;
        bool bHidden = false;
    };
    TMap<TWeakObjectPtr<AController>, BoardingState> BoardingAvatars;
    bool IsHost() const;
};
