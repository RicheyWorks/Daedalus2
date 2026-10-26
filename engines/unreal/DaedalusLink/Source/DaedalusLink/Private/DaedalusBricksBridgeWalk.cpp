// SPDX-License-Identifier: MIT
#include "DaedalusBricksBridgeWalk.h"
#include "DaedalusBricksBridgeWorkshop.h"
#include "DaedalusHero.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInterface.h"
#include "PhysicsEngine/BodyInstance.h"
#include "ProceduralMeshComponent.h"
#include "Templates/UnrealTemplate.h"
#include "UObject/ConstructorHelpers.h"

namespace DaedalusBridgeWalkLocal
{
    bool Placement(const FTransform& Pose)
    {
        return !Pose.ContainsNaN() && Pose.GetRotation().IsNormalized() && Pose.GetScale3D().Equals(FVector::OneVector,0.001) &&
            Pose.GetRotation().RotateVector(FVector::UpVector).Equals(FVector::UpVector,0.001);
    }
    bool LocalPlayer(const ADaedalusHero* Hero,const AActor* Walk,const APlayerController* Expected,bool Reach)
    {
        const auto PairAlive=[&]()
        {
            return IsInGameThread() && IsValid(Hero) && Hero->HasActorBegunPlay() && !Hero->IsActorBeingDestroyed() &&
                IsValid(Walk) && Walk->HasActorBegunPlay() && !Walk->IsActorBeingDestroyed() && Walk->GetWorld() &&
                Hero->GetWorld()==Walk->GetWorld() && Walk->GetWorld()->GetNetMode()==NM_Standalone;
        };
        if (!PairAlive() || !Hero->IsLocallyControlled() || !PairAlive()) return false;
        const auto* Player=Cast<APlayerController>(Hero->GetController());
        if (!IsValid(Player) || Player->IsActorBeingDestroyed() || !Player->HasActorBegunPlay() || Player->GetWorld()!=Walk->GetWorld() ||
            !Player->IsLocalController() || !PairAlive()) return false;
        if (!IsValid(Player) || Player->IsActorBeingDestroyed() || !Player->HasActorBegunPlay() || Player->GetWorld()!=Walk->GetWorld() ||
            Hero->GetController()!=Player || Player->GetPawn()!=Hero || !IsValid(Player->GetLocalPlayer()) || (Expected && Player!=Expected)) return false;
        if (!Reach) return true;
        const double Distance=FVector::DistSquared(Hero->GetActorLocation(),Walk->GetActorLocation());
        return FMath::IsFinite(Hero->InteractReach) && Hero->InteractReach>0 && FMath::IsFinite(Distance) &&
            Distance<=static_cast<double>(Hero->InteractReach)*Hero->InteractReach;
    }
    struct Ink
    {
        TArray<FVector> Vertices,Normals; TArray<int32> Triangles; TArray<FLinearColor> Colours;
        void Triangle(FVector A,FVector B,FVector C,FLinearColor Colour)
        {
            const int32 I=Vertices.Num(); const FVector N=FVector::CrossProduct(B-A,C-A).GetSafeNormal();
            Vertices.Append({A,B,C}); Normals.Append({N,N,N}); Triangles.Append({I,I+1,I+2}); Colours.Append({Colour,Colour,Colour});
        }
        void Quad(FVector A,FVector B,FVector C,FVector D,FLinearColor Colour)
        { Triangle(A,B,C,Colour); Triangle(A,C,D,Colour); }
        void Box(FVector Centre,FVector Half,FLinearColor Colour)
        {
            const double X=Centre.X,Y=Centre.Y,Z=Centre.Z,A=Half.X,B=Half.Y,C=Half.Z;
            Quad({X-A,Y-B,Z+C},{X+A,Y-B,Z+C},{X+A,Y+B,Z+C},{X-A,Y+B,Z+C},Colour);
            Quad({X-A,Y+B,Z-C},{X+A,Y+B,Z-C},{X+A,Y-B,Z-C},{X-A,Y-B,Z-C},Colour);
            Quad({X+A,Y-B,Z-C},{X+A,Y+B,Z-C},{X+A,Y+B,Z+C},{X+A,Y-B,Z+C},Colour*0.85f);
            Quad({X-A,Y+B,Z-C},{X-A,Y-B,Z-C},{X-A,Y-B,Z+C},{X-A,Y+B,Z+C},Colour*0.85f);
            Quad({X+A,Y+B,Z-C},{X-A,Y+B,Z-C},{X-A,Y+B,Z+C},{X+A,Y+B,Z+C},Colour*0.7f);
            Quad({X-A,Y-B,Z-C},{X+A,Y-B,Z-C},{X+A,Y-B,Z+C},{X-A,Y-B,Z+C},Colour*0.7f);
        }
    };
    FVector Centre(const daedalus::bridgewalk::Piece& Piece)
    { return FVector(Piece.CentreX,Piece.CentreY,daedalus::bridgewalk::DeckCentreZ); }
    FVector Half(const daedalus::bridgewalk::Piece& Piece)
    { return FVector(Piece.HalfX,Piece.HalfY,daedalus::bridgewalk::DeckHalfZ); }
}

