// SPDX-License-Identifier: MIT
#include "DaedalusGalleryMotifRack.h"
#include "DaedalusGalleryMotifStudio.h"
#include "DaedalusGalleryMotifStudy.h"
#include "DaedalusHero.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "ProceduralMeshComponent.h"
#include "Templates/UnrealTemplate.h"
#include "UObject/ConstructorHelpers.h"

namespace DaedalusMotifRackLocal
{
    FString Canonical(const FString& Id)
    {
        if (Id.Len()!=32) return FString();
        const FTCHARToUTF8 Encoded(*Id,Id.Len());
        const auto Value=daedalus::motif::CanonicalId(std::string(Encoded.Get(),static_cast<size_t>(Encoded.Length())));
        return FString(UTF8_TO_TCHAR(Value.c_str()));
    }
    FTransform Mount(int32 Slot)
    { return FTransform(FQuat::Identity,FVector(Slot<2?-350:-1000,Slot%2?300:-300,0),FVector(0.7)); }
    bool LocalReach(const ADaedalusHero* Hero,const AActor* Rack,const APlayerController* Expected=nullptr)
    {
        if (!IsInGameThread() || !IsValid(Hero) || Hero->IsActorBeingDestroyed() || !Hero->HasActorBegunPlay() || !IsValid(Rack) ||
            Rack->IsActorBeingDestroyed() || !Rack->HasActorBegunPlay() || !Rack->GetWorld() || Hero->GetWorld()!=Rack->GetWorld() ||
            Rack->GetWorld()->GetNetMode()!=NM_Standalone || !Hero->IsLocallyControlled() || !FMath::IsFinite(Hero->InteractReach) || Hero->InteractReach<=0.f) return false;
        const auto* Controller=Cast<APlayerController>(Hero->GetController());
        if (!IsValid(Controller) || Controller->IsActorBeingDestroyed() || Controller->GetWorld()!=Rack->GetWorld() || !Controller->IsLocalController() ||
            Controller->GetPawn()!=Hero || !IsValid(Controller->GetLocalPlayer()) || (Expected && Controller!=Expected)) return false;
        const double Distance=FVector::DistSquared(Hero->GetActorLocation(),Rack->GetActorLocation());
        return FMath::IsFinite(Distance) && Distance<=static_cast<double>(Hero->InteractReach)*Hero->InteractReach;
    }
    FString Wrap(const FString& Text)
    {
        TArray<FString> Lines; Text.ParseIntoArrayLines(Lines,false); FString Out;
        for (int32 I=0;I<Lines.Num();++I)
        {
            if (I) Out+=TEXT("\n"); TArray<FString> Words; Lines[I].ParseIntoArray(Words,TEXT(" "),true); int32 Columns=0;
            for (const auto& Word:Words)
            {
                if (Columns && Columns+1+Word.Len()>38) { Out+=TEXT("\n"); Columns=0; }
                if (Columns) { Out+=TEXT(" "); ++Columns; } Out+=Word; Columns+=Word.Len();
            }
        }
        return Out;
    }
}

