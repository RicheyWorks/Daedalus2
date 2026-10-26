// SPDX-License-Identifier: MIT
#include "DaedalusGalleryMotifFlipbook.h"
#include "DaedalusGalleryMotifRack.h"
#include "DaedalusGalleryMotifNative.h"
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

namespace DaedalusFlipbookLocal
{
    constexpr int32 ButtonCount=6;
    const TCHAR* CommandName(int32 Command)
    {
        static const TCHAR* Names[]={TEXT("Play / Pause"),TEXT("Previous frame"),TEXT("Next frame"),TEXT("Reverse direction"),TEXT("Speed 2 / 4 fps"),TEXT("First frame")};
        return Command>=0 && Command<ButtonCount?Names[Command]:TEXT("Unavailable");
    }
    bool Placement(const FTransform& Pose)
    { return !Pose.ContainsNaN() && Pose.GetRotation().IsNormalized() && Pose.GetScale3D().Equals(FVector::OneVector,0.001) && Pose.GetRotation().RotateVector(FVector::UpVector).Equals(FVector::UpVector,0.001); }
    bool LocalPlayer(const ADaedalusHero* Hero,const AActor* Target,const APlayerController* Expected,bool Reach)
    {
        const auto PairAlive=[&]()
        {
            return IsInGameThread() && IsValid(Hero) && Hero->HasActorBegunPlay() && !Hero->IsActorBeingDestroyed() &&
                IsValid(Target) && Target->HasActorBegunPlay() && !Target->IsActorBeingDestroyed() && Target->GetWorld() &&
                Hero->GetWorld()==Target->GetWorld() && Target->GetWorld()->GetNetMode()==NM_Standalone;
        };
        if (!PairAlive() || !Hero->IsLocallyControlled() || !PairAlive()) return false;
        const auto* Player=Cast<APlayerController>(Hero->GetController());
        if (!IsValid(Player) || Player->IsActorBeingDestroyed() || !Player->HasActorBegunPlay() || Player->GetWorld()!=Target->GetWorld() ||
            !Player->IsLocalController() || !PairAlive()) return false;
        if (!IsValid(Player) || Player->IsActorBeingDestroyed() || !Player->HasActorBegunPlay() || Player->GetWorld()!=Target->GetWorld() ||
            Hero->GetController()!=Player || Player->GetPawn()!=Hero || !IsValid(Player->GetLocalPlayer()) || (Expected && Player!=Expected)) return false;
        if (!Reach) return true;
        const double D=FVector::DistSquared(Hero->GetActorLocation(),Target->GetActorLocation());
        return FMath::IsFinite(Hero->InteractReach) && Hero->InteractReach>0 && FMath::IsFinite(D) && D<=static_cast<double>(Hero->InteractReach)*Hero->InteractReach;
    }
    FString Wrap(const FString& Text)
    {
        TArray<FString> Lines; Text.ParseIntoArrayLines(Lines,false); FString Out;
        for (int32 I=0;I<Lines.Num();++I)
        {
            if (I) Out+=TEXT("\n"); TArray<FString> Words; Lines[I].ParseIntoArray(Words,TEXT(" "),true); int32 Columns=0;
            for (const auto& Word:Words)
            {
                if (Columns && Columns+1+Word.Len()>36) { Out+=TEXT("\n"); Columns=0; }
                if (Columns) { Out+=TEXT(" "); ++Columns; } Out+=Word; Columns+=Word.Len();
            }
        }
        return Out;
    }
    struct Ink
    {
        TArray<FVector> Vertices; TArray<int32> Triangles; TArray<FLinearColor> Colours;
        void Tile(double X,double Y,double Z,double Radius,FLinearColor Colour)
        {
            const int32 I=Vertices.Num(); Vertices.Append({FVector(X,Y-Radius,Z-Radius),FVector(X,Y+Radius,Z-Radius),FVector(X,Y+Radius,Z+Radius),FVector(X,Y-Radius,Z+Radius)});
            Triangles.Append({I,I+1,I+2,I,I+2,I+3}); Colours.Append({Colour,Colour,Colour,Colour});
        }
        void Image(const daedalus::motif::Image& Pixels,double X,double Y,double Top,double CellSize)
        {
            for (int32 I=0;I<64;++I) Tile(X,Y-(I%8-3.5)*CellSize,Top-(I/8+0.5)*CellSize,CellSize*0.485,DaedalusMotifNative::PaletteColour(Pixels[static_cast<size_t>(I)]));
        }
    };
}

