// SPDX-License-Identifier: MIT
#include "DaedalusBricksBlueprintTrail.h"
#include "DaedalusBricksBridgeWorkshop.h"
#include "DaedalusBricksSkylineWorkshop.h"
#include "DaedalusHero.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInterface.h"
#include "ProceduralMeshComponent.h"
#include "Templates/UnrealTemplate.h"
#include "UObject/ConstructorHelpers.h"

namespace DaedalusBlueprintTrailLocal
{
    bool Placement(const FTransform& Pose)
    {
        return !Pose.ContainsNaN() && Pose.GetRotation().IsNormalized() && Pose.GetScale3D().Equals(FVector::OneVector,0.001) &&
            Pose.GetRotation().RotateVector(FVector::UpVector).Equals(FVector::UpVector,0.001);
    }
    bool LocalReach(const ADaedalusHero* Hero,const AActor* Trail,const APlayerController* Expected=nullptr)
    {
        const auto PairAlive=[&]()
        {
            return IsInGameThread() && IsValid(Hero) && !Hero->IsActorBeingDestroyed() && Hero->HasActorBegunPlay() && IsValid(Trail) &&
                !Trail->IsActorBeingDestroyed() && Trail->HasActorBegunPlay() && Trail->GetWorld() && Hero->GetWorld()==Trail->GetWorld() &&
                Trail->GetWorld()->GetNetMode()==NM_Standalone && FMath::IsFinite(Hero->InteractReach) && Hero->InteractReach>0.f;
        };
        if (!PairAlive() || !Hero->IsLocallyControlled() || !PairAlive()) return false;
        const auto* Player=Cast<APlayerController>(Hero->GetController());
        if (!IsValid(Player) || Player->IsActorBeingDestroyed() || !Player->HasActorBegunPlay() || Player->GetWorld()!=Trail->GetWorld() || !Player->IsLocalController() || !PairAlive()) return false;
        if (!IsValid(Player) || Player->IsActorBeingDestroyed() || !Player->HasActorBegunPlay() || Player->GetWorld()!=Trail->GetWorld() || Hero->GetController()!=Player ||
            Player->GetPawn()!=Hero || !IsValid(Player->GetLocalPlayer()) || (Expected && Player!=Expected)) return false;
        const double D=FVector::DistSquared(Hero->GetActorLocation(),Trail->GetActorLocation());
        return FMath::IsFinite(D) && D<=static_cast<double>(Hero->InteractReach)*Hero->InteractReach;
    }
    FString Wrap(const FString& Text)
    {
        TArray<FString> Lines; Text.ParseIntoArrayLines(Lines,false); FString Out;
        for (int32 I=0;I<Lines.Num();++I)
        {
            if (I) Out+=TEXT("\n"); TArray<FString> Words; Lines[I].ParseIntoArray(Words,TEXT(" "),true); int32 Columns=0;
            for (const auto& Word:Words)
            {
                if (Columns && Columns+1+Word.Len()>42) { Out+=TEXT("\n"); Columns=0; }
                if (Columns) { Out+=TEXT(" "); ++Columns; } Out+=Word; Columns+=Word.Len();
            }
        }
        return Out;
    }
    struct Ink
    {
        TArray<FVector> Vertices; TArray<int32> Triangles; TArray<FLinearColor> Colours;
        void Triangle(FVector A,FVector B,FVector C,FLinearColor Colour)
        { const int32 At=Vertices.Num(); Vertices.Append({A,B,C}); Triangles.Append({At,At+1,At+2}); Colours.Append({Colour,Colour,Colour}); }
        void Line(FVector A,FVector B,double Width,FLinearColor Colour)
        {
            const FVector D=(B-A).GetSafeNormal(),S(-D.Y*Width,D.X*Width,0);
            Triangle(A-S,B-S,B+S,Colour); Triangle(A-S,B+S,A+S,Colour);
        }
        void Arrow(FVector At,FVector Direction,FLinearColor Colour)
        { const FVector D=Direction.GetSafeNormal(),S(-D.Y*16,D.X*16,0); Triangle(At+D*28,At-D*20+S,At-D*20-S,Colour); }
    };
}