ADaedalusGalleryMotifRack::ADaedalusGalleryMotifRack()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    RackRoot=CreateDefaultSubobject<USceneComponent>(TEXT("MotifRackRoot")); RootComponent=RackRoot;
    Body->SetupAttachment(RackRoot); Glow->SetupAttachment(RackRoot); Glow->SetIntensity(0.f); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeLocation(FVector(0,0,65)); Body->SetRelativeScale3D(FVector(0.55,0.8,1.1)); Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Readout=CreateDefaultSubobject<UTextRenderComponent>(TEXT("MotifRackReadout")); Readout->SetupAttachment(RackRoot);
    Readout->SetRelativeLocation(FVector(30,0,245)); Readout->SetWorldSize(11.f); Readout->SetHorizontalAlignment(EHTA_Center);
    Readout->SetVerticalAlignment(EVRTA_TextTop); Readout->SetTextRenderColor(FColor(25,40,60));
}
bool ADaedalusGalleryMotifRack::Alive() const
{ return IsInGameThread() && !bEnding && !IsActorBeingDestroyed() && HasActorBegunPlay() && GetWorld(); }
bool ADaedalusGalleryMotifRack::ViewsReady() const
{
    return Alive() && IsValid(Readout) && Readout->GetOwner()==this && Readout->IsRegistered() &&
        IsValid(Body) && Body->GetOwner()==this && Body->IsRegistered() && Body->GetStaticMesh();
}
void ADaedalusGalleryMotifRack::Unavailable(const FString& Why) const
{ if (!bUnavailable) { bUnavailable=true; Fault=Why; } }
bool ADaedalusGalleryMotifRack::StudyReady(const ADaedalusGalleryMotifStudy* Study,const FString& Id,const FTransform& Expected,bool Begun) const
{
    if (!Alive() || !IsValid(Study) || Study->IsActorBeingDestroyed() || Study->GetOwner()!=this || Study->GetWorld()!=GetWorld() ||
        (Begun && !Study->HasActorBegunPlay()) || Study->GetActorEnableCollision() ||
        DaedalusMotifRackLocal::Canonical(Study->MotifId)!=Id || !Study->GetActorTransform().Equals(Expected,0.01)) return false;
    if (!Begun) return true;
    return IsValid(Study->Mosaic) && Study->Mosaic->GetOwner()==Study && Study->Mosaic->IsRegistered() && Study->Mosaic->GetNumSections()>0 &&
        Study->Mosaic->GetMaterial(0) && IsValid(Study->Readout) && Study->Readout->GetOwner()==Study && Study->Readout->IsRegistered();
}
bool ADaedalusGalleryMotifRack::ObservePrepared() const
{
    if (!Alive() || bUnavailable) return false;
    if (Studies.Num()!=PreparedIds.Num() || Studies.Num()!=PreparedTransforms.Num() || Studies.Num()>4)
    { Unavailable(TEXT("Prepared references are unavailable. Existing frames and files are kept; use a new rack.")); return false; }
    if (Studies.Num())
    {
        auto* Original=BoundStudio.Get();
        if (!IsValid(Original) || !Original->IsStudioAlive() || Studio.Get()!=Original || Original->GetWorld()!=GetWorld() ||
            !GetActorTransform().Equals(PreparedRackTransform,0.01))
        { Unavailable(TEXT("The rack or its Studio binding changed. Existing references stay; use a new rack.")); return false; }
    }
    for (int32 I=0;I<Studies.Num();++I)
        if (!StudyReady(Studies[I],PreparedIds[I],PreparedTransforms[I],true))
        { Unavailable(TEXT("A prepared frame moved, changed or became unavailable. Its slot stays reserved; use a new rack.")); return false; }
    return true;
}
void ADaedalusGalleryMotifRack::Refresh()
{
    if (!Alive() || bNotifying) return;
    ObservePrepared();
    FString Text=FString::Printf(TEXT("LOCAL STUDY RACK / %d OF 4\n"),PreparedIds.Num());
    for (int32 I=0;I<PreparedIds.Num();++I)
    {
        const bool Ready=!bUnavailable && Studies.IsValidIndex(I) && PreparedTransforms.IsValidIndex(I) && StudyReady(Studies[I],PreparedIds[I],PreparedTransforms[I],true);
        const bool Captured=Ready && Studies[I]->HasCapturedSketch();
        Text+=FString::Printf(TEXT("%d: %s / %s\n"),I+1,*PreparedIds[I].Left(8),!Ready?TEXT("reserved / unavailable"):Captured?TEXT("captured copy"):TEXT("prepared reference"));
    }
    Text+=bUnavailable?Fault:Notice;
    if (IsValid(Readout) && Readout->GetOwner()==this) Readout->SetText(FText::FromString(DaedalusMotifRackLocal::Wrap(Text)));
    if (!Alive()) return;
    TGuardValue<bool> Notification(bNotifying,true); OnViewChanged.Broadcast(this);
}
void ADaedalusGalleryMotifRack::BeginPlay()
{
    bEnding=false; ++Epoch; Super::BeginPlay(); if (!Alive()) return;
    Notice=TEXT("Bind a local Motif Studio. E / X prepares its last kept or loaded ID, not an unsaved draft. At each frame, use E / X to read and capture the file.");
    Refresh(); // No Studio export, file lookup, read or capture is performed.
}
FString ADaedalusGalleryMotifRack::Prompt(const ADaedalusHero*) const
{
    if (!Alive() || GetWorld()->GetNetMode()!=NM_Standalone || !ViewsReady()) return TEXT("Local study rack is unavailable here");
    if (!ObservePrepared()) return TEXT("Rack unavailable; existing references stay reserved");
    if (PreparedIds.Num()==4) return TEXT("Rack full / 4 references kept. Use a new rack for more");
    if (!IsValid(Studio) || Studio->GetWorld()!=GetWorld() || !Studio->IsStudioAlive()) return TEXT("Bind a ready local Motif Studio to this rack");
    FString Id; if (!Studio->CopyLastKeptSketchId(Id)) return TEXT("Export or load a sketch in the bound Studio first");
    if (PreparedIds.Contains(DaedalusMotifRackLocal::Canonical(Id))) return TEXT("That kept sketch already has a reference here");
    return TEXT("E / X: Prepare the last kept/loaded sketch reference; capture later at its frame");
}