ADaedalusBricksBridgeWalk::ADaedalusBricksBridgeWalk()
{
    PrimaryActorTick.bCanEverTick=true; PrimaryActorTick.bStartWithTickEnabled=false;
    PrimaryActorTick.TickGroup=TG_PostPhysics; PrimaryActorTick.TickInterval=0.05f;
    bReplicates=false; SetActorEnableCollision(false);
    WalkRoot=CreateDefaultSubobject<USceneComponent>(TEXT("BridgeWalkRoot")); RootComponent=WalkRoot;
    Body->SetupAttachment(WalkRoot); Glow->SetupAttachment(WalkRoot); Glow->SetIntensity(0); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Engine/EngineDebugMaterials/VertexColorMaterial.VertexColorMaterial")); InkMaterial=Material.Object;
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeLocation(FVector(0,0,65)); Body->SetRelativeScale3D(FVector(0.5,1.1,1.1));
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision); Body->SetCanEverAffectNavigation(false);
    ModelInk=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("FrozenBridgeInk")); ModelInk->SetupAttachment(WalkRoot);
    ModelInk->SetCollisionEnabled(ECollisionEnabled::NoCollision); ModelInk->SetCastShadow(false); ModelInk->SetCanEverAffectNavigation(false);
    for (int32 I=0;I<daedalus::bridgewalk::PieceCount;++I)
    {
        auto* Box=CreateDefaultSubobject<UBoxComponent>(*FString::Printf(TEXT("FrozenBridgePiece%d"),I)); Box->SetupAttachment(WalkRoot);
        Box->SetCollisionEnabled(ECollisionEnabled::NoCollision); Box->SetGenerateOverlapEvents(false);
        Box->SetCollisionObjectType(ECC_WorldStatic); Box->SetCollisionResponseToAllChannels(ECR_Ignore); Box->SetCollisionResponseToChannel(ECC_Pawn,ECR_Block);
        Box->SetCanEverAffectNavigation(false); Box->SetHiddenInGame(true); DeckPieces.Add(Box);
    }
    for (int32 I=0;I<daedalus::brickbridge::PadCount;++I)
    {
        auto* Label=CreateDefaultSubobject<UTextRenderComponent>(*FString::Printf(TEXT("FrozenBridgePad%d"),I)); Label->SetupAttachment(WalkRoot);
        Label->SetRelativeRotation(FRotator(90,0,0)); Label->SetWorldSize(8); Label->SetHorizontalAlignment(EHTA_Center);
        Label->SetVerticalAlignment(EVRTA_TextCenter); Label->SetTextRenderColor(FColor(20,25,35)); Label->SetVisibility(false); PadLabels.Add(Label);
    }
    Readout=CreateDefaultSubobject<UTextRenderComponent>(TEXT("BridgeWalkReadout")); Readout->SetupAttachment(WalkRoot);
    Readout->SetRelativeLocation(FVector(35,0,270)); Readout->SetWorldSize(13); Readout->SetHorizontalAlignment(EHTA_Center);
    Readout->SetVerticalAlignment(EVRTA_TextTop); Readout->SetTextRenderColor(FColor(25,35,50));
}
bool ADaedalusBricksBridgeWalk::Alive() const
{ return IsInGameThread() && !bEnding && HasActorBegunPlay() && !IsActorBeingDestroyed() && GetWorld(); }
bool ADaedalusBricksBridgeWalk::ViewsReady() const
{
    if (!Alive() || (!bAttempted && GetActorEnableCollision()) || !InkMaterial || !IsValid(WalkRoot) || GetRootComponent()!=WalkRoot ||
        WalkRoot->GetOwner()!=this || !WalkRoot->IsRegistered() || WalkRoot->GetAttachParent()!=nullptr ||
        !IsValid(Readout) || Readout->GetOwner()!=this || !Readout->IsRegistered() ||
        !IsValid(Body) || Body->GetOwner()!=this || !Body->IsRegistered() || !Body->GetStaticMesh() ||
        !IsValid(ModelInk) || ModelInk->GetOwner()!=this || !ModelInk->IsRegistered() || ModelInk->GetAttachParent()!=WalkRoot ||
        !ModelInk->GetRelativeTransform().Equals(FTransform::Identity,0.001) || ModelInk->GetCollisionEnabled()!=ECollisionEnabled::NoCollision ||
        DeckPieces.Num()!=daedalus::bridgewalk::PieceCount || PadLabels.Num()!=daedalus::brickbridge::PadCount) return false;
    for (const auto& Box:DeckPieces) if (!IsValid(Box) || Box->GetClass()!=UBoxComponent::StaticClass() || Box->GetOwner()!=this || !Box->IsRegistered() || Box->GetAttachParent()!=WalkRoot) return false;
    for (const auto& Label:PadLabels) if (!IsValid(Label) || Label->GetOwner()!=this || !Label->IsRegistered() || Label->GetAttachParent()!=WalkRoot) return false;
    return !bAttempted || (ModelInk->GetNumSections()>0 && ModelInk->GetMaterial(0));
}
void ADaedalusBricksBridgeWalk::Unavailable(const FString& Why) const
{ if (!bUnavailable) { bUnavailable=true; Fault=Why; } }
bool ADaedalusBricksBridgeWalk::SourceReady() const
{
    const auto* Source=SourceWorkshop.Get();
    return Alive() && IsValid(Source) && Source->GetWorld()==GetWorld() && !Source->IsActorBeingDestroyed() && Source->IsWorkshopReady();
}
bool ADaedalusBricksBridgeWalk::ObserveModel() const
{
    if (!Alive() || bUnavailable) return false;
    if (!ViewsReady()) { Unavailable(TEXT("Model display unavailable. Captured deck and visits are kept.")); return false; }
    if (!bAttempted) return true;
    if (!GetActorTransform().Equals(FrozenFrame,0.01))
    { Unavailable(TEXT("The model frame moved. Visits pause; its existing deck is retained.")); return false; }
    if (!bPrepared) return true;
    if (!GetActorEnableCollision() || !Builder.IsValid() || Builder->IsActorBeingDestroyed() || !Controller.IsValid() || Controller->IsActorBeingDestroyed() ||
        Builder->GetWorld()!=GetWorld() || Controller->GetWorld()!=GetWorld() || Builder->GetController()!=Controller.Get() || Controller->GetPawn()!=Builder.Get())
    { Unavailable(TEXT("The original builder or model changed. Existing deck and visits stay; use a new model.")); return false; }
    if (!DeckReady(true))
    { Unavailable(TEXT("A deck piece changed. Existing geometry stays; pad acknowledgements pause.")); return false; }
    return true;
}
bool ADaedalusBricksBridgeWalk::DeckReady(bool RequirePhysics) const
{
    if (!Alive() || !Model.Active() || DeckPieces.Num()!=daedalus::bridgewalk::PieceCount) return false;
    const auto& Pieces=Model.Geometry();
    for (int32 I=0;I<DeckPieces.Num();++I)
    {
        const auto* Box=DeckPieces[I].Get(); const auto& Piece=Pieces[static_cast<size_t>(I)];
        const FTransform Expected(DaedalusBridgeWalkLocal::Centre(Piece));
        if (!IsValid(Box) || Box->GetClass()!=UBoxComponent::StaticClass() || Box->GetOwner()!=this || !Box->IsRegistered() || Box->GetAttachParent()!=WalkRoot || !Box->GetRelativeTransform().Equals(Expected,0.01) ||
            !Box->GetUnscaledBoxExtent().Equals(DaedalusBridgeWalkLocal::Half(Piece),0.01) || Box->GetGenerateOverlapEvents() ||
            (RequirePhysics && Piece.Active && !Box->IsPhysicsStateCreated()) ||
            Box->GetCollisionResponseToChannel(ECC_Pawn)!=ECR_Block || Box->GetCollisionObjectType()!=ECC_WorldStatic)
            return false;
        // UE5.8 PrimitiveComponent::GetCollisionEnabled returns NoCollision
        // while the owner is disabled. Inspect this exact box's configured
        // body mode without owner/weld substitution before activation.
        const FBodyInstance* BodyState=Box->GetBodyInstance(NAME_None,false);
        const auto ExpectedMode=Piece.Active?ECollisionEnabled::QueryAndPhysics:ECollisionEnabled::NoCollision;
        if (!BodyState || BodyState->GetCollisionEnabled(false)!=ExpectedMode || (RequirePhysics && Box->GetCollisionEnabled()!=ExpectedMode)) return false;
    }
    return true;
}
bool ADaedalusBricksBridgeWalk::PawnSpaceClear(const daedalus::bridgewalk::Walk& Snapshot,const FTransform& Frame) const
{
    if (!Alive() || !DaedalusBridgeWalkLocal::Placement(Frame)) return false;
    FCollisionObjectQueryParams Objects; Objects.AddObjectTypesToQuery(ECC_Pawn);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DaedalusBridgeWalkSpace),false,this);
    for (const auto& Piece:Snapshot.Geometry()) if (Piece.Active)
    {
        const FVector Position=Frame.TransformPosition(DaedalusBridgeWalkLocal::Centre(Piece));
        if (GetWorld()->OverlapAnyTestByObjectType(Position,Frame.GetRotation(),Objects,FCollisionShape::MakeBox(DaedalusBridgeWalkLocal::Half(Piece)),Query)) return false;
        if (!Alive()) return false;
    }
    return true;
}
void ADaedalusBricksBridgeWalk::DrawModel()
{
    using namespace DaedalusBridgeWalkLocal;
    if (!Alive() || !Model.Active() || !IsValid(ModelInk) || ModelInk->GetOwner()!=this || !InkMaterial) return;
    Ink Drawing; const auto& Pieces=Model.Geometry();
    for (int32 I=0;I<daedalus::bridgewalk::PieceCount;++I)
    {
        const auto& Piece=Pieces[static_cast<size_t>(I)]; if (!Piece.Active) continue;
        const bool Pad=I<daedalus::brickbridge::PadCount;
        const FLinearColor Colour=Pad?(Model.WasVisited(I)?FLinearColor(0.15f,0.85f,0.5f):FLinearColor(1.f,0.7f,0.18f)):FLinearColor(0.13f,0.5f,0.9f);
        Drawing.Box(Centre(Piece),Half(Piece),Colour);
        if (Pad)
        {
            // Decorative studs have no collision; every blocking top stays35cm.
            for (int32 X:{-25,25}) for (int32 Y:{-25,25}) Drawing.Box(FVector(Piece.CentreX+X,Piece.CentreY+Y,36),FVector(6,6,1),Colour*0.85f);
        }
    }
    // A painted approach, never a new floor or an E/X control inside the deck.
    Drawing.Box(FVector(300,0,2),FVector(100,10,1),FLinearColor(0.13f,0.5f,0.9f));
    Drawing.Box(FVector(400,-100,2),FVector(10,100,1),FLinearColor(0.13f,0.5f,0.9f));
    Drawing.Box(FVector(550,-200,2),FVector(150,10,1),FLinearColor(0.13f,0.5f,0.9f));
    ModelInk->CreateMeshSection_LinearColor(0,Drawing.Vertices,Drawing.Triangles,Drawing.Normals,TArray<FVector2D>(),Drawing.Colours,TArray<FProcMeshTangent>(),false);
    if (!Alive() || !IsValid(ModelInk) || ModelInk->GetOwner()!=this) return; ModelInk->SetMaterial(0,InkMaterial);
}
void ADaedalusBricksBridgeWalk::Refresh()
{
    if (!Alive() || bNotifying) return; const uint64 Before=Epoch;
    if (bAttempted) ObserveModel();
    FString Text=TEXT("WALK YOUR BLUEPRINT\n");
    if (Model.Active())
    {
        Text+=FString::Printf(TEXT("%s / frozen plan\n%d of 9 pads visited\n"),UTF8_TO_TCHAR(daedalus::brickbridge::Blueprints[Model.Rule()].Name),Model.VisitedCount());
        for (int32 I=0;I<PadLabels.Num();++I) if (IsValid(PadLabels[I]) && PadLabels[I]->GetOwner()==this)
        {
            const auto Pad=Model.PadCentre(I);
            PadLabels[I]->SetRelativeLocation(FVector(Pad.X,Pad.Y,38));
            PadLabels[I]->SetText(FText::FromString(FString::Printf(TEXT("%d / %s"),I+1,Model.WasVisited(I)?TEXT("VISITED"):I==0?TEXT("HOME"):TEXT("PAD"))));
            PadLabels[I]->SetVisibility(true); if (!Alive() || Epoch!=Before) return;
        }
    }
    Text+=bUnavailable?Fault:Notice;
    if (IsValid(Readout) && Readout->GetOwner()==this) Readout->SetText(FText::FromString(Text));
    if (!Alive() || Epoch!=Before) return;
    TGuardValue<bool> Notification(bNotifying,true); OnViewChanged.Broadcast(this);
}
void ADaedalusBricksBridgeWalk::BeginPlay()
{
    bEnding=false; ++Epoch; Super::BeginPlay(); if (!Alive()) return; SetActorTickEnabled(false);
    Notice=TEXT("Finish a bound Bridge blueprint.\nE / X keeps a separate low model.\nNo source changes or rewards."); Refresh();
}
FString ADaedalusBricksBridgeWalk::Prompt(const ADaedalusHero* Hero) const
{
    if (!Alive() || GetWorld()->GetNetMode()!=NM_Standalone || !ObserveModel()) return TEXT("Bridge model unavailable; existing work kept");
    if (bPrepared) return Hero==Builder.Get()?FString::Printf(TEXT("Frozen model / %d of9 pads visited; follow blue paint"),Model.VisitedCount()):TEXT("Frozen model belongs to its original local builder");
    if (bAttempted) return TEXT("Model setup stopped; partial effects retained, no retry");
    return SourceReady()?TEXT("E / X: Keep a solved blueprint as a low walkable model"):TEXT("Bind a ready Bridge workshop to prepare a model");
}
bool ADaedalusBricksBridgeWalk::Use(ADaedalusHero* Hero)
{
    const uint64 Before=Epoch;
    if (!Alive() || bBusy || bNotifying || !DaedalusBridgeWalkLocal::LocalPlayer(Hero,this,nullptr,true) || !Alive() || Epoch!=Before) return false;
    TGuardValue<bool> Busy(bBusy,true);
    if (!ObserveModel()) { Refresh(); return false; }
    if (bAttempted) { Refresh(); return bPrepared && !bUnavailable; }
    if (!DaedalusBridgeWalkLocal::Placement(GetActorTransform()))
    { Notice=TEXT("Place upright at unit size on safe\nflat ground outside the obby/runway."); Refresh(); return false; }
    int32 Rule=-1,Mask=0; daedalus::bridgewalk::Walk Snapshot;
    auto* Source=SourceWorkshop.Get();
    if (!SourceReady() || !Source->CopyBlueprintSnapshot(Rule,Mask) || !Snapshot.Capture(Rule,Mask))
    { Notice=TEXT("The CURRENT source plan must connect\nall9 pads within its length limit.\nEarlier completion does not count."); Refresh(); return false; }
    const FTransform Frame=GetActorTransform();
    const TWeakObjectPtr<ADaedalusHero> Performer(Hero);
    const TWeakObjectPtr<APlayerController> Player(Cast<APlayerController>(Hero->GetController()));
    const auto CanCommit=[&]()
    {
        if (!Alive() || Epoch!=Before || !Player.IsValid() || !DaedalusBridgeWalkLocal::LocalPlayer(Performer.Get(),this,Player.Get(),true)) return false;
        return Alive() && Epoch==Before && ViewsReady() && !bUnavailable && GetActorTransform().Equals(Frame,0.01) &&
            Performer.IsValid() && Player.IsValid() && Performer->GetController()==Player.Get() && Player->GetPawn()==Performer.Get();
    };
    if (!CanCommit() || !PawnSpaceClear(Snapshot,Frame) || !CanCommit())
    { if (Alive()) { Notice=TEXT("Keep the low model footprint clear\nof every pawn, then try E / X.\nNo collision was added."); Refresh(); } return false; }
    bAttempted=true; FrozenFrame=Frame; Builder=Hero; Controller=Player; Model=Snapshot;
    // All boxes are built-in simple primitives: no procedural collision cook.
    // Configure while actor collision is off, then recheck occupancy before enable.
    const auto& Pieces=Model.Geometry();
    for (int32 I=0;I<DeckPieces.Num();++I)
    {
        auto* Box=DeckPieces[I].Get(); const auto& Piece=Pieces[static_cast<size_t>(I)];
        Box->SetRelativeTransform(FTransform(DaedalusBridgeWalkLocal::Centre(Piece)));
        Box->SetBoxExtent(DaedalusBridgeWalkLocal::Half(Piece),false);
        Box->SetCollisionEnabled(Piece.Active?ECollisionEnabled::QueryAndPhysics:ECollisionEnabled::NoCollision);
        if (!Alive() || Epoch!=Before) return false;
    }
    DrawModel();
    if (!CanCommit() || !DeckReady(false) || !PawnSpaceClear(Model,FrozenFrame) || !CanCommit() || !DeckReady(false))
    { if (Alive()) { Unavailable(TEXT("Model setup stopped. Its partial geometry is kept; no retry or replacement.")); Refresh(); } return false; }
    SetActorEnableCollision(true);
    if (!Alive() || Epoch!=Before) return false;
    if (!CanCommit() || !DeckReady(true))
    { if (Alive()) { Unavailable(TEXT("Setup changed while collision was enabled. The low deck stays; pad visits remain inactive.")); Refresh(); } return false; }
    bPrepared=true;
    if (!ObserveModel()) { Refresh(); return false; }
    Notice=TEXT("Follow blue paint to the35cm deck.\nWalk onto each numbered pad.\nSource Undo cannot change this copy.\nPad visits do not prove span traversal.");
    SetActorTickEnabled(true); Refresh(); return Alive() && !bUnavailable;
}
void ADaedalusBricksBridgeWalk::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!Alive() || bBusy || bNotifying || !bPrepared) return;
    const uint64 Before=Epoch;
    if (!ObserveModel()) { SetActorTickEnabled(false); Refresh(); return; }
    auto* Hero=Builder.Get(); auto* Player=Controller.Get();
    if (!DaedalusBridgeWalkLocal::LocalPlayer(Hero,this,Player,false) || !Alive() || Epoch!=Before || !ObserveModel()) return;
    const auto* Capsule=Hero->GetCapsuleComponent(); const auto* Movement=Hero->GetCharacterMovement();
    if (!IsValid(Capsule) || Capsule->GetOwner()!=Hero || !Capsule->IsRegistered() || !Capsule->GetUpVector().Equals(FVector::UpVector,0.001) ||
        !IsValid(Movement) || Movement->GetOwner()!=Hero || !Movement->IsRegistered()) return;
    const bool Grounded=Movement->IsMovingOnGround();
    if (!Alive() || Epoch!=Before || !ObserveModel() || Builder.Get()!=Hero || !IsValid(Capsule) || !IsValid(Movement) ||
        Hero->GetCapsuleComponent()!=Capsule || Hero->GetCharacterMovement()!=Movement || !Grounded || !Movement->CurrentFloor.IsWalkableFloor()) return;
    const auto* Floor=Movement->CurrentFloor.HitResult.GetComponent(); bool OwnFloor=false;
    for (int32 I=0;I<DeckPieces.Num();++I) if (Model.Geometry()[static_cast<size_t>(I)].Active && DeckPieces[I].Get()==Floor) { OwnFloor=true; break; }
    if (!OwnFloor) return;
    const double HalfHeight=Capsule->GetScaledCapsuleHalfHeight(); if (!FMath::IsFinite(HalfHeight) || HalfHeight<=0) return;
    const FVector Feet=FrozenFrame.InverseTransformPosition(Capsule->GetComponentLocation()-FVector(0,0,HalfHeight));
    TGuardValue<bool> Busy(bBusy,true); const int32 Pad=Model.Observe(Feet.X,Feet.Y,Feet.Z,true);
    if (Pad<0) return;
    const bool ReportAll=Model.VisitedCount()==daedalus::brickbridge::PadCount && !bAllReported;
    if (ReportAll) { bAllReported=true; SetActorTickEnabled(false); }
    Notice=ReportAll?TEXT("All9 pads visited! Your frozen\ncreation and visits stay here.\nNo item, reward or saved progress."):
        FString::Printf(TEXT("Pad%d visited / %d of9.\nLook at how your spans connect.\nVisit the remaining numbered pads."),Pad+1,Model.VisitedCount());
    DrawModel(); if (!Alive() || Epoch!=Before) return; Refresh();
    if (!Alive() || Epoch!=Before || !ObserveModel()) return;
    TGuardValue<bool> Notification(bNotifying,true); OnPadVisited.Broadcast(this,Pad+1,Model.VisitedCount());
    if (ReportAll && Alive() && Epoch==Before && ObserveModel()) OnAllPadsVisited.Broadcast(this);
}
void ADaedalusBricksBridgeWalk::EndPlay(const EEndPlayReason::Type Reason)
{
    bEnding=true; ++Epoch; SetActorTickEnabled(false);
    // Normal actor/component teardown only; never touch the source or a pawn.
    Super::EndPlay(Reason);
}