ADaedalusMotifFlipbookButton::ADaedalusMotifFlipbookButton()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    ButtonRoot=CreateDefaultSubobject<USceneComponent>(TEXT("FlipbookButtonRoot")); RootComponent=ButtonRoot;
    Body->SetupAttachment(ButtonRoot); Glow->SetupAttachment(ButtonRoot); Glow->SetIntensity(0); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeLocation(FVector(0,0,30)); Body->SetRelativeScale3D(FVector(0.65,0.65,0.6));
    Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Label=CreateDefaultSubobject<UTextRenderComponent>(TEXT("FlipbookButtonLabel")); Label->SetupAttachment(ButtonRoot);
    Label->SetRelativeLocation(FVector(0,0,63)); Label->SetRelativeRotation(FRotator(90,0,0)); Label->SetWorldSize(7);
    Label->SetHorizontalAlignment(EHTA_Center); Label->SetVerticalAlignment(EVRTA_TextCenter); Label->SetTextRenderColor(FColor(25,35,50));
    Label->SetText(FText::FromString(TEXT("UNAVAILABLE")));
}
bool ADaedalusMotifFlipbookButton::ViewsReady() const
{
    return !bEnding && HasActorBegunPlay() && !IsActorBeingDestroyed() && IsValid(ButtonRoot) && GetRootComponent()==ButtonRoot &&
        ButtonRoot->GetOwner()==this && ButtonRoot->IsRegistered() && ButtonRoot->GetAttachParent()==nullptr &&
        IsValid(Body) && Body->GetOwner()==this && Body->IsRegistered() && Body->GetStaticMesh() &&
        IsValid(Label) && Label->GetOwner()==this && Label->IsRegistered() && Label->GetAttachParent()==ButtonRoot;
}
FString ADaedalusMotifFlipbookButton::Prompt(const ADaedalusHero* Hero) const
{ const auto* Parent=Bench.Get(); return Parent && Parent->ButtonReady(this,Command,true)?Parent->ButtonPrompt(Hero,Command):TEXT("Flipbook button unavailable"); }
bool ADaedalusMotifFlipbookButton::Use(ADaedalusHero* Hero)
{ auto* Parent=Bench.Get(); return Parent && Parent->Operate(Hero,this); }
void ADaedalusMotifFlipbookButton::EndPlay(const EEndPlayReason::Type Reason)
{ bEnding=true; Super::EndPlay(Reason); }