bool ADaedalusGalleryMotifRack::Use(ADaedalusHero* Hero)
{
    if (!Alive() || bBusy || bNotifying || !DaedalusMotifRackLocal::LocalReach(Hero,this)) return false;
    if (!Alive()) return false;
    TGuardValue<bool> Busy(bBusy,true);
    if (PendingStudy)
    {
        Unavailable(TEXT("An earlier preparation is unresolved. The rack stopped; existing slots stay reserved."));
        auto* Outstanding=PendingStudy.Get(); PendingStudy=nullptr;
        bool Committed=false; for (const auto& Existing:Studies) if (Existing.Get()==Outstanding) { Committed=true; break; }
        if (!Committed)
        {
            UnbindStudy(Outstanding);
            if (IsValid(Outstanding) && !Outstanding->IsActorBeingDestroyed() && Outstanding->GetOwner()==this) Outstanding->Destroy();
        }
        if (Alive()) Refresh(); return false;
    }
    if (!ViewsReady()) { Notice=TEXT("The rack view is unavailable. Existing references are kept."); Refresh(); return false; }
    if (!ObservePrepared()) { Refresh(); return false; }
    if (PreparedIds.Num()==4) { Notice=TEXT("All four slots are prepared. Nothing is replaced; use a new rack for more references."); Refresh(); return false; }
    auto* Participant=Studio.Get();
    if (!IsValid(Participant) || Participant->GetWorld()!=GetWorld() || !Participant->IsStudioAlive())
    { Notice=TEXT("Bind a ready local Motif Studio in this world. No frame was prepared."); Refresh(); return false; }
    FString Id;
    if (!Participant->CopyLastKeptSketchId(Id) || (Id=DaedalusMotifRackLocal::Canonical(Id)).IsEmpty())
    { Notice=TEXT("Export or load a sketch in the bound Studio first. This rack prepares kept IDs, not unsaved drafts."); Refresh(); return false; }
    if (PreparedIds.Contains(Id)) { Notice=TEXT("That kept ID already has a prepared reference here. Use E / X at its frame to capture it."); Refresh(); return false; }
    const int32 Slot=PreparedIds.Num(); const uint64 StartEpoch=Epoch; const FTransform RackTransform=GetActorTransform();
    const FVector Scale=RackTransform.GetScale3D();
    if (RackTransform.ContainsNaN() || Scale.X<=0 || Scale.Y<=0 || Scale.Z<=0)
    { Notice=TEXT("This rack's placement is unavailable. Existing references are kept."); Refresh(); return false; }
    const FTransform Expected=DaedalusMotifRackLocal::Mount(Slot)*RackTransform;
    const TWeakObjectPtr<ADaedalusHero> Performer(Hero);
    const TWeakObjectPtr<APlayerController> Controller(Cast<APlayerController>(Hero->GetController()));
    const TWeakObjectPtr<ADaedalusGalleryMotifStudio> Source(Participant);
    auto ParticipantsReady=[&]()
    {
        auto* Walker=Performer.Get(); auto* Player=Controller.Get(); auto* Original=Source.Get();
        if (!Alive() || Epoch!=StartEpoch || !ViewsReady() || !ObservePrepared() || !IsValid(Player) ||
            !DaedalusMotifRackLocal::LocalReach(Walker,this,Player) || !IsValid(Original) || Studio.Get()!=Original ||
            Original->GetWorld()!=GetWorld() || !Original->IsStudioAlive() || !GetActorTransform().Equals(RackTransform,0.01) || PreparedIds.Num()!=Slot) return false;
        FString Current;
        return Original->CopyLastKeptSketchId(Current) && DaedalusMotifRackLocal::Canonical(Current)==Id;
    };
    if (!ParticipantsReady()) { if (Alive()) { Notice=TEXT("The Studio or walker changed before preparation. Existing references are kept."); Refresh(); } return false; }
    FActorSpawnParameters Parameters; Parameters.Owner=this; Parameters.ObjectFlags=RF_Transient|RF_DuplicateTransient; Parameters.bDeferConstruction=true;
    Parameters.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    const TWeakObjectPtr<ADaedalusGalleryMotifRack> Self(this);
    TWeakObjectPtr<ADaedalusGalleryMotifStudy> Staged;
    const ADaedalusGalleryMotifStudy* StagedIdentity=nullptr; // Comparison only, even if the weak actor ends.
    // Stage before normal world callbacks. Owner assignment happens later in
    // PostSpawnInitialize, so cleanup still checks exact ownership after return.
    Parameters.CustomPreSpawnInitialization=[Self,StartEpoch,Id,&Staged,&StagedIdentity](AActor* Actor)
    {
        Actor->SetActorEnableCollision(false); auto* Rack=Self.Get(); auto* Study=Cast<ADaedalusGalleryMotifStudy>(Actor);
        if (!Rack || !Rack->Alive() || Rack->Epoch!=StartEpoch || !Study) return;
        Staged=Study; StagedIdentity=Study; Rack->PendingStudy=Study; Study->MotifId=Id;
        Study->OnEndPlay.AddUniqueDynamic(Rack,&ADaedalusGalleryMotifRack::StudyEnded);
        Study->OnViewChanged.AddUniqueDynamic(Rack,&ADaedalusGalleryMotifRack::StudyViewChanged);
    };
    auto* Candidate=GetWorld()->SpawnActor<ADaedalusGalleryMotifStudy>(ADaedalusGalleryMotifStudy::StaticClass(),Expected,Parameters);
    auto Discard=[&]()
    {
        if (Alive() && (PendingStudy.Get()==Candidate || PendingStudy.Get()==StagedIdentity)) PendingStudy=nullptr;
        else if (Alive() && PendingStudy) Unavailable(TEXT("An unexpected pending frame remains. No slot was reused; use a new rack."));
        TArray<TWeakObjectPtr<ADaedalusGalleryMotifStudy>> Effects;
        if (IsValid(Candidate)) Effects.AddUnique(TWeakObjectPtr<ADaedalusGalleryMotifStudy>(Candidate));
        if (Staged.IsValid()) Effects.AddUnique(Staged);
        auto Committed=[&](const ADaedalusGalleryMotifStudy* Actor)
        { for (const auto& Existing:Studies) if (Existing.Get()==Actor) return true; return false; };
        for (const auto& Effect:Effects)
        {
            auto* Actor=Effect.Get(); if (!Actor) continue;
            if (Committed(Actor)) { if (Alive()) Unavailable(TEXT("A returned frame was already reserved. It was not changed; use a new rack.")); continue; }
            UnbindStudy(Actor);
        }
        for (const auto& Effect:Effects)
        {
            auto* Actor=Effect.Get(); if (!Actor || Committed(Actor)) continue;
            if (!Actor->IsActorBeingDestroyed() && Actor->GetOwner()==this) Actor->Destroy();
            else if (Alive() && Actor->GetOwner()!=this)
                Unavailable(TEXT("A new frame's ownership changed. It was not destroyed or claimed; use a new rack."));
        }
    };
    auto Fail=[&]()
    {
        Discard();
        if (Alive()) { Notice=TEXT("A new reference could not be prepared. Existing slots, frames and files are unchanged."); Refresh(); }
        return false;
    };
    if (!ParticipantsReady() || PendingStudy.Get()!=Candidate || !StudyReady(Candidate,Id,Expected,false)) return Fail();
    Candidate->FinishSpawning(Expected);
    if (!ParticipantsReady() || PendingStudy.Get()!=Candidate || !StudyReady(Candidate,Id,Expected,true) || Candidate->HasCapturedSketch()) return Fail();
    Candidate->AttachToActor(this,FAttachmentTransformRules::KeepWorldTransform);
    if (!ParticipantsReady() || PendingStudy.Get()!=Candidate || !StudyReady(Candidate,Id,Expected,true) || Candidate->HasCapturedSketch()) return Fail();
    // No callback remains between final validation and this local append. Slots
    // are committed together and never removed/replaced during the rack's life.
    const bool ChangedDraft=Source.Get()->IsDirty();
    if (!Alive() || !ParticipantsReady()) return Fail();
    if (Slot==0)
    {
        BoundStudio=Source; BoundStudioIdentity=Source.Get(); PreparedRackTransform=RackTransform;
        Source.Get()->OnEndPlay.AddUniqueDynamic(this,&ADaedalusGalleryMotifRack::StudioEnded);
    }
    Studies.Add(Candidate); PreparedIds.Add(Id); PreparedTransforms.Add(Expected); PendingStudy=nullptr;
    Notice=FString::Printf(TEXT("Reference %d prepared. No file was read here; use E / X at that frame to capture it. %s"),Slot+1,
        ChangedDraft?TEXT("Unsaved Studio changes are not included."):TEXT("This is the Studio's last kept or loaded ID, not a file-existence check."));
    Refresh(); return Alive();
}

