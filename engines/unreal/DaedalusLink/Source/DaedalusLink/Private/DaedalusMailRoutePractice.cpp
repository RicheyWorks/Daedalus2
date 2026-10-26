// SPDX-License-Identifier: MIT
#include "DaedalusMailRoutePractice.h"
#include "DaedalusHero.h"
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
#include "ProceduralMeshComponent.h"
#include "Templates/UnrealTemplate.h"
#include "UObject/ConstructorHelpers.h"

namespace DaedalusMailPracticeLocal
{
    using namespace daedalus::parcels;
    bool Placement(const FTransform& Frame)
    {
        return !Frame.ContainsNaN() && Frame.GetRotation().IsNormalized() && Frame.GetScale3D().Equals(FVector::OneVector,0.001) &&
            Frame.GetRotation().RotateVector(FVector::UpVector).Equals(FVector::UpVector,0.001);
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
    FVector Point(Coord Cell,double Height=3)
    { const auto D=Depot().At(); return FVector((static_cast<double>(Cell.X)-D.X)*100,(static_cast<double>(Cell.Z)-D.Z)*100,Height); }
    FVector Point(double X,double Z,double Height)
    { const auto D=Depot().At(); return FVector((X-D.X)*100,(Z-D.Z)*100,Height); }
    bool LocalReach(const ADaedalusHero* Hero,const AActor* Station,const APlayerController* Expected=nullptr)
    {
        const auto PairAlive=[&]()
        {
            return IsInGameThread() && IsValid(Hero) && Hero->HasActorBegunPlay() && !Hero->IsActorBeingDestroyed() &&
                IsValid(Station) && Station->HasActorBegunPlay() && !Station->IsActorBeingDestroyed() && Station->GetWorld() &&
                Hero->GetWorld()==Station->GetWorld() && Station->GetWorld()->GetNetMode()==NM_Standalone &&
                FMath::IsFinite(Hero->InteractReach) && Hero->InteractReach>0;
        };
        if (!PairAlive() || !Hero->IsLocallyControlled() || !PairAlive()) return false;
        const auto* Player=Cast<APlayerController>(Hero->GetController());
        if (!IsValid(Player) || Player->IsActorBeingDestroyed() || !Player->HasActorBegunPlay() || Player->GetWorld()!=Station->GetWorld() ||
            !Player->IsLocalController() || !PairAlive()) return false;
        if (!IsValid(Player) || Player->IsActorBeingDestroyed() || !Player->HasActorBegunPlay() || Player->GetWorld()!=Station->GetWorld() ||
            Hero->GetController()!=Player || Player->GetPawn()!=Hero || !IsValid(Player->GetLocalPlayer()) || (Expected && Expected!=Player)) return false;
        const double Distance=FVector::DistSquared(Hero->GetActorLocation(),Station->GetActorLocation());
        return FMath::IsFinite(Distance) && Distance<=static_cast<double>(Hero->InteractReach)*Hero->InteractReach;
    }
    struct Ink
    {
        TArray<FVector> Vertices; TArray<int32> Indices; TArray<FLinearColor> Colours;
        void Triangle(FVector A,FVector B,FVector C,FLinearColor Colour)
        { const int32 I=Vertices.Num(); Vertices.Append({A,B,C}); Indices.Append({I,I+1,I+2}); Colours.Append({Colour,Colour,Colour}); }
        void Line(FVector A,FVector B,double HalfWidth,FLinearColor Colour)
        {
            const FVector D=(B-A).GetSafeNormal(); if (D.IsNearlyZero()) return;
            const FVector S(-D.Y*HalfWidth,D.X*HalfWidth,0);
            Triangle(A-S,B-S,B+S,Colour); Triangle(A-S,B+S,A+S,Colour);
        }
        void Arrow(FVector A,FVector B,FLinearColor Colour)
        {
            const double Length=FVector::Dist(A,B); if (Length<1) return;
            const FVector D=(B-A)/Length,S(-D.Y*25,D.X*25,0);
            const int32 Count=FMath::Max(1,FMath::FloorToInt(Length/600));
            for (int32 I=0;I<Count;++I)
            { const FVector P=FMath::Lerp(A,B,(I+0.5)/Count); Triangle(P+D*45,P-D*30+S,P-D*30-S,Colour); }
        }
        void Apply(UProceduralMeshComponent* Mesh,UMaterialInterface* Material) const
        {
            TArray<FVector> Normals; Normals.SetNum(Vertices.Num());
            for (int32 I=0;I+2<Vertices.Num();I+=3)
            {
                const FVector N=FVector::CrossProduct(Vertices[I+1]-Vertices[I],Vertices[I+2]-Vertices[I]).GetSafeNormal();
                Normals[I]=N; Normals[I+1]=N; Normals[I+2]=N;
            }
            Mesh->CreateMeshSection_LinearColor(0,Vertices,Indices,Normals,TArray<FVector2D>(),Colours,TArray<FProcMeshTangent>(),false);
            Mesh->SetMaterial(0,Material);
        }
    };
    const TCHAR* MedalName(Medal Value)
    {
        switch (Value) { case Medal::Gold:return TEXT("GOLD"); case Medal::Silver:return TEXT("SILVER"); case Medal::Bronze:return TEXT("BRONZE"); default:return TEXT("OPEN"); }
    }
    FString OutcomeLine(Outcome Value)
    {
        switch (Value)
        {
        case Outcome::OnTime:return TEXT("Delivered on time. Follow the next street arrows.");
        case Outcome::Late:return TEXT("Delivered late, and it still counts. Keep going!");
        case Outcome::PickedUp:return TEXT("Ghost letter collected. Carry the bright envelope back to the depot.");
        case Outcome::AlreadyDone:return TEXT("Already delivered. Your earlier delivery is kept.");
        case Outcome::Trespass:return TEXT("Stay on the street outside plot borders to deliver.");
        case Outcome::TooFar:return TEXT("Stand on the flat street within two metres of this mailbox.");
        default:return TEXT("This sample was unavailable. Stand on the street and try again; no letter was spent.");
        }
    }
}

ADaedalusMailPracticeStop::ADaedalusMailPracticeStop()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    MailRoot=CreateDefaultSubobject<USceneComponent>(TEXT("PracticeMailboxRoot")); RootComponent=MailRoot;
    Body->SetupAttachment(MailRoot); Glow->SetupAttachment(MailRoot); Glow->SetIntensity(0); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeLocation(FVector(0,0,70)); Body->SetRelativeScale3D(FVector(0.5,0.7,1.1));
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Label=CreateDefaultSubobject<UTextRenderComponent>(TEXT("PracticeMailboxLabel")); Label->SetupAttachment(MailRoot);
    Label->SetRelativeLocation(FVector(35,0,220)); Label->SetWorldSize(14); Label->SetHorizontalAlignment(EHTA_Center);
    Label->SetVerticalAlignment(EVRTA_TextTop); Label->SetTextRenderColor(FColor(30,35,60));
    Label->SetText(FText::FromString(TEXT("LOCAL PRACTICE\nMailbox inactive")));
}
bool ADaedalusMailPracticeStop::ViewsReady() const
{
    return !bEnding && HasActorBegunPlay() && !IsActorBeingDestroyed() && IsValid(Body) && Body->GetOwner()==this &&
        Body->IsRegistered() && Body->GetStaticMesh() && IsValid(Label) && Label->GetOwner()==this && Label->IsRegistered();
}
FString ADaedalusMailPracticeStop::Prompt(const ADaedalusHero* Hero) const
{ const auto* Parent=Course.Get(); return Parent && Parent->StopReady(this,Letter,true)?Parent->StopPrompt(Hero,Letter):TEXT("Local practice mailbox is inactive"); }
bool ADaedalusMailPracticeStop::Use(ADaedalusHero* Hero)
{ auto* Parent=Course.Get(); return Parent && Parent->UseStop(Hero,this); }
void ADaedalusMailPracticeStop::EndPlay(const EEndPlayReason::Type Reason)
{ bEnding=true; Super::EndPlay(Reason); }

