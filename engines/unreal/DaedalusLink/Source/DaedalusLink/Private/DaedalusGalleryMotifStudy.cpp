// SPDX-License-Identifier: MIT
#include "DaedalusGalleryMotifStudy.h"
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

namespace DaedalusMotifStudyLocal
{
    bool LocalReach(const ADaedalusHero* Hero,const AActor* Actor)
    {
        if (!IsInGameThread() || !IsValid(Hero) || Hero->IsActorBeingDestroyed() || !Hero->HasActorBegunPlay() || !IsValid(Actor) ||
            Actor->IsActorBeingDestroyed() || !Actor->HasActorBegunPlay() || !Actor->GetWorld() || Hero->GetWorld()!=Actor->GetWorld() ||
            Actor->GetWorld()->GetNetMode()!=NM_Standalone || !Hero->IsLocallyControlled() || !FMath::IsFinite(Hero->InteractReach) || Hero->InteractReach<=0.f) return false;
        const auto* Controller=Cast<APlayerController>(Hero->GetController());
        if (!IsValid(Controller) || Controller->IsActorBeingDestroyed() || Controller->GetWorld()!=Actor->GetWorld() || !Controller->IsLocalController() ||
            Controller->GetPawn()!=Hero || !IsValid(Controller->GetLocalPlayer())) return false;
        const double D=FVector::DistSquared(Hero->GetActorLocation(),Actor->GetActorLocation());
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
                if (Columns && Columns+1+Word.Len()>34) { Out+=TEXT("\n"); Columns=0; }
                if (Columns) { Out+=TEXT(" "); ++Columns; } Out+=Word; Columns+=Word.Len();
            }
        }
        return Out;
    }
}