ADaedalusGalleryMotifFlipbook::ADaedalusGalleryMotifFlipbook()
{
    PrimaryActorTick.bCanEverTick=true; PrimaryActorTick.bStartWithTickEnabled=false; PrimaryActorTick.TickInterval=0.05f;
    bReplicates=false; SetActorEnableCollision(false);
    BenchRoot=CreateDefaultSubobject<USceneComponent>(TEXT("FlipbookBenchRoot")); RootComponent=BenchRoot;
    Body->SetupAttachment(BenchRoot); Glow->SetupAttachment(BenchRoot); Glow->SetIntensity(0); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Engine/EngineDebugMaterials/VertexColorMaterial.VertexColorMaterial")); InkMaterial=Material.Object;
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeLocation(FVector(0,0,230)); Body->SetRelativeScale3D(FVector(0.12,2.6,2.6)); Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    auto* Placard=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FlipbookMetadataPanel")); Placard->SetupAttachment(BenchRoot); Placard->SetStaticMesh(Cube.Object);
    Placard->SetRelativeLocation(FVector(0,-330,230)); Placard->SetRelativeScale3D(FVector(0.12,2.4,2.6)); Placard->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mosaic=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("FlipbookPreviewMosaic")); Mosaic->SetupAttachment(BenchRoot);
    Mosaic->SetCollisionEnabled(ECollisionEnabled::NoCollision); Mosaic->SetCastShadow(false);
    auto* Title=CreateDefaultSubobject<UTextRenderComponent>(TEXT("FlipbookTitle")); Title->SetupAttachment(BenchRoot);
    Title->SetRelativeLocation(FVector(15,0,385)); Title->SetWorldSize(22); Title->SetHorizontalAlignment(EHTA_Center);
    Title->SetTextRenderColor(FColor(25,35,50)); Title->SetText(FText::FromString(TEXT("MOTIF FLIPBOOK")));
    Readout=CreateDefaultSubobject<UTextRenderComponent>(TEXT("FlipbookMetadata")); Readout->SetupAttachment(BenchRoot);
    Readout->SetRelativeLocation(FVector(15,-330,345)); Readout->SetWorldSize(8.5f); Readout->SetHorizontalAlignment(EHTA_Center);
    Readout->SetVerticalAlignment(EVRTA_TextTop); Readout->SetTextRenderColor(FColor(25,35,50));
    for (int32 I=0;I<4;++I)
    {
        auto* Label=CreateDefaultSubobject<UTextRenderComponent>(*FString::Printf(TEXT("FlipbookThumbnail%d"),I)); Label->SetupAttachment(BenchRoot);
        Label->SetRelativeLocation(FVector(15,(1.5-I)*70,28)); Label->SetWorldSize(9); Label->SetHorizontalAlignment(EHTA_Center);
        Label->SetVerticalAlignment(EVRTA_TextCenter); Label->SetTextRenderColor(FColor(25,35,50)); ThumbnailLabels.Add(Label);
    }
}
bool ADaedalusGalleryMotifFlipbook::Alive() const
{ return IsInGameThread() && !bEnding && HasActorBegunPlay() && !IsActorBeingDestroyed() && GetWorld(); }
bool ADaedalusGalleryMotifFlipbook::ViewsReady() const
{
    if (!Alive() || GetActorEnableCollision() || !InkMaterial || !IsValid(BenchRoot) || GetRootComponent()!=BenchRoot || BenchRoot->GetOwner()!=this ||
        !BenchRoot->IsRegistered() || BenchRoot->GetAttachParent()!=nullptr || !IsValid(Body) || Body->GetOwner()!=this || !Body->IsRegistered() || !Body->GetStaticMesh() ||
        !IsValid(Readout) || Readout->GetOwner()!=this || !Readout->IsRegistered() || !IsValid(Mosaic) || Mosaic->GetOwner()!=this || !Mosaic->IsRegistered() ||
        Mosaic->GetAttachParent()!=BenchRoot || !Mosaic->GetRelativeTransform().Equals(FTransform::Identity,0.001) || ThumbnailLabels.Num()!=4) return false;
    for (const auto& Label:ThumbnailLabels) if (!IsValid(Label) || Label->GetOwner()!=this || !Label->IsRegistered() || Label->GetAttachParent()!=BenchRoot) return false;
    return Mosaic->GetNumSections()>0 && Mosaic->GetMaterial(0);
}
void ADaedalusGalleryMotifFlipbook::Unavailable(const FString& Why) const
{ if (!bUnavailable) { bUnavailable=true; Fault=Why; } }
FTransform ADaedalusGalleryMotifFlipbook::ButtonPose(int32 Command) const
{ return FTransform(FVector(180,(Command-2.5)*90,0))*FrozenFrame; }
bool ADaedalusGalleryMotifFlipbook::ButtonReady(const ADaedalusMotifFlipbookButton* Button,int32 Command,bool Begun) const
{
    return Alive() && Command>=0 && Command<DaedalusFlipbookLocal::ButtonCount && Buttons.IsValidIndex(Command) && Buttons[Command].Get()==Button &&
        IsValid(Button) && Button->GetClass()==ADaedalusMotifFlipbookButton::StaticClass() && !Button->IsActorBeingDestroyed() && Button->GetOwner()==this &&
        Button->GetWorld()==GetWorld() && Button->Bench.Get()==this && Button->Command==Command && !Button->GetActorEnableCollision() &&
        IsValid(Button->GetRootComponent()) && Button->GetRootComponent()->GetAttachParent()==nullptr && Button->GetActorTransform().Equals(ButtonPose(Command),0.01) &&
        (!Begun || Button->ViewsReady());
}
bool ADaedalusGalleryMotifFlipbook::ObserveBench() const
{
    if (!Alive() || bUnavailable) return false;
    if (!ViewsReady()) { Unavailable(TEXT("Preview display unavailable. Copied images and metadata stay.")); return false; }
    if (!bAttempted) return true;
    if (!GetActorTransform().Equals(FrozenFrame,0.01))
    { Unavailable(TEXT("The bench moved. Playback pauses; the captured frames stay unchanged.")); return false; }
    if (!bPrepared) return true;
    if (!Artist.IsValid() || Artist->IsActorBeingDestroyed() || !Controller.IsValid() || Controller->IsActorBeingDestroyed() ||
        Artist->GetWorld()!=GetWorld() || Controller->GetWorld()!=GetWorld() || Artist->GetController()!=Controller.Get() || Controller->GetPawn()!=Artist.Get())
    { Unavailable(TEXT("The original artist/controller changed. Captured frames stay; use a new bench for another artist.")); return false; }
    for (int32 I=0;I<DaedalusFlipbookLocal::ButtonCount;++I) if (!ButtonReady(Buttons.IsValidIndex(I)?Buttons[I].Get():nullptr,I,true))
    { Unavailable(TEXT("A playback button changed or ended. Images are kept; no button is replaced.")); return false; }
    return true;
}
void ADaedalusGalleryMotifFlipbook::Refresh()
{
    if (!Alive() || bNotifying) return; const uint64 Before=Epoch;
    if (bAttempted) ObserveBench();
    if (bUnavailable && Book.Playing()) { Book.TogglePlay(); SetActorTickEnabled(false); }
    DaedalusFlipbookLocal::Ink Drawing;
    Drawing.Tile(8,0,230,124,FLinearColor(0.07f,0.12f,0.17f));
    if (const auto* Current=Book.Frame(Book.Index())) Drawing.Image(Current->Pixels,10,0,350,30);
    for (int32 I=0;I<4;++I)
    {
        const double Y=(1.5-I)*70; const bool Selected=Book.Active() && Book.Index()==I;
        Drawing.Tile(8,Y,72,31,Selected?FLinearColor(1.f,0.7f,0.18f):FLinearColor(0.07f,0.12f,0.17f));
        if (const auto* Frame=Book.Frame(I)) Drawing.Image(Frame->Pixels,10,Y,100,7);
        if (ThumbnailLabels.IsValidIndex(I) && IsValid(ThumbnailLabels[I]) && ThumbnailLabels[I]->GetOwner()==this)
            ThumbnailLabels[I]->SetText(FText::FromString(I<Book.Count()?FString::Printf(TEXT("%d%s"),I+1,Selected?TEXT(" / NOW"):TEXT("")):TEXT("EMPTY")));
        if (!Alive() || Epoch!=Before) return;
    }
    if (IsValid(Mosaic) && Mosaic->GetOwner()==this && Mosaic->IsRegistered() && InkMaterial)
    {
        TArray<FVector> Normals; Normals.Init(FVector(1,0,0),Drawing.Vertices.Num());
        Mosaic->CreateMeshSection_LinearColor(0,Drawing.Vertices,Drawing.Triangles,Normals,TArray<FVector2D>(),Drawing.Colours,TArray<FProcMeshTangent>(),false);
        if (!Alive() || Epoch!=Before) return;
        if (IsValid(Mosaic) && Mosaic->GetOwner()==this) Mosaic->SetMaterial(0,InkMaterial);
    }
    if (!Alive() || Epoch!=Before) return;
    FString Text=TEXT("LOCAL PREVIEW COPY\n");
    if (const auto* Frame=Book.Frame(Book.Index()))
    {
        Text+=FString::Printf(TEXT("FRAME %d / %d / %s\n%d FPS / %s\nID\n"),Book.Index()+1,Book.Count(),Book.Playing()?TEXT("PLAYING"):TEXT("PAUSED"),Book.Fps(),Book.Direction()>0?TEXT("FORWARD"):TEXT("REVERSE"));
        Text+=FString(UTF8_TO_TCHAR(Frame->Id.c_str()))+TEXT("\nPARENT\n")+(Frame->Parent.empty()?TEXT("none"):FString(UTF8_TO_TCHAR(Frame->Parent.c_str())))+TEXT("\n");
    }
    else Text+=TEXT("NOT CAPTURED\n2 to 4 captured studies required.\n");
    Text+=bUnavailable?Fault:Notice;
    if (IsValid(Readout) && Readout->GetOwner()==this) Readout->SetText(FText::FromString(DaedalusFlipbookLocal::Wrap(Text)));
    if (!Alive() || Epoch!=Before) return;
    for (int32 I=0;I<Buttons.Num();++I) if (ButtonReady(Buttons[I],I,true))
    {
        FString Label=DaedalusFlipbookLocal::CommandName(I);
        if (I==0) Label=Book.Playing()?TEXT("PAUSE"):TEXT("PLAY");
        else if (I==1) Label=TEXT("PREVIOUS"); else if (I==2) Label=TEXT("NEXT");
        else if (I==3) Label=Book.Direction()>0?TEXT("REVERSE"):TEXT("FORWARD");
        else if (I==4) Label=FString::Printf(TEXT("SPEED\n%d FPS"),Book.Fps()); else if (I==5) Label=TEXT("FIRST\nFRAME");
        Buttons[I]->Label->SetText(FText::FromString(Label)); if (!Alive() || Epoch!=Before) return;
    }
    TGuardValue<bool> Notification(bNotifying,true); OnViewChanged.Broadcast(this);
}
void ADaedalusGalleryMotifFlipbook::BeginPlay()
{
    bEnding=false; ++Epoch; Super::BeginPlay(); if (!Alive()) return; SetActorTickEnabled(false);
    Notice=TEXT("Bind a local rack. Prepare and capture 2 to 4 studies. E / X copies them once, initially paused; use PLAY deliberately.");
    Refresh(); // No source capture, file IO, controls or autoplay during startup.
}
FString ADaedalusGalleryMotifFlipbook::Prompt(const ADaedalusHero* Hero) const
{
    if (!Alive() || GetWorld()->GetNetMode()!=NM_Standalone || !ObserveBench()) return TEXT("Flipbook unavailable; copied frames kept");
    if (bPrepared) return Hero==Artist.Get()?TEXT("E / X: Pause / read frozen flipbook metadata"):TEXT("This local preview keeps its original artist");
    if (bAttempted) return TEXT("Setup stopped; captured frames and partial buttons kept");
    return TEXT("E / X: Copy 2 to 4 captured rack studies into a paused flipbook");
}
FString ADaedalusGalleryMotifFlipbook::ButtonPrompt(const ADaedalusHero* Hero,int32 Command) const
{
    if (!ObserveBench() || !bPrepared) return TEXT("Playback unavailable; frames kept");
    if (Hero!=Artist.Get()) return TEXT("This preview belongs to its original local artist");
    return FString::Printf(TEXT("E / X: %s"),DaedalusFlipbookLocal::CommandName(Command));
}
void ADaedalusGalleryMotifFlipbook::RememberEffect(AActor* Actor)
{ if (Alive() && IsValid(Actor)) SetupEffects.AddUnique(Actor); }
bool ADaedalusGalleryMotifFlipbook::PrepareButtons(ADaedalusHero* Hero)
{
    const uint64 Before=Epoch; Buttons.SetNum(DaedalusFlipbookLocal::ButtonCount); const TWeakObjectPtr<ADaedalusGalleryMotifFlipbook> Self(this);
    const auto Participants=[&]()
    {
        if (!Alive() || Epoch!=Before || !Controller.IsValid() || !DaedalusFlipbookLocal::LocalPlayer(Hero,this,Controller.Get(),true)) return false;
        if (!Alive() || Epoch!=Before || !ObserveBench() || Hero!=Artist.Get()) return false;
        for (int32 I=0;I<Buttons.Num();++I) if (Buttons[I] && !ButtonReady(Buttons[I],I,Buttons[I]->HasActorBegunPlay())) return false;
        return true;
    };
    for (int32 I=0;I<DaedalusFlipbookLocal::ButtonCount;++I)
    {
        if (!Participants()) return false;
        const FTransform Pose=ButtonPose(I); TWeakObjectPtr<ADaedalusMotifFlipbookButton> Staged; const ADaedalusMotifFlipbookButton* Identity=nullptr;
        FActorSpawnParameters P; P.Owner=this; P.ObjectFlags=RF_Transient|RF_DuplicateTransient; P.bDeferConstruction=true;
        P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        P.CustomPreSpawnInitialization=[Self,Before,I,&Staged,&Identity](AActor* Actor)
        {
            if (!Actor || Actor->GetClass()!=ADaedalusMotifFlipbookButton::StaticClass()) return;
            auto* Button=Cast<ADaedalusMotifFlipbookButton>(Actor); Staged=Button; Identity=Button;
            auto* Owner=Self.Get(); if (!Owner || !Owner->Alive() || Owner->Epoch!=Before || !Owner->Buttons.IsValidIndex(I)) return;
            Owner->RememberEffect(Button); Owner->Buttons[I]=Button; Button->Bench=Owner; Button->Command=I;
            Button->OnEndPlay.AddUniqueDynamic(Owner,&ADaedalusGalleryMotifFlipbook::ButtonEnded);
        };
        auto* Candidate=GetWorld()->SpawnActor<ADaedalusMotifFlipbookButton>(ADaedalusMotifFlipbookButton::StaticClass(),Pose,P);
        const auto ReconcileEnded=[&]()
        {
            TArray<TWeakObjectPtr<ADaedalusMotifFlipbookButton>> Effects;
            if (IsValid(Candidate)) Effects.AddUnique(TWeakObjectPtr<ADaedalusMotifFlipbookButton>(Candidate)); if (Staged.IsValid()) Effects.AddUnique(Staged);
            for (const auto& Effect:Effects) if (auto* Button=Effect.Get())
            {
                Button->OnEndPlay.RemoveDynamic(this,&ADaedalusGalleryMotifFlipbook::ButtonEnded);
                if (Button->GetClass()==ADaedalusMotifFlipbookButton::StaticClass() && Button->GetOwner()==this && !Button->IsActorBeingDestroyed()) Button->Destroy();
            }
        };
        if (!Alive()) { ReconcileEnded(); return false; }
        RememberEffect(Candidate);
        const auto Valid=[&](bool Begun) { return Participants() && Candidate==Identity && Staged.Get()==Candidate && ButtonReady(Candidate,I,Begun); };
        if (!Valid(false)) return false;
        Candidate->FinishSpawning(Pose); if (!Alive()) { ReconcileEnded(); return false; }
        if (!Valid(true)) return false;
    }
    return Participants();
}
bool ADaedalusGalleryMotifFlipbook::Use(ADaedalusHero* Hero)
{
    const uint64 Before=Epoch;
    if (!Alive() || bBusy || bNotifying || !DaedalusFlipbookLocal::LocalPlayer(Hero,this,nullptr,true) || !Alive() || Epoch!=Before) return false;
    TGuardValue<bool> Busy(bBusy,true);
    if (!ObserveBench()) { Refresh(); return false; }
    if (bAttempted)
    {
        if (bPrepared && Hero==Artist.Get()) { if (Book.Playing()) Book.TogglePlay(); SetActorTickEnabled(false); Notice=TEXT("Paused for inspection. Step to compare images, or use PLAY to continue. Captured frames are unchanged."); }
        Refresh(); return bPrepared && Hero==Artist.Get() && !bUnavailable;
    }
    if (!DaedalusFlipbookLocal::Placement(GetActorTransform()))
    { Notice=TEXT("Place the bench upright at unit size on existing safe ground."); Refresh(); return false; }
    auto* Rack=SourceRack.Get(); std::array<daedalus::motif::Document,4> Frames{}; int32 Count=0; FString Error;
    if (!IsValid(Rack) || Rack->IsActorBeingDestroyed() || Rack->GetWorld()!=GetWorld() || !Rack->CopyCapturedFrames(Frames,Count,Error))
    { Notice=Error.IsEmpty()?TEXT("Bind a ready local rack with 2 to 4 captured studies first."):Error; Refresh(); return false; }
    daedalus::flipbook::Player Prepared;
    if (!Prepared.Capture(Frames,Count))
    { Notice=TEXT("Capture 2 to 4 ready studies with distinct local IDs. Each prepared rack slot must be captured; nothing was replaced."); Refresh(); return false; }
    const FTransform Frame=GetActorTransform(); const TWeakObjectPtr<APlayerController> Player(Cast<APlayerController>(Hero->GetController()));
    if (!Player.IsValid() || !DaedalusFlipbookLocal::LocalPlayer(Hero,this,Player.Get(),true) || !Alive() || Epoch!=Before ||
        !ObserveBench() || !GetActorTransform().Equals(Frame,0.01) || SourceRack.Get()!=Rack || !IsValid(Rack) || Rack->IsActorBeingDestroyed()) return false;
    bAttempted=true; FrozenFrame=Frame; Artist=Hero; Controller=Player; Book=Prepared;
    const bool Ready=PrepareButtons(Hero); if (!Alive() || Epoch!=Before) return false;
    if (!Ready) Unavailable(TEXT("Preview setup stopped. Copied frames and partial buttons are kept; no automatic retry or replacement."));
    else { bPrepared=true; Notice=TEXT("Paused at frame 1. PLAY starts 2 fps; Previous/Next pause. Reverse changes direction; Speed toggles 2/4 fps. New frames need a new bench."); ObserveBench(); }
    Refresh(); return Alive() && bPrepared && !bUnavailable;
}
bool ADaedalusGalleryMotifFlipbook::Operate(ADaedalusHero* Hero,ADaedalusMotifFlipbookButton* Button)
{
    if (!Alive() || bBusy || bNotifying || !ObserveBench() || !bPrepared || Hero!=Artist.Get() || !IsValid(Button) || !ButtonReady(Button,Button->Command,true)) return false;
    const uint64 Before=Epoch;
    if (!DaedalusFlipbookLocal::LocalPlayer(Hero,Button,Controller.Get(),true) || !Alive() || Epoch!=Before || !ObserveBench() || !ButtonReady(Button,Button->Command,true)) return false;
    TGuardValue<bool> Busy(bBusy,true); bool Changed=false;
    switch (Button->Command)
    {
    case 0:Changed=Book.TogglePlay(); break; case 1:Changed=Book.Step(-1); break; case 2:Changed=Book.Step(1); break;
    case 3:Changed=Book.Reverse(); break; case 4:Changed=Book.CycleSpeed(); break; case 5:Changed=Book.FirstFrame(); break; default:return false;
    }
    SetActorTickEnabled(Book.Playing()); Notice=TEXT("Local preview only. Pixels, original studies and kept files never change."); Refresh(); return Changed;
}
void ADaedalusGalleryMotifFlipbook::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!Alive() || bBusy || bNotifying || !bPrepared || !Book.Playing()) return; const uint64 Before=Epoch;
    if (!ObserveBench()) { if (Book.Playing()) Book.TogglePlay(); SetActorTickEnabled(false); Refresh(); return; }
    if (!DaedalusFlipbookLocal::LocalPlayer(Artist.Get(),this,Controller.Get(),false) || !Alive() || Epoch!=Before || !ObserveBench())
    { if (Alive()) { if (Book.Playing()) Book.TogglePlay(); SetActorTickEnabled(false); Notice=TEXT("Playback paused because the original local artist is unavailable. Captured images stay."); Refresh(); } return; }
    TGuardValue<bool> Busy(bBusy,true); if (Book.Advance(DeltaSeconds)) Refresh();
}
void ADaedalusGalleryMotifFlipbook::ButtonEnded(AActor* Actor,EEndPlayReason::Type)
{
    if (!Alive() || !Actor) return; bool Found=false; for (const auto& Effect:SetupEffects) if (Effect.Get()==Actor) { Found=true; break; }
    if (!Found) return; Unavailable(TEXT("A playback button ended. Captured frames stay; this bench will not replace it."));
    if (!bBusy && !bNotifying) Refresh();
}
void ADaedalusGalleryMotifFlipbook::ReleaseEffects()
{
    const auto Effects=SetupEffects; SetupEffects.Reset(); Buttons.Reset();
    for (const auto& Entry:Effects) if (IsValid(Entry.Get())) Entry->OnEndPlay.RemoveDynamic(this,&ADaedalusGalleryMotifFlipbook::ButtonEnded);
    for (const auto& Entry:Effects) if (auto* Actor=Entry.Get())
        if (IsValid(Actor) && Actor->GetClass()==ADaedalusMotifFlipbookButton::StaticClass() && Actor->GetOwner()==this && !Actor->IsActorBeingDestroyed()) Actor->Destroy();
}
void ADaedalusGalleryMotifFlipbook::EndPlay(const EEndPlayReason::Type Reason)
{ bEnding=true; ++Epoch; SetActorTickEnabled(false); ReleaseEffects(); Super::EndPlay(Reason); }
