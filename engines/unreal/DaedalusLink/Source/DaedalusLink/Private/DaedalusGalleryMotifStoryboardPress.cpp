// SPDX-License-Identifier: MIT
#include "DaedalusGalleryMotifStoryboardPress.h"
#include "DaedalusGalleryMotifStoryboardCore.h"
#include "DaedalusGalleryMotifFlipbook.h"
#include "DaedalusGalleryMotifNative.h"
#include "DaedalusLocalSvgFiles.h"
#include "DaedalusHero.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/Guid.h"
#include "Templates/UnrealTemplate.h"
#include "UObject/ConstructorHelpers.h"

namespace DaedalusStoryboardLocal
{
    static_assert(daedalus::storyboard::MaxSvgBytes==DaedalusLocalSvgFiles::MaxBytes,"SVG renderer/writer bounds agree");
    std::string Utf8(const FString& Text)
    { const FTCHARToUTF8 Encoded(*Text,Text.Len()); return std::string(Encoded.Get(),static_cast<size_t>(Encoded.Length())); }
    bool LocalReach(const ADaedalusHero* Hero,const AActor* Press,const APlayerController* Expected=nullptr)
    {
        const auto PairAlive=[&]()
        {
            return IsInGameThread() && IsValid(Hero) && Hero->HasActorBegunPlay() && !Hero->IsActorBeingDestroyed() &&
                IsValid(Press) && Press->HasActorBegunPlay() && !Press->IsActorBeingDestroyed() && Press->GetWorld() &&
                Hero->GetWorld()==Press->GetWorld() && Press->GetWorld()->GetNetMode()==NM_Standalone;
        };
        if (!PairAlive() || !Hero->IsLocallyControlled() || !PairAlive()) return false;
        const auto* Player=Cast<APlayerController>(Hero->GetController());
        if (!IsValid(Player) || Player->IsActorBeingDestroyed() || !Player->HasActorBegunPlay() || Player->GetWorld()!=Press->GetWorld() ||
            !Player->IsLocalController() || !PairAlive()) return false;
        if (!IsValid(Player) || Player->IsActorBeingDestroyed() || !Player->HasActorBegunPlay() || Player->GetWorld()!=Press->GetWorld() ||
            Hero->GetController()!=Player || Player->GetPawn()!=Hero || !IsValid(Player->GetLocalPlayer()) || (Expected && Player!=Expected)) return false;
        const double D=FVector::DistSquared(Hero->GetActorLocation(),Press->GetActorLocation());
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
                if (Columns && Columns+1+Word.Len()>38) { Out+=TEXT("\n"); Columns=0; }
                if (Columns) { Out+=TEXT(" "); ++Columns; } Out+=Word; Columns+=Word.Len();
            }
        }
        return Out;
    }
}