ADaedalusMailRoutePractice::ADaedalusMailRoutePractice()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    PracticeRoot=CreateDefaultSubobject<USceneComponent>(TEXT("MailPracticeRoot")); RootComponent=PracticeRoot;
    Body->SetupAttachment(PracticeRoot); Glow->SetupAttachment(PracticeRoot); Glow->SetIntensity(0); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Engine/EngineDebugMaterials/VertexColorMaterial.VertexColorMaterial")); InkMaterial=Material.Object;
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeLocation(FVector(0,0,65)); Body->SetRelativeScale3D(FVector(0.5,1.2,1.1));
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    StreetInk=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("PracticeStreetPaint")); StreetInk->SetupAttachment(PracticeRoot);
    GuideInk=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("PracticeStreetArrows")); GuideInk->SetupAttachment(PracticeRoot);
    GhostLetter=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("PracticeGhostEnvelope")); GhostLetter->SetupAttachment(PracticeRoot);
    for (auto* Mesh:{StreetInk.Get(),GuideInk.Get(),GhostLetter.Get()}) { Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision); Mesh->SetCastShadow(false); }
    GhostLetter->SetVisibility(false);
    Readout=CreateDefaultSubobject<UTextRenderComponent>(TEXT("PracticeDepotReadout")); Readout->SetupAttachment(PracticeRoot);
    Readout->SetRelativeLocation(FVector(40,0,340)); Readout->SetWorldSize(14); Readout->SetHorizontalAlignment(EHTA_Center);
    Readout->SetVerticalAlignment(EVRTA_TextTop); Readout->SetTextRenderColor(FColor(30,35,60));
}
bool ADaedalusMailRoutePractice::Alive() const
{ return IsInGameThread() && !bEnding && HasActorBegunPlay() && !IsActorBeingDestroyed() && GetWorld(); }
bool ADaedalusMailRoutePractice::ViewsReady() const
{
    if (!Alive() || !InkMaterial || !IsValid(Body) || Body->GetOwner()!=this || !Body->IsRegistered() || !Body->GetStaticMesh() ||
        !IsValid(Readout) || Readout->GetOwner()!=this || !Readout->IsRegistered()) return false;
    for (const auto* Mesh:{StreetInk.Get(),GuideInk.Get(),GhostLetter.Get()})
        if (!IsValid(Mesh) || Mesh->GetOwner()!=this || !Mesh->IsRegistered()) return false;
    return StreetInk->GetNumSections()>0 && StreetInk->GetMaterial(0) && GhostLetter->GetNumSections()>0 && GhostLetter->GetMaterial(0);
}
void ADaedalusMailRoutePractice::Unavailable(const FString& Why) const
{ if (!bUnavailable) { bUnavailable=true; Fault=Why; } }
bool ADaedalusMailRoutePractice::StopReady(const ADaedalusMailPracticeStop* Stop,int32 Letter,bool Begun) const
{
    if (!Alive() || !Stops.IsValidIndex(Letter) || !ExpectedStops.IsValidIndex(Letter) || Stops[Letter].Get()!=Stop || !IsValid(Stop) ||
        Stop->GetClass()!=ADaedalusMailPracticeStop::StaticClass() || Stop->IsActorBeingDestroyed() || Stop->GetOwner()!=this ||
        Stop->GetWorld()!=GetWorld() || Stop->Course.Get()!=this || Stop->Letter!=Letter || Stop->GetActorEnableCollision() ||
        !IsValid(Stop->GetRootComponent()) || Stop->GetRootComponent()->GetAttachParent()!=nullptr ||
        !Stop->GetActorTransform().Equals(ExpectedStops[Letter],0.01)) return false;
    return !Begun || Stop->ViewsReady();
}
bool ADaedalusMailRoutePractice::ObserveCourse() const
{
    if (!Alive() || bUnavailable) return false;
    if (!ViewsReady()) { Unavailable(TEXT("A practice display is unavailable. Existing letters and stops are kept.")); return false; }
    if (!bAttempted) return true;
    if (!GetActorTransform().Equals(FrozenFrame,0.01) || PracticeSeed!=FrozenSeed)
    { Unavailable(TEXT("The practice frame or seed changed. This round stays here; use a new practice course.")); return false; }
    if (!bPrepared) return true;
    if (!Courier.IsValid() || Courier->IsActorBeingDestroyed() || !Controller.IsValid() || Controller->IsActorBeingDestroyed() ||
        Courier->GetWorld()!=GetWorld() || Controller->GetWorld()!=GetWorld() || Courier->GetController()!=Controller.Get() || Controller->GetPawn()!=Courier.Get())
    { Unavailable(TEXT("The practice courier changed or left. This round is retained without replacement.")); return false; }
    for (int32 I=0;I<Stops.Num();++I) if (!StopReady(Stops[I],I,true))
    { Unavailable(TEXT("A practice mailbox moved or became unavailable. Existing deliveries remain; no stop is replaced.")); return false; }
    return true;
}
bool ADaedalusMailRoutePractice::IsPracticeActive() const
{ return ObserveCourse() && bPrepared && Round.Active(); }
bool ADaedalusMailRoutePractice::ReadCourier(ADaedalusHero* Hero,const AActor* Station,FVector& LocalFeet,double& Now) const
{
    const uint64 Before=Epoch;
    if (!Alive() || !ObserveCourse() || Hero!=Courier.Get() || !Controller.IsValid() ||
        !DaedalusMailPracticeLocal::LocalReach(Hero,Station,Controller.Get())) return false;
    if (!Alive() || Epoch!=Before || !ObserveCourse() || Hero!=Courier.Get() || !Controller.IsValid()) return false;
    const auto* Capsule=Hero->GetCapsuleComponent(); const auto* Movement=Hero->GetCharacterMovement();
    if (!IsValid(Capsule) || Capsule->GetOwner()!=Hero || !Capsule->IsRegistered() || !IsValid(Movement) ||
        Movement->GetOwner()!=Hero || !Movement->IsRegistered() || !Movement->IsMovingOnGround()) return false;
    if (!Alive() || Epoch!=Before || !ObserveCourse() || Hero!=Courier.Get() || Hero->GetController()!=Controller.Get()) return false;
    const double HalfHeight=Capsule->GetScaledCapsuleHalfHeight(); if (!FMath::IsFinite(HalfHeight) || HalfHeight<=0) return false;
    const FVector Feet=Hero->GetActorLocation()-FVector(0,0,HalfHeight);
    const FVector Sample=FrozenFrame.InverseTransformPosition(Feet); const double Time=GetWorld()->GetTimeSeconds();
    if (Sample.ContainsNaN() || !FMath::IsFinite(Time) || Time<0 || FMath::Abs(Sample.Z)>25) return false;
    LocalFeet=Sample; Now=Time; return true;
}
void ADaedalusMailRoutePractice::DrawStreets()
{
    using namespace DaedalusMailPracticeLocal;
    if (!Alive() || !IsValid(StreetInk) || !InkMaterial) return;
    Ink Paint; const FLinearColor Street(0.12f,0.19f,0.27f),Border(0.55f,0.23f,0.12f),Centre(0.95f,0.77f,0.2f);
    for (int32 R=0;R<5;++R)
    {
        const double X=-24+R*36,Z=-146+R*36;
        // Four whole cube cells; the canonical delivery line is half a cell
        // east/north of the geometric centre of this even-width road.
        Paint.Line(Point(X-0.5,-148.5,2),Point(X-0.5,-0.5,2),200,Street);
        Paint.Line(Point(-26.5,Z-0.5,2),Point(121.5,Z-0.5,2),200,Street);
        Paint.Line(Point(X,-148.5,3),Point(X,-0.5,3),4,Centre);
        Paint.Line(Point(-26.5,Z,3),Point(121.5,Z,3),4,Centre);
    }
    Paint.Line(Point(29.5,-74.5,2.5),Point(65.5,-74.5,2.5),1800,Street); // 36x36-cell plaza.
    for (int32 P=0;P<64;++P)
    {
        if (!daedalus::parcels::Detail::IsPlot(P)) continue;
        const double X=-26+daedalus::parcels::Detail::Offset(P%8)-0.5,Z=-148+daedalus::parcels::Detail::Offset(P/8)-0.5;
        const FVector A=Point(X,Z,4),B=Point(X+16,Z,4),C=Point(X+16,Z+16,4),D=Point(X,Z+16,4);
        Paint.Line(A,B,5,Border); Paint.Line(B,C,5,Border); Paint.Line(C,D,5,Border); Paint.Line(D,A,5,Border);
    }
    Paint.Apply(StreetInk,InkMaterial);
}
void ADaedalusMailRoutePractice::DrawGuide()
{
    using namespace DaedalusMailPracticeLocal;
    if (!Alive() || !IsValid(GuideInk) || !InkMaterial) return;
    if (!bPrepared || bUnavailable || !Round.Active()) { GuideInk->ClearAllMeshSections(); return; }
    const int Next=Round.NextLetter(); const auto& Day=Round.ReadRoute().CurrentDay();
    const Stop Target=Next>=0?Day.Letters[static_cast<size_t>(Next)].Mailbox:Depot();
    const auto Corners=Waypoints(Round.LastStation(),Target); Ink Paint;
    for (size_t I=1;I<Corners.size();++I)
    {
        const FVector A=Point(Corners[I-1],6),B=Point(Corners[I],6);
        Paint.Line(A,B,13,FLinearColor(0.05f,0.9f,0.7f)); Paint.Arrow(A+FVector(0,0,1),B+FVector(0,0,1),FLinearColor(0.95f,1.f,0.85f));
    }
    const FVector Goal=Point(Target.At(),7); const FLinearColor Colour(0.05f,0.9f,0.7f);
    Paint.Line(Goal+FVector(-65,-65,0),Goal+FVector(65,-65,0),8,Colour);
    Paint.Line(Goal+FVector(65,-65,0),Goal+FVector(65,65,0),8,Colour);
    Paint.Line(Goal+FVector(65,65,0),Goal+FVector(-65,65,0),8,Colour);
    Paint.Line(Goal+FVector(-65,65,0),Goal+FVector(-65,-65,0),8,Colour);
    Paint.Apply(GuideInk,InkMaterial);
}
void ADaedalusMailRoutePractice::BeginPlay()
{
    bEnding=false; ++Epoch; Super::BeginPlay(); if (!Alive()) return;
    DrawStreets(); if (!Alive()) return;
    DaedalusMailPracticeLocal::Ink Envelope; const FLinearColor Paper(0.65f,0.4f,1.f),Fold(1.f,0.95f,0.6f);
    // Bright original two-sided envelope geometry, no physical light or Hero material edits.
    const FVector A(0,-18,-12),B(0,18,-12),C(0,18,12),D(0,-18,12),M(1,0,0);
    Envelope.Triangle(A,B,C,Paper); Envelope.Triangle(A,C,D,Paper);
    Envelope.Triangle(C,B,A,Paper); Envelope.Triangle(D,C,A,Paper); Envelope.Triangle(D,M,C,Fold); Envelope.Triangle(C,M,D,Fold);
    if (IsValid(GhostLetter) && InkMaterial) Envelope.Apply(GhostLetter,InkMaterial);
    Notice=TEXT("E / X starts local street-mail practice. Walk the marked roads; plot borders are not shortcuts. No stamps or saved progress are issued.");
    Refresh(); // No mailbox, courier binding, clock or file work during startup.
}
FString ADaedalusMailRoutePractice::Prompt(const ADaedalusHero* Hero) const
{
    if (!Alive() || GetWorld()->GetNetMode()!=NM_Standalone || !ObserveCourse()) return TEXT("Local mail practice is unavailable; existing work is kept");
    if (!bAttempted) return TEXT("E / X: Start local street-mail practice");
    if (!bPrepared) return TEXT("Practice setup stopped; partial mailboxes kept, no retry");
    if (Hero!=Courier.Get()) return TEXT("This practice belongs to its original local courier");
    return TEXT("E / X: Return Ghost / view practice receipt; route stays open");
}
FString ADaedalusMailRoutePractice::StopPrompt(const ADaedalusHero* Hero,int32 Letter) const
{
    if (!ObserveCourse() || !bPrepared || !Round.Active() || !StopReady(Stops.IsValidIndex(Letter)?Stops[Letter].Get():nullptr,Letter,true)) return TEXT("Practice mailbox unavailable; progress kept");
    if (Hero!=Courier.Get()) return TEXT("This mailbox belongs to another local practice courier");
    if (Round.ReadRoute().IsDone(Letter)) return TEXT("Letter already done; follow the street arrows");
    const auto& Item=Round.ReadRoute().CurrentDay().Letters[static_cast<size_t>(Letter)];
    return Item.Type==daedalus::parcels::Kind::GhostPickup?TEXT("E / X: Collect the practice Ghost letter"):TEXT("E / X: Deliver this practice letter");
}
void ADaedalusMailRoutePractice::RememberEffect(AActor* Actor)
{ if (Alive() && IsValid(Actor)) SetupEffects.AddUnique(Actor); }
bool ADaedalusMailRoutePractice::Prepare(ADaedalusHero* Hero)
{
    if (bAttempted || !Alive() || !ObserveCourse() || !DaedalusMailPracticeLocal::Placement(GetActorTransform())) return false;
    FrozenFrame=GetActorTransform(); FrozenSeed=PracticeSeed; Courier=Hero; Controller=Cast<APlayerController>(Hero->GetController());
    FVector Feet; double Before=0;
    if (!ReadCourier(Hero,this,Feet,Before) || FMath::Square(Feet.X)+FMath::Square(Feet.Y)>40000)
    { Courier.Reset(); Controller.Reset(); Notice=TEXT("Stand on flat safe ground within two metres of the depot to begin."); return false; }
    bAttempted=true; const uint64 StartEpoch=Epoch;
    daedalus::parcels::Day Plan;
    if (!daedalus::parcels::MakeDay(FrozenSeed,Plan)) { Unavailable(TEXT("The practice day could not be prepared; no automatic retry.")); return false; }
    const int32 Count=static_cast<int32>(Plan.Letters.size()); Stops.SetNum(Count); ExpectedStops.SetNum(Count);
    for (int32 I=0;I<Count;++I) ExpectedStops[I]=FTransform(DaedalusMailPracticeLocal::Point(Plan.Letters[static_cast<size_t>(I)].Mailbox.At(),0))*FrozenFrame;
    const TWeakObjectPtr<ADaedalusMailRoutePractice> Self(this);
    const auto Participants=[&]()
    {
        FVector CurrentFeet; double Time=0;
        if (!Alive() || Epoch!=StartEpoch || !ObserveCourse() || !ReadCourier(Hero,this,CurrentFeet,Time)) return false;
        if (!Alive() || Epoch!=StartEpoch || !ObserveCourse() || Courier.Get()!=Hero) return false;
        for (int32 J=0;J<Stops.Num();++J) if (Stops[J] && !StopReady(Stops[J],J,Stops[J]->HasActorBegunPlay())) return false;
        return true;
    };
    for (int32 I=0;I<Count;++I)
    {
        if (!Participants()) { Unavailable(TEXT("Practice setup stopped. Partial mailboxes are kept; no replacement or retry.")); return false; }
        TWeakObjectPtr<ADaedalusMailPracticeStop> Staged; const ADaedalusMailPracticeStop* Identity=nullptr;
        FActorSpawnParameters P; P.Owner=this; P.ObjectFlags=RF_Transient|RF_DuplicateTransient; P.bDeferConstruction=true;
        P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        P.CustomPreSpawnInitialization=[Self,StartEpoch,I,&Staged,&Identity](AActor* Actor)
        {
            if (!Actor || Actor->GetClass()!=ADaedalusMailPracticeStop::StaticClass()) return;
            auto* Stop=Cast<ADaedalusMailPracticeStop>(Actor); Staged=Stop; Identity=Stop;
            auto* Owner=Self.Get(); if (!Owner || !Owner->Alive() || Owner->Epoch!=StartEpoch || !Owner->Stops.IsValidIndex(I)) return;
            Owner->RememberEffect(Stop); Owner->Stops[I]=Stop; Stop->Course=Owner; Stop->Letter=I;
            Stop->OnEndPlay.AddUniqueDynamic(Owner,&ADaedalusMailRoutePractice::StopEnded);
        };
        auto* Candidate=GetWorld()->SpawnActor<ADaedalusMailPracticeStop>(ADaedalusMailPracticeStop::StaticClass(),ExpectedStops[I],P);
        const auto ReconcileEnded=[&]()
        {
            TArray<TWeakObjectPtr<ADaedalusMailPracticeStop>> Effects;
            if (IsValid(Candidate)) Effects.AddUnique(TWeakObjectPtr<ADaedalusMailPracticeStop>(Candidate)); if (Staged.IsValid()) Effects.AddUnique(Staged);
            for (const auto& Effect:Effects) if (auto* Stop=Effect.Get())
            { Stop->OnEndPlay.RemoveDynamic(this,&ADaedalusMailRoutePractice::StopEnded); if (Stop->GetClass()==ADaedalusMailPracticeStop::StaticClass() && !Stop->IsActorBeingDestroyed() && Stop->GetOwner()==this) Stop->Destroy(); }
        };
        if (!Alive()) { ReconcileEnded(); return false; }
        RememberEffect(Candidate);
        const auto Valid=[&](bool Begun)
        { return Participants() && Candidate==Identity && Staged.Get()==Candidate && StopReady(Candidate,I,Begun); };
        if (!Valid(false)) { Unavailable(TEXT("A mailbox setup was incomplete. Its effects stay for review; no retry.")); return false; }
        Candidate->FinishSpawning(ExpectedStops[I]);
        if (!Alive()) { ReconcileEnded(); return false; }
        if (!Valid(true)) { Unavailable(TEXT("A practice mailbox failed readiness. All partial effects are kept.")); return false; }
    }
    FVector FinalFeet; double Started=0;
    if (!Participants() || !ReadCourier(Hero,this,FinalFeet,Started) || FMath::Square(FinalFeet.X)+FMath::Square(FinalFeet.Y)>40000 || !Round.BeginPrepared(Plan,Started))
    { Unavailable(TEXT("The practice clock could not start. Prepared mailboxes stay, with no automatic retry.")); return false; }
    bPrepared=true; Notice=TEXT("Satchel ready! Follow the mint arrows from the last stop. Other mailboxes also accept their letters. Return here for a practice receipt at any time.");
    return ObserveCourse();
}
bool ADaedalusMailRoutePractice::Use(ADaedalusHero* Hero)
{
    const uint64 Before=Epoch;
    if (!Alive() || bBusy || bNotifying || !DaedalusMailPracticeLocal::LocalReach(Hero,this) || !Alive() || Epoch!=Before) return false;
    TGuardValue<bool> Busy(bBusy,true);
    if (!ObserveCourse()) { Refresh(); return false; }
    if (!bAttempted)
    {
        if (!DaedalusMailPracticeLocal::Placement(GetActorTransform())) Notice=TEXT("Place this depot upright at unit size on safe flat ground, with 148 metres of clear practice space.");
        else Prepare(Hero);
        Refresh(); return Alive() && bPrepared && !bUnavailable;
    }
    if (!bPrepared || Hero!=Courier.Get()) { Refresh(); return false; }
    FVector Feet; double Time=0; daedalus::parcels::Receipt Sample;
    if (!ReadCourier(Hero,this,Feet,Time) || !Round.Receipt(Feet.X,Feet.Y,Feet.Z,Time,Sample))
    { Notice=TEXT("Stand on the flat street within two metres of the depot. No route progress changed."); Refresh(); return false; }
    LastReceipt.Delivered=Sample.Delivered; LastReceipt.Late=Sample.Late; LastReceipt.Undelivered=Sample.Undelivered;
    LastReceipt.bGhostReturned=Sample.GhostReturned; LastReceipt.PracticePoints=Sample.Stamps;
    LastReceipt.Seconds=Sample.Seconds; LastReceipt.ParSeconds=Sample.ParSeconds; LastReceipt.Medal=DaedalusMailPracticeLocal::MedalName(Sample.Award);
    bHasReceipt=true; bGhostReturned=bGhostReturned || Sample.GhostReturned;
    Notice=TEXT("Practice receipt only: no stamps issued. Your route stays open; remaining letters still accept delivery.");
    const auto EventReceipt=LastReceipt; Refresh();
    if (Alive() && Epoch==Before && ObserveCourse()) { TGuardValue<bool> Notification(bNotifying,true); OnPracticeReceipt.Broadcast(this,EventReceipt); }
    return true;
}
bool ADaedalusMailRoutePractice::UseStop(ADaedalusHero* Hero,ADaedalusMailPracticeStop* Stop)
{
    if (!Alive() || bBusy || bNotifying || !ObserveCourse() || !bPrepared || !Round.Active() || !IsValid(Stop) || !StopReady(Stop,Stop->Letter,true)) return false;
    TGuardValue<bool> Busy(bBusy,true); const uint64 Before=Epoch;
    FVector Feet; double Time=0;
    if (!ReadCourier(Hero,Stop,Feet,Time) || !Alive() || Epoch!=Before || !ObserveCourse() || !StopReady(Stop,Stop->Letter,true))
    {
        if (Alive() && Epoch==Before && Hero==Courier.Get() && StopReady(Stop,Stop->Letter,true))
        {
            Notice=TEXT("Stand on the flat street within two metres of the mailbox. Your letter is kept."); Refresh();
            if (Alive() && Epoch==Before && StopReady(Stop,Stop->Letter,true)) Stop->Label->SetText(FText::FromString(TEXT("LOCAL PRACTICE MAIL\nStand on the flat street\nE / X within two metres\nYour letter is kept")));
        }
        return false;
    }
    const auto Result=Round.Deliver(Stop->Letter,Feet.X,Feet.Y,Feet.Z,Time);
    Notice=DaedalusMailPracticeLocal::OutcomeLine(Result); Refresh();
    if (Alive() && Epoch==Before && StopReady(Stop,Stop->Letter,true))
    {
        if (Result==daedalus::parcels::Outcome::TooFar)
            Stop->Label->SetText(FText::FromString(TEXT("LETTER KEPT\nStand on the flat street\nWithin two metres\nE / X tries again")));
        else if (Result==daedalus::parcels::Outcome::Trespass)
            Stop->Label->SetText(FText::FromString(TEXT("LETTER KEPT\nPlots are not shortcuts\nDeliver from the street\nE / X tries again")));
        else if (Result==daedalus::parcels::Outcome::UnknownLetter)
            Stop->Label->SetText(FText::FromString(TEXT("SAMPLE UNAVAILABLE\nYour letter is kept\nReturn to the depot\nfor practice status")));
    }
    return Result==daedalus::parcels::Outcome::OnTime || Result==daedalus::parcels::Outcome::Late || Result==daedalus::parcels::Outcome::PickedUp;
}
void ADaedalusMailRoutePractice::Refresh()
{
    if (!Alive() || bNotifying) return; const uint64 Before=Epoch; ObserveCourse();
    FString Text=TEXT("STREET MAIL / LOCAL PRACTICE\n");
    if (bPrepared && Round.Active())
    {
        const auto& Route=Round.ReadRoute(); const auto& Day=Route.CurrentDay(); int32 Done=0;
        for (const auto& Letter:Day.Letters) if (Route.IsDone(Letter.Id)) ++Done;
        Text+=FString::Printf(TEXT("Stops %d/%d / par %ds\nClock at last station: %ds\n"),Done,static_cast<int32>(Day.Letters.size()),Day.ParSeconds,Round.LastElapsed());
        const int Next=Round.NextLetter(); Text+=Next>=0?FString::Printf(TEXT("Next: mailbox %d / plot %d\n"),Next+1,Day.Letters[static_cast<size_t>(Next)].Plot):TEXT("All stops visited: return to depot\n");
        if (Route.HoldingGhost()) Text+=bGhostReturned?TEXT("Ghost letter returned at depot.\n"):TEXT("Ghost letter in satchel: return to depot.\n");
        for (int32 I=0;I<Stops.Num();++I) if (StopReady(Stops[I],I,true))
        {
            const auto& Letter=Day.Letters[static_cast<size_t>(I)];
            FString Line=FString::Printf(TEXT("PRACTICE MAIL %d / PLOT %d\n"),I+1,Letter.Plot);
            if (Route.IsDone(I)) Line+=Letter.Type==daedalus::parcels::Kind::GhostPickup?TEXT("GHOST COLLECTED\nReturn to depot"):TEXT("DELIVERED / THANK YOU!");
            else if (Letter.Type==daedalus::parcels::Kind::Express) Line+=FString::Printf(TEXT("EXPRESS / deadline %ds\nE / X delivers / late still counts"),Letter.Deadline);
            else if (Letter.Type==daedalus::parcels::Kind::GhostPickup) Line+=TEXT("GHOST LETTER\nE / X collects / carry home");
            else Line+=TEXT("STANDARD LETTER\nE / X delivers");
            Stops[I]->Label->SetText(FText::FromString(Line));
            if (!Alive() || Epoch!=Before) return;
        }
        if (!bUnavailable && Round.ReadRoute().HoldingGhost() && !bGhostReturned)
        {
            auto* Hero=Courier.Get(); if (IsValid(Hero) && IsValid(Hero->GetRootComponent()))
            {
                const bool Attached=GhostLetter->AttachToComponent(Hero->GetRootComponent(),FAttachmentTransformRules::KeepRelativeTransform);
                GhostLetter->SetRelativeLocation(FVector(0,55,40)); GhostLetter->SetRelativeRotation(FRotator::ZeroRotator);
                GhostLetter->SetRelativeScale3D(FVector::OneVector);
                if (Attached && GhostLetter->GetAttachParent()==Hero->GetRootComponent()) GhostLetter->SetVisibility(true);
                else { GhostLetter->SetVisibility(false); Unavailable(TEXT("The Ghost envelope display could not attach. The pickup is kept; no replacement is made.")); }
            }
        }
        else if (IsValid(GhostLetter)) GhostLetter->SetVisibility(false);
    }
    if (bHasReceipt) Text+=FString::Printf(TEXT("LAST DEPOT RECEIPT / %s\n%d delivered / %d late / %d left\n%d practice points / %ds\n"),*LastReceipt.Medal,LastReceipt.Delivered,LastReceipt.Late,LastReceipt.Undelivered,LastReceipt.PracticePoints,LastReceipt.Seconds);
    Text+=bUnavailable?Fault:Notice;
    if (IsValid(Readout) && Readout->GetOwner()==this) Readout->SetText(FText::FromString(DaedalusMailPracticeLocal::Wrap(Text)));
    if (!Alive() || Epoch!=Before) return; DrawGuide();
    if (!Alive() || Epoch!=Before) return;
    TGuardValue<bool> Notification(bNotifying,true); OnViewChanged.Broadcast(this);
}
void ADaedalusMailRoutePractice::StopEnded(AActor* Actor,EEndPlayReason::Type)
{
    if (!Alive() || !Actor) return; bool Found=false;
    for (const auto& Effect:SetupEffects) if (Effect.Get()==Actor) { Found=true; break; }
    if (!Found) return; Unavailable(TEXT("A practice mailbox ended. Existing deliveries are retained; this course will not replace it."));
    if (!bBusy && !bNotifying) Refresh();
}
void ADaedalusMailRoutePractice::ReleaseEffects()
{
    const auto Effects=SetupEffects; SetupEffects.Reset(); Stops.Reset();
    for (const auto& Entry:Effects) if (IsValid(Entry.Get())) Entry->OnEndPlay.RemoveDynamic(this,&ADaedalusMailRoutePractice::StopEnded);
    for (const auto& Entry:Effects) if (auto* Actor=Entry.Get())
        if (IsValid(Actor) && Actor->GetClass()==ADaedalusMailPracticeStop::StaticClass() && Actor->GetOwner()==this && !Actor->IsActorBeingDestroyed()) Actor->Destroy();
}
void ADaedalusMailRoutePractice::EndPlay(const EEndPlayReason::Type Reason)
{ bEnding=true; ++Epoch; ReleaseEffects(); Super::EndPlay(Reason); }
