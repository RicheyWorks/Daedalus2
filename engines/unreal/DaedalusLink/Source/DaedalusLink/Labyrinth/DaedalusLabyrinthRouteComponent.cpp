// SPDX-License-Identifier: MIT
#include "DaedalusLabyrinthRouteComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "GameFramework/Pawn.h"
#include "Net/UnrealNetwork.h"

namespace
{
bool ValidId(const FString& Id)
{
    if (Id.Len() < 1 || Id.Len() > 128 || Id.TrimStartAndEnd().IsEmpty()) return false;
    for (TCHAR C : Id) if (C < 32 || (C >= 127 && C <= 159)) return false;
    return true;
}
bool Finite(const FVector& Value)
{
    return FMath::IsFinite(Value.X) && FMath::IsFinite(Value.Y) && FMath::IsFinite(Value.Z);
}
bool ValidPoint(FIntPoint Point)
{
    return Point.X >= -1000000 && Point.X <= 1000000 && Point.Y >= -1000000 && Point.Y <= 1000000;
}
bool LocallyOwned(const AActor* Owner)
{
    if (const APawn* Pawn = Cast<APawn>(Owner)) return Pawn->IsLocallyControlled();
    return false; // This personal route boundary is explicitly mounted on an owned pawn.
}
bool ValidView(const FDaedalusLabyrinthRouteView& View)
{
    if (!ValidId(View.PlayerId) || !ValidId(View.InstanceId) || View.RealmId != TEXT("LABYRINTH")
        || View.Revision < 0 || View.Revision > 512 || View.Capacity < 1 || View.Capacity > 512
        || View.Charges < 0 || View.Charges > 10000 || !ValidPoint(View.Lectern)
        || View.Marks.Num() > View.Capacity || View.LearnedTurns.Num() > 3) return false;
    TSet<FIntPoint> Active;
    for (FIntPoint Point : View.Marks)
    {
        if (!ValidPoint(Point) || Point == View.Lectern || Active.Contains(Point)) return false;
        Active.Add(Point);
    }
    TSet<FIntPoint> Learned;
    for (FIntPoint Point : View.LearnedTurns)
    {
        if (!ValidPoint(Point) || Point == View.Lectern || Learned.Contains(Point)) return false;
        Learned.Add(Point);
    }
    switch (View.Stage)
    {
    case EDaedalusLabyrinthRouteStage::MarkThreeTurns: return Learned.Num() < 3;
    case EDaedalusLabyrinthRouteStage::ReturnToLectern:
    case EDaedalusLabyrinthRouteStage::Complete: return Learned.Num() == 3;
    default: return false;
    }
}
bool SameView(const FDaedalusLabyrinthRouteView& A, const FDaedalusLabyrinthRouteView& B)
{
    return A.PlayerId == B.PlayerId && A.RealmId == B.RealmId && A.InstanceId == B.InstanceId
        && A.Revision == B.Revision && A.Capacity == B.Capacity && A.Charges == B.Charges
        && A.Lectern == B.Lectern && A.Marks == B.Marks && A.LearnedTurns == B.LearnedTurns && A.Stage == B.Stage;
}
}

UDaedalusLabyrinthRouteComponent::UDaedalusLabyrinthRouteComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
    SetIsReplicatedByDefault(true);
}

void UDaedalusLabyrinthRouteComponent::BeginPlay()
{
    Super::BeginPlay();
    if (APawn* Pawn = Cast<APawn>(GetOwner()))
        Pawn->ReceiveControllerChangedDelegate.AddDynamic(this, &UDaedalusLabyrinthRouteComponent::OnPawnControllerChanged);
    RefreshMarkers();
}

void UDaedalusLabyrinthRouteComponent::OnPawnControllerChanged(APawn* Pawn, AController* OldController, AController* NewController)
{
    if (!Pawn || Pawn != GetOwner() || OldController == NewController) return;
    // A new controller needs an explicit new host binding, including on reused pawns.
    if (Pawn->HasAuthority()) ClearHostRoute();
    else
    {
        // Owner-only clear replication may stop reaching the former owner. Clear locally.
        if (!Pawn->IsLocallyControlled()) RouteView = FDaedalusLabyrinthRouteView();
        OnRep_RouteView();
    }
}

void UDaedalusLabyrinthRouteComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME_CONDITION(UDaedalusLabyrinthRouteComponent, RouteView, COND_OwnerOnly);
}

bool UDaedalusLabyrinthRouteComponent::BindHostRoute(const FString& PlayerId, const FString& InstanceId,
    FVector GridOriginCm, float GridYawDegrees, float CellSizeCm)
{
    if (!GetOwner() || !GetOwner()->HasAuthority() || !Cast<APawn>(GetOwner())
        || !BoundPlayerId.IsEmpty() || !ValidId(PlayerId) || !ValidId(InstanceId)
        || !Finite(GridOriginCm) || !FMath::IsFinite(GridYawDegrees)
        || !FMath::IsFinite(CellSizeCm) || CellSizeCm < 1 || CellSizeCm > 100000) return false;
    BoundPlayerId = PlayerId;
    BoundInstanceId = InstanceId;
    BoundOrigin = GridOriginCm;
    BoundYaw = FMath::UnwindDegrees(GridYawDegrees);
    BoundCellSize = CellSizeCm;
    return true;
}