ADaedalusGalleryMotifStoryboardPress::ADaedalusGalleryMotifStoryboardPress()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    PressRoot=CreateDefaultSubobject<USceneComponent>(TEXT("StoryboardPressRoot")); RootComponent=PressRoot;
    Body->SetupAttachment(PressRoot); Glow->SetupAttachment(PressRoot); Glow->SetIntensity(0); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeLocation(FVector(0,0,65)); Body->SetRelativeScale3D(FVector(0.7,1.3,1.1)); Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Readout=CreateDefaultSubobject<UTextRenderComponent>(TEXT("StoryboardPressReadout")); Readout->SetupAttachment(PressRoot);
    Readout->SetRelativeLocation(FVector(40,0,290)); Readout->SetWorldSize(10); Readout->SetHorizontalAlignment(EHTA_Center);
    Readout->SetVerticalAlignment(EVRTA_TextTop); Readout->SetTextRenderColor(FColor(25,35,50));
}
bool ADaedalusGalleryMotifStoryboardPress::Alive() const
{ return IsInGameThread() && !bEnding && HasActorBegunPlay() && !IsActorBeingDestroyed() && GetWorld(); }
bool ADaedalusGalleryMotifStoryboardPress::ViewsReady() const
{
    return Alive() && !GetActorEnableCollision() && IsValid(PressRoot) && GetRootComponent()==PressRoot && PressRoot->GetOwner()==this && PressRoot->IsRegistered() &&
        PressRoot->GetAttachParent()==nullptr && IsValid(Body) && Body->GetOwner()==this && Body->IsRegistered() && Body->GetStaticMesh() &&
        IsValid(Readout) && Readout->GetOwner()==this && Readout->IsRegistered() && Readout->GetAttachParent()==PressRoot;
}
bool ADaedalusGalleryMotifStoryboardPress::SourceReady() const
{
    const auto* Source=SourceFlipbook.Get();
    return Alive() && GetWorld()->GetNetMode()==NM_Standalone && IsValid(Source) && !Source->IsActorBeingDestroyed() && Source->HasActorBegunPlay() &&
        Source->GetWorld()==GetWorld() && Source->FrameCount()>=2 && Source->FrameCount()<=4 && (!bFrozen || FrozenSource.Get()==Source);
}
void ADaedalusGalleryMotifStoryboardPress::Refresh(const FString& KeptId)
{
    if (!Alive() || bNotifying) return; const uint64 Before=Epoch;
    FString Text=TEXT("MOTIF STORYBOARD PRESS\nSTATIC LOCAL CONTACT SHEET\n");
    if (!LastPrintId.empty())
    {
        Text+=TEXT("LAST VERIFIED PRINT ID\n")+FString(UTF8_TO_TCHAR(LastPrintId.substr(0,16).c_str()))+TEXT("\n")+
            FString(UTF8_TO_TCHAR(LastPrintId.substr(16).c_str()))+TEXT("\n");
    }
    Text+=Notice;
    if (IsValid(Readout) && Readout->GetOwner()==this) Readout->SetText(FText::FromString(DaedalusStoryboardLocal::Wrap(Text)));
    if (!Alive() || Epoch!=Before) return;
    TGuardValue<bool> Notification(bNotifying,true); OnViewChanged.Broadcast(this);
    if (!KeptId.IsEmpty() && Alive() && Epoch==Before) OnStoryboardKept.Broadcast(this,KeptId);
}
void ADaedalusGalleryMotifStoryboardPress::BeginPlay()
{
    bEnding=false; ++Epoch; Super::BeginPlay(); if (!Alive()) return;
    Notice=TEXT("Bind a captured local Flipbook. E / X keeps a fresh SVG with its frames, IDs and settings at capture. No file is created on startup."); Refresh();
}
FString ADaedalusGalleryMotifStoryboardPress::Prompt(const ADaedalusHero*) const
{
    if (!Alive() || !ViewsReady() || GetWorld()->GetNetMode()!=NM_Standalone) return TEXT("Storyboard press is unavailable here");
    if (bFrozen && (!FrozenSource.IsValid() || FrozenSource.Get()!=SourceFlipbook.Get())) return TEXT("Use a new press for another Flipbook; earlier files are kept");
    return SourceReady()?TEXT("E / X: Keep a new static SVG contact sheet of captured frames"):TEXT("Bind a Flipbook with two to four captured frames first");
}
bool ADaedalusGalleryMotifStoryboardPress::Use(ADaedalusHero* Hero)
{
    const uint64 Before=Epoch;
    if (!Alive() || bBusy || bNotifying || !DaedalusStoryboardLocal::LocalReach(Hero,this) || !Alive() || Epoch!=Before) return false;
    TGuardValue<bool> Busy(bBusy,true);
    if (!ViewsReady() || !SourceReady())
    { Notice=TEXT("The press or captured source is unavailable. Existing files and frames are kept."); Refresh(); return false; }
    const TWeakObjectPtr<ADaedalusGalleryMotifFlipbook> Source(SourceFlipbook.Get());
    const TWeakObjectPtr<ADaedalusHero> Performer(Hero); const TWeakObjectPtr<APlayerController> Player(Cast<APlayerController>(Hero->GetController()));
    const auto Participants=[&]()
    {
        if (!Alive() || Epoch!=Before || !ViewsReady() || !SourceReady() || Source.Get()!=SourceFlipbook.Get() || !Player.IsValid() ||
            !DaedalusStoryboardLocal::LocalReach(Performer.Get(),this,Player.Get())) return false;
        return Alive() && Epoch==Before && ViewsReady() && SourceReady() && Source.Get()==SourceFlipbook.Get() && Player.IsValid() &&
            Performer.IsValid() && Performer->GetController()==Player.Get() && Player->GetPawn()==Performer.Get();
    };
    daedalus::flipbook::Player Snapshot;
    if (!Source->CopyCapturedBook(Snapshot) || !Participants())
    { if (Alive()) { Notice=TEXT("The captured book could not be copied. No print was started; all source data stays."); Refresh(); } return false; }
    const FString Id=FGuid::NewGuid().ToString(EGuidFormats::DigitsLower);
    const daedalus::storyboard::Identity Identity{DaedalusStoryboardLocal::Utf8(Id),LastPrintId}; daedalus::storyboard::Palette Palette;
    for (int32 I=0;I<8;++I)
    {
        const FColor Colour=DaedalusMotifNative::PaletteColour(I).ToFColorSRGB();
        Palette[static_cast<size_t>(I)]=DaedalusStoryboardLocal::Utf8(FString::Printf(TEXT("#%02x%02x%02x"),static_cast<uint32>(Colour.R),static_cast<uint32>(Colour.G),static_cast<uint32>(Colour.B)));
    }
    std::string Bytes;
    if (!daedalus::storyboard::RenderSvg(Snapshot,Palette,Identity,Bytes) || !Participants())
    { if (Alive()) { Notice=TEXT("The static sheet could not be prepared. No print was started; the captured book is unchanged."); Refresh(); } return false; }
    FString Error; const bool Kept=DaedalusLocalSvgFiles::WriteNewVerified(DaedalusLocalSvgFiles::Kind::Storyboard,Id,Bytes,Error);
    // A fresh file may already exist if an actor ends during native IO. Keep it;
    // never describe a started write as having no effect or delete failed files.
    if (!Alive() || Epoch!=Before) return false;
    if (!Kept) { Notice=Error; Refresh(); return false; }
    LastPrintId=Identity.Id; LastFilename=DaedalusLocalSvgFiles::Filename(DaedalusLocalSvgFiles::Kind::Storyboard,Id); FrozenSource=Source; bFrozen=true;
    Notice=SourceReady()?TEXT("Static sheet saved and readback verified in Saved/Daedalus/GalleryMotif/Storyboards. Each fresh file keeps original frame order and identity. Settings are at capture, not SVG animation."):
        TEXT("The frozen sheet was saved and verified; its source changed or ended afterward. Use a new press for another Flipbook. Find this copy in Saved/Daedalus/GalleryMotif/Storyboards.");
    Refresh(Id); return Alive();
}
void ADaedalusGalleryMotifStoryboardPress::EndPlay(const EEndPlayReason::Type Reason)
{ bEnding=true; ++Epoch; Super::EndPlay(Reason); }