ADaedalusBricksBlueprintTrail::ADaedalusBricksBlueprintTrail()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    TrailRoot=CreateDefaultSubobject<USceneComponent>(TEXT("BlueprintTrailRoot")); RootComponent=TrailRoot;
    Body->SetupAttachment(TrailRoot); Glow->SetupAttachment(TrailRoot); Glow->SetIntensity(0.f); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Engine/EngineDebugMaterials/VertexColorMaterial.VertexColorMaterial")); InkMaterial=Material.Object;
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeLocation(FVector(0,0,65)); Body->SetRelativeScale3D(FVector(0.5,0.9,1.1)); Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Wayfinding=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("BlueprintGroundTrail")); Wayfinding->SetupAttachment(TrailRoot);
    Wayfinding->SetCollisionEnabled(ECollisionEnabled::NoCollision); Wayfinding->SetCastShadow(false);
    Title=CreateDefaultSubobject<UTextRenderComponent>(TEXT("BlueprintTrailTitle")); Title->SetupAttachment(TrailRoot);
    Title->SetRelativeLocation(FVector(30,0,300)); Title->SetWorldSize(19.f); Title->SetHorizontalAlignment(EHTA_Center); Title->SetTextRenderColor(FColor(25,40,60));
    Readout=CreateDefaultSubobject<UTextRenderComponent>(TEXT("BlueprintTrailReadout")); Readout->SetupAttachment(TrailRoot);
    Readout->SetRelativeLocation(FVector(30,0,270)); Readout->SetWorldSize(11.f); Readout->SetHorizontalAlignment(EHTA_Center);
    Readout->SetVerticalAlignment(EVRTA_TextTop); Readout->SetTextRenderColor(FColor(25,40,60));
    BridgeSign=CreateDefaultSubobject<UTextRenderComponent>(TEXT("BridgeTrailSign")); BridgeSign->SetupAttachment(TrailRoot);
    BridgeSign->SetRelativeLocation(FVector(-80,-850,170)); BridgeSign->SetWorldSize(17.f); BridgeSign->SetHorizontalAlignment(EHTA_Center);
    BridgeSign->SetTextRenderColor(FColor(25,40,60)); BridgeSign->SetText(FText::FromString(TEXT("1 / BRIDGE\nFollow the green spans")));
    SkylineSign=CreateDefaultSubobject<UTextRenderComponent>(TEXT("SkylineTrailSign")); SkylineSign->SetupAttachment(TrailRoot);
    SkylineSign->SetRelativeLocation(FVector(-80,850,170)); SkylineSign->SetWorldSize(17.f); SkylineSign->SetHorizontalAlignment(EHTA_Center);
    SkylineSign->SetTextRenderColor(FColor(25,40,60)); SkylineSign->SetText(FText::FromString(TEXT("2 / SKYLINE\nFollow the gold towers")));
}
bool ADaedalusBricksBlueprintTrail::Alive() const
{ return IsInGameThread() && !bEnding && !IsActorBeingDestroyed() && HasActorBegunPlay() && GetWorld(); }
bool ADaedalusBricksBlueprintTrail::ViewsReady() const
{
    if (!Alive() || !InkMaterial || !IsValid(Wayfinding) || Wayfinding->GetOwner()!=this || !Wayfinding->IsRegistered() ||
        Wayfinding->GetNumSections()<1 || !Wayfinding->GetMaterial(0) || !IsValid(Body) || Body->GetOwner()!=this || !Body->IsRegistered() || !Body->GetStaticMesh()) return false;
    for (const auto* Label:{Title.Get(),Readout.Get(),BridgeSign.Get(),SkylineSign.Get()})
        if (!IsValid(Label) || Label->GetOwner()!=this || !Label->IsRegistered()) return false;
    return true;
}
void ADaedalusBricksBlueprintTrail::Unavailable(const FString& Why) const
{ if (!bUnavailable) { bUnavailable=true; Fault=Why; } }
bool ADaedalusBricksBlueprintTrail::StationReady(const AActor* Station,const FTransform& Expected,int32 Lane,bool Begun) const
{
    const UClass* Type=Lane==0?ADaedalusBricksBridgeWorkshop::StaticClass():ADaedalusBricksSkylineWorkshop::StaticClass();
    if (!Alive() || !IsValid(Station) || Station->IsActorBeingDestroyed() || Station->GetClass()!=Type || Station->GetOwner()!=this ||
        !IsValid(Station->GetRootComponent()) || Station->GetRootComponent()->GetAttachParent()!=nullptr ||
        Station->GetWorld()!=GetWorld() || Station->GetActorEnableCollision() || !Station->GetActorTransform().Equals(Expected,0.01) ||
        (Begun && !Station->HasActorBegunPlay())) return false;
    if (!Begun) return true;
    return Lane==0?Cast<ADaedalusBricksBridgeWorkshop>(Station)->IsWorkshopReady():Cast<ADaedalusBricksSkylineWorkshop>(Station)->IsWorkshopReady();
}
bool ADaedalusBricksBlueprintTrail::ObservePrepared() const
{
    if (!Alive() || bUnavailable) return false;
    if (bSetupAttempted && !ViewsReady())
    { Unavailable(TEXT("The trail display became unavailable. Existing workshops and study notes stay in place.")); return false; }
    if (bSetupAttempted && !GetActorTransform().Equals(FrozenTrail,0.01))
    { Unavailable(TEXT("The trail marker moved. Existing workshops and study notes stay; use a new trail.")); return false; }
    if (!bPrepared) return true; // Pending BeginPlay views cannot certify two stations.
    if (Bridge.Get()!=BridgeIdentity || Skyline.Get()!=SkylineIdentity || !StationReady(Bridge,ExpectedBridge,0,true) || !StationReady(Skyline,ExpectedSkyline,1,true))
    { Unavailable(TEXT("A workshop moved, changed or became unavailable. Existing practice and study notes are kept.")); return false; }
    return true;
}
int32 ADaedalusBricksBlueprintTrail::StudiedCount() const
{ int32 Count=0; for (int32 I=0;I<3;++I) { if (BridgeNotes[I]) ++Count; if (SkylineNotes[I]) ++Count; } return Count; }
void ADaedalusBricksBlueprintTrail::DrawWayfinding()
{
    if (!Alive() || !IsValid(Wayfinding) || Wayfinding->GetOwner()!=this || !Wayfinding->IsRegistered() || !InkMaterial) return;
    DaedalusBlueprintTrailLocal::Ink Ink;
    for (int32 Lane=0;Lane<2;++Lane)
    {
        const double Y=Lane?1300:-1300; const FLinearColor Colour=Lane?FLinearColor(0.95f,0.63f,0.08f):FLinearColor(0.05f,0.65f,0.42f);
        Ink.Line(FVector(-80,0,3),FVector(-80,Y,3),13,Colour); Ink.Line(FVector(-80,Y,3),FVector(-250,Y,3),13,Colour);
        for (int32 Mark=1;Mark<=4;++Mark) Ink.Arrow(FVector(-80,Y*Mark/5,4),FVector(0,Lane?1:-1,0),Colour);
        Ink.Arrow(FVector(-210,Y,4),FVector(-1,0,0),Colour);
    }
    TArray<FVector> Normals; Normals.Init(FVector::UpVector,Ink.Vertices.Num());
    Wayfinding->CreateMeshSection_LinearColor(0,Ink.Vertices,Ink.Triangles,Normals,TArray<FVector2D>(),Ink.Colours,TArray<FProcMeshTangent>(),false);
    if (!Alive() || !IsValid(Wayfinding) || Wayfinding->GetOwner()!=this) return;
    Wayfinding->SetMaterial(0,InkMaterial);
}
void ADaedalusBricksBlueprintTrail::Refresh()
{
    if (!Alive() || bNotifying) return;
    const uint64 StartEpoch=Epoch; bool Report=false;
    if (bPrepared && ObservePrepared())
    {
        for (int32 I=0;I<3;++I)
        { BridgeNotes[I]=BridgeNotes[I] || Bridge->WasBlueprintStudied(I); SkylineNotes[I]=SkylineNotes[I] || Skyline->WasBlueprintStudied(I); }
        if (StudiedCount()==6 && !bEverReported) { bEverReported=true; Report=true; }
    }
    FString Text=FString::Printf(TEXT("BLUEPRINT TRAIL / %d OF 6 STUDIED\n"),StudiedCount());
    if (bPrepared)
    {
        Text+=TEXT("1 / BRIDGE: "); for (int32 I=0;I<3;++I) Text+=FString::Printf(TEXT("%d %s%s"),I+1,BridgeNotes[I]?TEXT("DONE"):TEXT("OPEN"),I==2?TEXT("\n"):TEXT(" / "));
        Text+=TEXT("2 / SKYLINE: "); for (int32 I=0;I<3;++I) Text+=FString::Printf(TEXT("%d %s%s"),I+1,SkylineNotes[I]?TEXT("DONE"):TEXT("OPEN"),I==2?TEXT("\n"):TEXT(" / "));
    }
    Text+=bUnavailable?Fault:Notice;
    if (IsValid(Title) && Title->GetOwner()==this) Title->SetText(FText::FromString(TEXT("BUILD / CONNECT / LOOK")));
    if (!Alive() || Epoch!=StartEpoch) return;
    if (IsValid(Readout) && Readout->GetOwner()==this) Readout->SetText(FText::FromString(DaedalusBlueprintTrailLocal::Wrap(Text)));
    if (!Alive() || Epoch!=StartEpoch) return;
    TGuardValue<bool> Notification(bNotifying,true); OnViewChanged.Broadcast(this);
    if (Report && Alive() && Epoch==StartEpoch && ObservePrepared()) OnBlueprintTrailStudied.Broadcast(this);
}
void ADaedalusBricksBlueprintTrail::BeginPlay()
{
    bEnding=false; ++Epoch; Super::BeginPlay(); if (!Alive()) return;
    DrawWayfinding(); if (!Alive()) return;
    Notice=TEXT("E / X prepares two local workshops. Study three bridge plans and three skyline plans in any order. Follow the numbered paths; Undo stays available at both stations.");
    Refresh(); // Explicit first use only: no child actor or file is created here.
}
FString ADaedalusBricksBlueprintTrail::Prompt(const ADaedalusHero*) const
{
    if (!Alive() || GetWorld()->GetNetMode()!=NM_Standalone || !ViewsReady()) return TEXT("Blueprint trail is unavailable here");
    if (!ObservePrepared()) return TEXT("Trail unavailable; existing workshops and notes are kept");
    if (!bSetupAttempted) return TEXT("E / X: Prepare the bridge and skyline teaching trail");
    return bPrepared?FString::Printf(TEXT("E / X: Trail notes / %d of 6 studied; follow paths 1 and 2"),StudiedCount()):TEXT("Trail setup stopped; partial workshops are kept, with no retry");
}
void ADaedalusBricksBlueprintTrail::RememberEffect(AActor* Actor)
{ if (Alive() && IsValid(Actor)) SetupEffects.AddUnique(Actor); }
void ADaedalusBricksBlueprintTrail::UnbindEffect(AActor* Actor)
{
    if (!IsValid(Actor)) return;
    Actor->OnEndPlay.RemoveDynamic(this,&ADaedalusBricksBlueprintTrail::WorkshopEnded);
    if (auto* Workshop=Cast<ADaedalusBricksBridgeWorkshop>(Actor)) Workshop->OnViewChanged.RemoveDynamic(this,&ADaedalusBricksBlueprintTrail::BridgeViewChanged);
    if (auto* Workshop=Cast<ADaedalusBricksSkylineWorkshop>(Actor)) Workshop->OnViewChanged.RemoveDynamic(this,&ADaedalusBricksBlueprintTrail::SkylineViewChanged);
}
bool ADaedalusBricksBlueprintTrail::Use(ADaedalusHero* Hero)
{
    if (!Alive() || bBusy || bNotifying || !DaedalusBlueprintTrailLocal::LocalReach(Hero,this)) return false;
    if (!Alive()) return false;
    TGuardValue<bool> Busy(bBusy,true);
    if (!ViewsReady()) { Notice=TEXT("The trail display is unavailable. Existing workshops and notes are kept."); Refresh(); return false; }
    if (!ObservePrepared()) { Refresh(); return false; }
    if (bSetupAttempted) { Refresh(); return bPrepared && !bUnavailable; }
    if (!DaedalusBlueprintTrailLocal::Placement(GetActorTransform()))
    { Notice=TEXT("Place this trail upright at its original size on existing safe ground, then try E / X again."); Refresh(); return false; }
    bSetupAttempted=true; FrozenTrail=GetActorTransform(); const uint64 StartEpoch=Epoch;
    ExpectedBridge=FTransform(FVector(-900,-1300,0))*FrozenTrail; ExpectedSkyline=FTransform(FVector(-900,1300,0))*FrozenTrail;
    const TWeakObjectPtr<ADaedalusHero> Performer(Hero);
    const TWeakObjectPtr<APlayerController> Controller(Cast<APlayerController>(Hero->GetController()));
    const TWeakObjectPtr<ADaedalusBricksBlueprintTrail> Self(this);
    const auto ParticipantsReady=[&]()
    {
        auto* Player=Controller.Get();
        if (!Alive() || Epoch!=StartEpoch || !IsValid(Player) || !DaedalusBlueprintTrailLocal::LocalReach(Performer.Get(),this,Player)) return false;
        return Alive() && Epoch==StartEpoch && !bUnavailable && ViewsReady() && GetActorTransform().Equals(FrozenTrail,0.01) &&
            Controller.Get()==Player && IsValid(Performer.Get()) && Performer->GetController()==Player && Player->GetPawn()==Performer.Get();
    };
    const auto SpawnStation=[&](int32 Lane)->bool
    {
        if (!ParticipantsReady() || (Lane==1 && !StationReady(Bridge,ExpectedBridge,0,true))) return false;
        const FTransform Expected=Lane==0?ExpectedBridge:ExpectedSkyline;
        UClass* Type=Lane==0?ADaedalusBricksBridgeWorkshop::StaticClass():ADaedalusBricksSkylineWorkshop::StaticClass();
        TWeakObjectPtr<AActor> Staged; const AActor* StagedIdentity=nullptr;
        FActorSpawnParameters Parameters; Parameters.Owner=this; Parameters.ObjectFlags=RF_Transient|RF_DuplicateTransient; Parameters.bDeferConstruction=true;
        Parameters.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        Parameters.CustomPreSpawnInitialization=[Self,StartEpoch,Lane,Type,&Staged,&StagedIdentity](AActor* Actor)
        {
            if (!Actor || Actor->GetClass()!=Type) return;
            Staged=Actor; StagedIdentity=Actor; auto* Trail=Self.Get();
            if (!Trail || !Trail->Alive() || Trail->Epoch!=StartEpoch) return;
            Trail->RememberEffect(Actor);
            if (Lane==0) { Trail->Bridge=Cast<ADaedalusBricksBridgeWorkshop>(Actor); Trail->BridgeIdentity=Actor; }
            else { Trail->Skyline=Cast<ADaedalusBricksSkylineWorkshop>(Actor); Trail->SkylineIdentity=Actor; }
            Actor->OnEndPlay.AddUniqueDynamic(Trail,&ADaedalusBricksBlueprintTrail::WorkshopEnded);
            if (auto* Workshop=Cast<ADaedalusBricksBridgeWorkshop>(Actor)) Workshop->OnViewChanged.AddUniqueDynamic(Trail,&ADaedalusBricksBlueprintTrail::BridgeViewChanged);
            if (auto* Workshop=Cast<ADaedalusBricksSkylineWorkshop>(Actor)) Workshop->OnViewChanged.AddUniqueDynamic(Trail,&ADaedalusBricksBlueprintTrail::SkylineViewChanged);
            Actor->SetActorEnableCollision(false);
        };
        auto* Candidate=GetWorld()->SpawnActor<AActor>(Type,Expected,Parameters);
        // Normal EndPlay can run inside SpawnActor before Owner is assigned.
        // Reconcile both exact attempt identities after return; a null/different
        // return never proves that the staged actor had no effect.
        const auto ReconcileEnded=[&]()
        {
            TArray<TWeakObjectPtr<AActor>> Effects;
            if (IsValid(Candidate)) Effects.AddUnique(TWeakObjectPtr<AActor>(Candidate));
            if (Staged.IsValid()) Effects.AddUnique(Staged);
            for (const auto& Effect:Effects) UnbindEffect(Effect.Get());
            for (const auto& Effect:Effects) if (auto* Actor=Effect.Get())
                if (!Actor->IsActorBeingDestroyed() && Actor->GetOwner()==this) Actor->Destroy();
        };
        if (!Alive()) { ReconcileEnded(); return false; }
        RememberEffect(Candidate); // Live failures keep every tracked effect.
        const auto Valid=[&](bool Begun)
        {
            return ParticipantsReady() && (Lane==0 || StationReady(Bridge,ExpectedBridge,0,true)) && Candidate==StagedIdentity && Staged.Get()==Candidate &&
                (Lane==0?Bridge.Get()==Candidate:Skyline.Get()==Candidate) && StationReady(Candidate,Expected,Lane,Begun);
        };
        if (!Valid(false)) return false;
        Candidate->FinishSpawning(Expected);
        if (!Alive()) { ReconcileEnded(); return false; }
        return Valid(true);
    };
    const bool Ready=SpawnStation(0) && SpawnStation(1) && ParticipantsReady() &&
        StationReady(Bridge,ExpectedBridge,0,true) && StationReady(Skyline,ExpectedSkyline,1,true);
    if (!Alive()) return false;
    if (!Ready)
    {
        Unavailable(TEXT("The teaching trail could not finish setup. Any partial workshops and their practice stay in place. No retry or replacement is made; use a new trail."));
        Refresh(); return false;
    }
    bPrepared=true;
    Notice=TEXT("Both workshops are ready. Follow 1 for three bridge plans and 2 for three skyline plans. Use Next Blueprint at each station. First study notes stay even when you Undo or restart a plan.");
    Refresh(); return Alive() && !bUnavailable;
}
void ADaedalusBricksBlueprintTrail::BridgeViewChanged(ADaedalusBricksBridgeWorkshop* ChangedWorkshop)
{
    if (!Alive() || ChangedWorkshop!=BridgeIdentity || !bPrepared) return;
    ObservePrepared(); if (!bBusy && !bNotifying) Refresh();
}
void ADaedalusBricksBlueprintTrail::SkylineViewChanged(ADaedalusBricksSkylineWorkshop* ChangedWorkshop)
{
    if (!Alive() || ChangedWorkshop!=SkylineIdentity || !bPrepared) return;
    ObservePrepared(); if (!bBusy && !bNotifying) Refresh();
}
void ADaedalusBricksBlueprintTrail::WorkshopEnded(AActor* Actor,EEndPlayReason::Type)
{
    if (!Alive() || !Actor) return;
    bool Found=Actor==BridgeIdentity || Actor==SkylineIdentity;
    for (const auto& Effect:SetupEffects) if (Effect.Get()==Actor) { Found=true; break; }
    if (!Found) return;
    Unavailable(TEXT("A teaching workshop became unavailable. Its practice and all recorded study notes stay; this trail will not replace it."));
    if (!bBusy && !bNotifying) Refresh();
}
void ADaedalusBricksBlueprintTrail::ReleaseEffects()
{
    const auto Effects=SetupEffects; SetupEffects.Reset(); Bridge=nullptr; Skyline=nullptr; BridgeIdentity=SkylineIdentity=nullptr;
    for (const auto& Effect:Effects) UnbindEffect(Effect.Get());
    for (const auto& Effect:Effects) if (IsValid(Effect) && !Effect->IsActorBeingDestroyed() && Effect->GetOwner()==this) Effect->Destroy();
}
void ADaedalusBricksBlueprintTrail::EndPlay(const EEndPlayReason::Type Reason)
{ bEnding=true; ++Epoch; ReleaseEffects(); OnViewChanged.Broadcast(this); Super::EndPlay(Reason); }