bool UDaedalusLabyrinthRouteComponent::ApplyCommittedHostView(const FDaedalusLabyrinthRouteView& Approved)
{
    if (!GetOwner() || !GetOwner()->HasAuthority() || BoundPlayerId.IsEmpty() || !ValidView(Approved)
        || Approved.PlayerId != BoundPlayerId || Approved.InstanceId != BoundInstanceId
        || Approved.Revision < RouteView.Revision) return false;
    if (Approved.Revision == RouteView.Revision) return SameView(Approved, RouteView);
    if (RouteView.Revision >= 0)
    {
        if (Approved.Capacity != RouteView.Capacity || Approved.Lectern != RouteView.Lectern
            || Approved.Charges > RouteView.Charges || Approved.LearnedTurns.Num() < RouteView.LearnedTurns.Num()
            || static_cast<uint8>(Approved.Stage) < static_cast<uint8>(RouteView.Stage)) return false;
        for (FIntPoint Point : RouteView.LearnedTurns) if (!Approved.LearnedTurns.Contains(Point)) return false;
    }
    RouteView = Approved;
    RouteView.GridOriginCm = BoundOrigin;
    RouteView.GridYawDegrees = BoundYaw;
    RouteView.CellSizeCm = BoundCellSize;
    OnRep_RouteView();
    GetOwner()->ForceNetUpdate();
    return true;
}

bool UDaedalusLabyrinthRouteComponent::ClearHostRoute()
{
    if (!GetOwner() || !GetOwner()->HasAuthority()) return false;
    BoundPlayerId.Reset();
    BoundInstanceId.Reset();
    RouteView = FDaedalusLabyrinthRouteView();
    OnRep_RouteView();
    GetOwner()->ForceNetUpdate();
    return true;
}

void UDaedalusLabyrinthRouteComponent::OnRep_RouteView()
{
    RefreshMarkers();
    OnRouteViewChanged.Broadcast();
}

bool UDaedalusLabyrinthRouteComponent::GridPointToWorld(FIntPoint Point, FVector& WorldPoint) const
{
    if (!ValidView(RouteView) || !ValidPoint(Point) || !Finite(RouteView.GridOriginCm)
        || !FMath::IsFinite(RouteView.CellSizeCm) || RouteView.CellSizeCm < 1
        || !FMath::IsFinite(RouteView.GridYawDegrees)) return false;
    WorldPoint = RouteView.GridOriginCm + FRotator(0, RouteView.GridYawDegrees, 0).RotateVector(
        FVector(static_cast<double>(Point.X) * RouteView.CellSizeCm,
                static_cast<double>(Point.Y) * RouteView.CellSizeCm, 0));
    return Finite(WorldPoint);
}

bool UDaedalusLabyrinthRouteComponent::CanMakeIntent(const FString& CurrentRealm) const
{
    return GetOwner() && LocallyOwned(GetOwner()) && CurrentRealm == TEXT("LABYRINTH")
        && ValidView(RouteView) && FMath::IsFinite(InteractionRadiusCm)
        && InteractionRadiusCm > 0 && InteractionRadiusCm <= 100000;
}

bool UDaedalusLabyrinthRouteComponent::MakeIntent(EDaedalusLabyrinthRouteIntentKind Kind, FIntPoint Point,
    FDaedalusLabyrinthRouteIntent& OutIntent)
{
    OutIntent = FDaedalusLabyrinthRouteIntent();
    OutIntent.PlayerId = RouteView.PlayerId;
    OutIntent.RealmId = RouteView.RealmId;
    OutIntent.InstanceId = RouteView.InstanceId;
    OutIntent.EventId = FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphens);
    OutIntent.ExpectedRevision = RouteView.Revision;
    OutIntent.Kind = Kind;
    OutIntent.Point = Point;
    OnRouteIntent.Broadcast(OutIntent);
    return true;
}

