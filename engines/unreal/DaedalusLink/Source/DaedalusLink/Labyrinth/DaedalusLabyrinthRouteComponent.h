// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DaedalusLabyrinthRouteComponent.generated.h"

class UInstancedStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;

UENUM(BlueprintType)
enum class EDaedalusLabyrinthRouteStage : uint8 { MarkThreeTurns, ReturnToLectern, Complete };

UENUM(BlueprintType)
enum class EDaedalusLabyrinthRouteIntentKind : uint8 { MarkTurn, ReturnToLectern };

/** Approved Java LabyrinthRouteSession.View plus explicit native grid presentation metadata. */
USTRUCT(BlueprintType)
struct FDaedalusLabyrinthRouteView
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") FString PlayerId;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") FString RealmId;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") FString InstanceId;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") int64 Revision = -1;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") int32 Capacity = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") int32 Charges = 0;
    // X = Java x, Y = Java z. This is the maze plane, not Unreal XYZ block coordinates.
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") FIntPoint Lectern = FIntPoint::ZeroValue;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") TArray<FIntPoint> Marks;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") TArray<FIntPoint> LearnedTurns;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") EDaedalusLabyrinthRouteStage Stage = EDaedalusLabyrinthRouteStage::MarkThreeTurns;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") FVector GridOriginCm = FVector::ZeroVector;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") float GridYawDegrees = 0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") float CellSizeCm = 400;
};

/** Intent only. Host validates real realm, turn/proximity, debit and durable commit. */
USTRUCT(BlueprintType)
struct FDaedalusLabyrinthRouteIntent
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") FString PlayerId;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") FString RealmId;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") FString InstanceId;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") FString EventId;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") int64 ExpectedRevision = -1;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") EDaedalusLabyrinthRouteIntentKind Kind = EDaedalusLabyrinthRouteIntentKind::MarkTurn;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Labyrinth") FIntPoint Point = FIntPoint::ZeroValue;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusLabyrinthRouteIntentEvent,
    const FDaedalusLabyrinthRouteIntent&, Intent);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FDaedalusLabyrinthRouteViewEvent);

/**
 * Opt-in, owner-only presentation/intent boundary. Does not grant inventory, awards,
 * client mutation RPCs or a second route authority. Attach to an owned replicated pawn;
 * existing host code supplies committed Java views and consumes intents separately.
 */
UCLASS(ClassGroup=(Daedalus), meta=(BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusLabyrinthRouteComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UDaedalusLabyrinthRouteComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    /** Authority-only binding; maze instance changes require ClearHostRoute first. */
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Labyrinth")
    bool BindHostRoute(const FString& PlayerId, const FString& InstanceId,
        FVector GridOriginCm, float GridYawDegrees, float CellSizeCm = 400);
    /** Called after the Java/inventory save commit. Same revision must mean the same view. */
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Labyrinth")
    bool ApplyCommittedHostView(const FDaedalusLabyrinthRouteView& Approved);
    /** Call on realm departure/unpossession; clears this presentation, never the Java save. */
    UFUNCTION(BlueprintCallable, BlueprintAuthorityOnly, Category="Daedalus|Labyrinth")
    bool ClearHostRoute();

    UFUNCTION(BlueprintPure, Category="Daedalus|Labyrinth")
    FDaedalusLabyrinthRouteView GetRouteView() const { return RouteView; }
    /** No prediction/debit occurs. Keep OutIntent unchanged when retrying at the host. */
    UFUNCTION(BlueprintCallable, Category="Daedalus|Labyrinth")
    bool RequestTurnMark(FVector ObservedWorldPoint, const FString& CurrentRealm,
        FDaedalusLabyrinthRouteIntent& OutIntent);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Labyrinth")
    bool RequestLecternReturn(const FString& CurrentRealm, FDaedalusLabyrinthRouteIntent& OutIntent);
    UFUNCTION(BlueprintPure, Category="Daedalus|Labyrinth")
    FText LessonInstruction() const;
    UFUNCTION(BlueprintPure, Category="Daedalus|Labyrinth")
    bool GridPointToWorld(FIntPoint Point, FVector& WorldPoint) const;

    UPROPERTY(BlueprintAssignable, Category="Daedalus|Labyrinth") FDaedalusLabyrinthRouteIntentEvent OnRouteIntent;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|Labyrinth") FDaedalusLabyrinthRouteViewEvent OnRouteViewChanged;
    // Optional existing marker mesh/material. No content loads or default realm wiring.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Labyrinth|Presentation") TObjectPtr<UStaticMesh> ChalkMarkerMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Labyrinth|Presentation") TObjectPtr<UMaterialInterface> ChalkMarkerMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Labyrinth|Presentation") FVector MarkerScale = FVector(0.12, 0.12, 0.02);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Labyrinth|Presentation") float MarkerLiftCm = 2;
    // These are local input usability limits, not server authorization or approved balance.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Daedalus|Labyrinth|Input") float InteractionRadiusCm = 500;

private:
    UPROPERTY(ReplicatedUsing=OnRep_RouteView) FDaedalusLabyrinthRouteView RouteView;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> MarkerInstances;
    FString BoundPlayerId;
    FString BoundInstanceId;
    FVector BoundOrigin = FVector::ZeroVector;
    float BoundYaw = 0;
    float BoundCellSize = 400;
    UFUNCTION() void OnRep_RouteView();
    bool CanMakeIntent(const FString& CurrentRealm) const;
    bool MakeIntent(EDaedalusLabyrinthRouteIntentKind Kind, FIntPoint Point,
        FDaedalusLabyrinthRouteIntent& OutIntent);
    void RefreshMarkers();
};