ADaedalusGalleryMotifStudy::ADaedalusGalleryMotifStudy()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    StudyRoot=CreateDefaultSubobject<USceneComponent>(TEXT("MotifStudyRoot")); RootComponent=StudyRoot;
    Body->SetupAttachment(StudyRoot); Glow->SetupAttachment(StudyRoot); Glow->SetIntensity(0.f); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Engine/EngineDebugMaterials/VertexColorMaterial.VertexColorMaterial")); InkMaterial=Material.Object;
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeLocation(FVector(0,0,140)); Body->SetRelativeScale3D(FVector(0.12,2.6,2.6)); Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    auto* Placard=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("MotifStudyPlacard")); Placard->SetupAttachment(StudyRoot); Placard->SetStaticMesh(Cube.Object);
    Placard->SetRelativeLocation(FVector(0,-235,150)); Placard->SetRelativeScale3D(FVector(0.12,2,2.5)); Placard->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mosaic=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("CapturedMotifMosaic")); Mosaic->SetupAttachment(StudyRoot);
    Mosaic->SetCollisionEnabled(ECollisionEnabled::NoCollision); Mosaic->SetCastShadow(false);
    auto* Title=CreateDefaultSubobject<UTextRenderComponent>(TEXT("MotifStudyTitle")); Title->SetupAttachment(StudyRoot);
    Title->SetRelativeLocation(FVector(12,0,295)); Title->SetWorldSize(21.f); Title->SetHorizontalAlignment(EHTA_Center);
    Title->SetTextRenderColor(FColor(25,40,60)); Title->SetText(FText::FromString(TEXT("LOCAL MOTIF STUDY")));
    Readout=CreateDefaultSubobject<UTextRenderComponent>(TEXT("MotifStudyReadout")); Readout->SetupAttachment(StudyRoot);
    Readout->SetRelativeLocation(FVector(12,-235,255)); Readout->SetWorldSize(8.5f); Readout->SetHorizontalAlignment(EHTA_Center);
    Readout->SetVerticalAlignment(EVRTA_TextTop); Readout->SetTextRenderColor(FColor(25,40,60));
}
bool ADaedalusGalleryMotifStudy::Alive() const
{ return IsInGameThread() && !bEnding && !IsActorBeingDestroyed() && HasActorBegunPlay() && GetWorld(); }
bool ADaedalusGalleryMotifStudy::ViewsReady() const
{
    return Alive() && IsValid(Mosaic) && Mosaic->GetOwner()==this && Mosaic->IsRegistered() && Mosaic->GetAttachParent()==StudyRoot &&
        IsValid(Readout) && Readout->GetOwner()==this && Readout->IsRegistered() && InkMaterial;
}
FString ADaedalusGalleryMotifStudy::RequestedId() const
{
    if (MotifId.Len()!=32) return FString();
    const FTCHARToUTF8 Encoded(*MotifId,MotifId.Len());
    const auto Canonical=daedalus::motif::CanonicalId(std::string(Encoded.Get(),static_cast<size_t>(Encoded.Length())));
    return FString(UTF8_TO_TCHAR(Canonical.c_str()));
}
void ADaedalusGalleryMotifStudy::Refresh()
{
    if (!Alive() || bNotifying) return;
    if (ViewsReady())
    {
        TArray<FVector> Vertices; TArray<int32> Triangles; TArray<FLinearColor> Colours;
        auto Tile=[&](double X,double Y,double Z,double Radius,FLinearColor Colour)
        {
            const int32 At=Vertices.Num(); Vertices.Append({FVector(X,Y-Radius,Z-Radius),FVector(X,Y+Radius,Z-Radius),FVector(X,Y+Radius,Z+Radius),FVector(X,Y-Radius,Z+Radius)});
            Triangles.Append({At,At+1,At+2,At,At+2,At+3}); Colours.Append({Colour,Colour,Colour,Colour});
        };
        Tile(8,0,140,124,FLinearColor(0.07f,0.12f,0.17f));
        if (bCaptured)
            for (int32 Cell=0;Cell<64;++Cell) Tile(10,-(Cell%8-3.5)*30,260-(Cell/8+0.5)*30,14.6,DaedalusMotifNative::PaletteColour(Captured.Pixels[Cell]));
        TArray<FVector> Normals; Normals.Init(FVector(1,0,0),Vertices.Num()); TArray<FVector2D> UV; UV.Init(FVector2D::ZeroVector,Vertices.Num()); TArray<FProcMeshTangent> Tangents;
        Mosaic->CreateMeshSection_LinearColor(0,Vertices,Triangles,Normals,UV,Colours,Tangents,false);
        if (!Alive()) return;
        if (ViewsReady()) Mosaic->SetMaterial(0,InkMaterial);
    }
    if (!Alive()) return;
    FString Text;
    if (bCaptured)
    {
        Text=TEXT("CAPTURED LOCAL SKETCH\nID\n")+FString(UTF8_TO_TCHAR(Captured.Id.c_str()))+TEXT("\nPARENT\n")+
            (Captured.Parent.empty()?TEXT("none / first export"):FString(UTF8_TO_TCHAR(Captured.Parent.c_str())))+TEXT("\n8 x 8 / local motif format\n");
    }
    else Text=TEXT("STUDY NOT CAPTURED\n");
    Text+=Notice;
    if (IsValid(Readout) && Readout->GetOwner()==this) Readout->SetText(FText::FromString(DaedalusMotifStudyLocal::Wrap(Text)));
    if (!Alive()) return;
    TGuardValue<bool> Notification(bNotifying,true); OnViewChanged.Broadcast(this);
}
void ADaedalusGalleryMotifStudy::BeginPlay()
{
    bEnding=false; ++Epoch; Super::BeginPlay(); if (!Alive()) return;
    // No file lookup or read on startup, including when an ID is preconfigured.
    Notice=RequestedId().IsEmpty()?TEXT("No local sketch is bound to this study."):TEXT("Use E / X to capture the bound local export. The study keeps its original copy afterward.");
    Refresh();
}
FString ADaedalusGalleryMotifStudy::Prompt(const ADaedalusHero*) const
{
    if (!Alive() || GetWorld()->GetNetMode()!=NM_Standalone) return TEXT("Local motif study is unavailable here");
    if (bCaptured) return TEXT("E / X: Read the captured study's local metadata (no file reload)");
    return RequestedId().IsEmpty()?TEXT("This study needs a local export ID"):TEXT("E / X: Capture this local motif export once");
}
bool ADaedalusGalleryMotifStudy::Use(ADaedalusHero* Hero)
{
    if (!Alive() || bBusy || bNotifying || !DaedalusMotifStudyLocal::LocalReach(Hero,this)) return false;
    if (!Alive()) return false; TGuardValue<bool> Busy(bBusy,true);
    if (!ViewsReady()) { Notice=TEXT("The study view is unavailable. Any captured sketch is kept unchanged."); Refresh(); return false; }
    if (bCaptured)
    { Notice=TEXT("This actor keeps its captured copy. A different export or version needs a new study actor."); Refresh(); return Alive(); }
    const FString Requested=RequestedId();
    if (Requested.IsEmpty()) { Notice=TEXT("No valid local sketch ID is bound. The study is unchanged."); Refresh(); return false; }
    const uint64 StartEpoch=Epoch; daedalus::motif::Document Prepared; std::string Bytes; FString Error;
    if (!DaedalusMotifNative::ReadLocalExport(Requested,Prepared,Bytes,Error))
    {
        if (Alive())
        {
#if PLATFORM_WINDOWS
            Notice=TEXT("Study not captured. ")+Error.Replace(TEXT("draft"),TEXT("study"));
#else
            Notice=TEXT("Local motif file loading needs Windows in this edition. This study remains uncaptured.");
#endif
            Refresh();
        }
        return false;
    }
    if (!Alive() || Epoch!=StartEpoch) return false;
    if (!ViewsReady() || bCaptured || RequestedId()!=Requested || FString(UTF8_TO_TCHAR(Prepared.Id.c_str()))!=Requested)
    { Notice=TEXT("The study or its binding changed before capture. Nothing was replaced; try again when ready."); Refresh(); return false; }
    Captured=Prepared; bCaptured=true;
    Notice=TEXT("Captured from a validated local export. The image and metadata stay fixed for this actor's lifetime.");
    Refresh(); return Alive();
}
void ADaedalusGalleryMotifStudy::EndPlay(const EEndPlayReason::Type Reason)
{
    bEnding=true; ++Epoch; OnViewChanged.Broadcast(this); Super::EndPlay(Reason);
}