bool UDaedalusLabyrinthRouteComponent::RequestTurnMark(FVector ObservedWorldPoint, const FString& CurrentRealm,
    FDaedalusLabyrinthRouteIntent& OutIntent)
{
    if (!CanMakeIntent(CurrentRealm) || !Finite(ObservedWorldPoint)
        || !Finite(GetOwner()->GetActorLocation())
        || FVector::DistSquared(GetOwner()->GetActorLocation(), ObservedWorldPoint)
            > FMath::Square(static_cast<double>(InteractionRadiusCm))) return false;
    const FVector Local = FRotator(0, RouteView.GridYawDegrees, 0).UnrotateVector(ObservedWorldPoint - RouteView.GridOriginCm);
    const double X = Local.X / RouteView.CellSizeCm, Z = Local.Y / RouteView.CellSizeCm;
    if (!FMath::IsFinite(X) || !FMath::IsFinite(Z) || FMath::Abs(X) > 1000000 || FMath::Abs(Z) > 1000000) return false;
    const FIntPoint Point(FMath::RoundToInt(X), FMath::RoundToInt(Z));
    if (Point == RouteView.Lectern || RouteView.Marks.Contains(Point)
        || RouteView.Marks.Num() == RouteView.Capacity || RouteView.Charges == 0) return false;
    return MakeIntent(EDaedalusLabyrinthRouteIntentKind::MarkTurn, Point, OutIntent);
}

bool UDaedalusLabyrinthRouteComponent::RequestLecternReturn(const FString& CurrentRealm,
    FDaedalusLabyrinthRouteIntent& OutIntent)
{
    FVector LecternWorld;
    if (!CanMakeIntent(CurrentRealm) || RouteView.Stage != EDaedalusLabyrinthRouteStage::ReturnToLectern
        || !GridPointToWorld(RouteView.Lectern, LecternWorld) || !Finite(GetOwner()->GetActorLocation())
        || FVector::DistSquared(GetOwner()->GetActorLocation(), LecternWorld)
            > FMath::Square(static_cast<double>(InteractionRadiusCm))) return false;
    return MakeIntent(EDaedalusLabyrinthRouteIntentKind::ReturnToLectern, RouteView.Lectern, OutIntent);
}

FText UDaedalusLabyrinthRouteComponent::LessonInstruction() const
{
    if (!ValidView(RouteView)) return NSLOCTEXT("DaedalusLabyrinth", "Unavailable", "Route lesson unavailable.");
    switch (RouteView.Stage)
    {
    case EDaedalusLabyrinthRouteStage::MarkThreeTurns:
        return FText::Format(NSLOCTEXT("DaedalusLabyrinth", "MarkTurns", "Mark three deliberate turns: {0}/3. Chalk: {1}."),
            FText::AsNumber(RouteView.LearnedTurns.Num()), FText::AsNumber(RouteView.Charges));
    case EDaedalusLabyrinthRouteStage::ReturnToLectern:
        return NSLOCTEXT("DaedalusLabyrinth", "Return", "Return to the lectern. Your learned turns remain credited if chalk fades.");
    case EDaedalusLabyrinthRouteStage::Complete:
        return NSLOCTEXT("DaedalusLabyrinth", "Complete", "First route recorded. Chalk marks still help you find your way.");
    default: return FText::GetEmpty();
    }
}

void UDaedalusLabyrinthRouteComponent::RefreshMarkers()
{
    if (MarkerInstances) MarkerInstances->ClearInstances();
    if (!GetOwner() || !LocallyOwned(GetOwner()) || !ValidView(RouteView) || !ChalkMarkerMesh
        || !Finite(MarkerScale) || MarkerScale.X <= 0 || MarkerScale.Y <= 0 || MarkerScale.Z <= 0
        || !FMath::IsFinite(MarkerLiftCm)) return;
    if (!MarkerInstances)
    {
        MarkerInstances = NewObject<UInstancedStaticMeshComponent>(GetOwner());
        MarkerInstances->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        MarkerInstances->SetCanEverAffectNavigation(false);
        MarkerInstances->SetCastShadow(false);
        MarkerInstances->SetOnlyOwnerSee(true);
        MarkerInstances->SetMobility(EComponentMobility::Movable);
        // World transforms stay in the maze, even though the component belongs to a moving pawn.
        MarkerInstances->SetAbsolute(true, true, true);
        MarkerInstances->SetWorldTransform(FTransform::Identity);
        GetOwner()->AddInstanceComponent(MarkerInstances);
        MarkerInstances->RegisterComponent();
    }
    MarkerInstances->SetStaticMesh(ChalkMarkerMesh);
    if (ChalkMarkerMaterial) MarkerInstances->SetMaterial(0, ChalkMarkerMaterial);
    for (FIntPoint Point : RouteView.Marks)
    {
        FVector WorldPoint;
        if (GridPointToWorld(Point, WorldPoint))
        {
            WorldPoint.Z += MarkerLiftCm;
            MarkerInstances->AddInstance(FTransform(FRotator(0, RouteView.GridYawDegrees, 0), WorldPoint, MarkerScale), true);
        }
    }
}

void UDaedalusLabyrinthRouteComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if (APawn* Pawn = Cast<APawn>(GetOwner()))
        Pawn->ReceiveControllerChangedDelegate.RemoveDynamic(this, &UDaedalusLabyrinthRouteComponent::OnPawnControllerChanged);
    if (MarkerInstances) MarkerInstances->DestroyComponent();
    MarkerInstances = nullptr;
    Super::EndPlay(Reason);
}