void ADaedalusGalleryMotifRack::StudyViewChanged(ADaedalusGalleryMotifStudy* Study)
{
    if (!Alive() || Study==PendingStudy.Get()) return; // BeginPlay's pending view is not a committed slot.
    bool Found=false; for (const auto& Existing:Studies) if (Existing.Get()==Study) { Found=true; break; } if (!Found) return;
    ObservePrepared();
    if (!bBusy && !bNotifying) Refresh();
}
void ADaedalusGalleryMotifRack::StudyEnded(AActor* Actor,EEndPlayReason::Type)
{
    if (!Alive() || !Actor) return;
    bool Found=PendingStudy.Get()==Actor;
    for (const auto& Study:Studies) if (Study.Get()==Actor) { Found=true; break; }
    if (!Found) return;
    Unavailable(TEXT("A prepared or pending study became unavailable. Existing IDs stay reserved; use a new rack."));
    if (!bBusy && !bNotifying) Refresh();
}
void ADaedalusGalleryMotifRack::StudioEnded(AActor* Actor,EEndPlayReason::Type)
{
    if (!Alive() || Actor!=BoundStudioIdentity) return;
    Unavailable(TEXT("The bound Studio became unavailable. Existing frames and references stay; use a new rack."));
    if (!bBusy && !bNotifying) Refresh();
}
void ADaedalusGalleryMotifRack::UnbindStudy(ADaedalusGalleryMotifStudy* Study)
{
    if (!IsValid(Study)) return;
    Study->OnEndPlay.RemoveDynamic(this,&ADaedalusGalleryMotifRack::StudyEnded);
    Study->OnViewChanged.RemoveDynamic(this,&ADaedalusGalleryMotifRack::StudyViewChanged);
}
void ADaedalusGalleryMotifRack::ReleaseStudies()
{
    if (auto* Original=BoundStudio.Get()) Original->OnEndPlay.RemoveDynamic(this,&ADaedalusGalleryMotifRack::StudioEnded);
    auto Children=Studies; if (PendingStudy && !Children.Contains(PendingStudy)) Children.Add(PendingStudy);
    Studies.Reset(); PendingStudy=nullptr; PreparedIds.Reset(); PreparedTransforms.Reset(); BoundStudio.Reset(); BoundStudioIdentity=nullptr;
    for (const auto& Study:Children) UnbindStudy(Study);
    for (const auto& Study:Children) if (IsValid(Study) && !Study->IsActorBeingDestroyed() && Study->GetOwner()==this) Study->Destroy();
}
void ADaedalusGalleryMotifRack::EndPlay(const EEndPlayReason::Type Reason)
{ bEnding=true; ++Epoch; ReleaseStudies(); OnViewChanged.Broadcast(this); Super::EndPlay(Reason); }
