// SPDX-License-Identifier: MIT
#include "DaedalusBricksBlueprintPress.h"
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
#include "HAL/FileManager.h"
#include "Misc/Guid.h"
#include "Misc/Paths.h"
#include "Templates/UnrealTemplate.h"
#include "UObject/ConstructorHelpers.h"
#if PLATFORM_WINDOWS
#include "Windows/WindowsHWrapper.h"
#endif

namespace DaedalusBlueprintPressLocal
{
    std::string Utf8(const FString& Text)
    { const FTCHARToUTF8 Value(*Text,Text.Len()); return std::string(Value.Get(),static_cast<size_t>(Value.Length())); }
    FString Folder()
    { return FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("Daedalus"),TEXT("BlueprintPrints"))); }
    FString Filename(const FString& Id) { return TEXT("Blueprint_")+Id+TEXT(".svg"); }
    bool LocalReach(const ADaedalusHero* Hero,const AActor* Press,const APlayerController* Expected=nullptr)
    {
        if (!IsInGameThread() || !IsValid(Hero) || Hero->IsActorBeingDestroyed() || !Hero->HasActorBegunPlay() || !IsValid(Press) ||
            Press->IsActorBeingDestroyed() || !Press->HasActorBegunPlay() || !Press->GetWorld() || Hero->GetWorld()!=Press->GetWorld() ||
            Press->GetWorld()->GetNetMode()!=NM_Standalone || !FMath::IsFinite(Hero->InteractReach) || Hero->InteractReach<=0.f) return false;
        if (!Hero->IsLocallyControlled()) return false;
        if (!IsValid(Hero) || Hero->IsActorBeingDestroyed() || !IsValid(Press) || Press->IsActorBeingDestroyed() || Hero->GetWorld()!=Press->GetWorld()) return false;
        const auto* Player=Cast<APlayerController>(Hero->GetController());
        if (!IsValid(Player) || Player->IsActorBeingDestroyed() || Player->GetWorld()!=Press->GetWorld() || !Player->IsLocalController()) return false;
        if (!IsValid(Hero) || Hero->IsActorBeingDestroyed() || !IsValid(Press) || Press->IsActorBeingDestroyed() ||
            !IsValid(Player) || Player->IsActorBeingDestroyed() || Player->GetPawn()!=Hero || Hero->GetController()!=Player || !IsValid(Player->GetLocalPlayer()) ||
            Hero->GetWorld()!=Press->GetWorld() || Player->GetWorld()!=Press->GetWorld() || (Expected && Player!=Expected)) return false;
        const double D=FVector::DistSquared(Hero->GetActorLocation(),Press->GetActorLocation());
        return FMath::IsFinite(D) && FMath::IsFinite(Hero->InteractReach) && Hero->InteractReach>0.f && D<=static_cast<double>(Hero->InteractReach)*Hero->InteractReach;
    }
    FString Wrap(const FString& Text)
    {
        TArray<FString> Lines; Text.ParseIntoArrayLines(Lines,false); FString Out;
        for (int32 I=0;I<Lines.Num();++I)
        {
            if (I) Out+=TEXT("\n"); TArray<FString> Words; Lines[I].ParseIntoArray(Words,TEXT(" "),true); int32 Columns=0;
            for (const auto& Word:Words)
            {
                if (Columns && Columns+1+Word.Len()>40) { Out+=TEXT("\n"); Columns=0; }
                if (Columns) { Out+=TEXT(" "); ++Columns; } Out+=Word; Columns+=Word.Len();
            }
        }
        return Out;
    }
    bool Refuse(FString& Error,const TCHAR* Why) { Error=Why; return false; }
#if PLATFORM_WINDOWS
    class Handle
    {
    public:
        explicit Handle(HANDLE File):Value(File) {}
        ~Handle() { Close(); }
        Handle(const Handle&)=delete; Handle& operator=(const Handle&)=delete;
        bool Valid() const { return Value!=INVALID_HANDLE_VALUE && Value!=nullptr; }
        HANDLE Get() const { return Value; }
        bool Close() { if (!Valid()) return true; const HANDLE Previous=Value; Value=INVALID_HANDLE_VALUE; return ::CloseHandle(Previous)!=0; }
    private:
        HANDLE Value;
    };
#endif
    bool WriteNewVerified(const FString& Id,const std::string& Bytes,FString& Error)
    {
        if (!daedalus::blueprintprint::ValidId(Utf8(Id)) || Bytes.empty() || Bytes.size()>daedalus::blueprintprint::MaxSvgBytes)
            return Refuse(Error,TEXT("The print could not be prepared. Your blueprint is unchanged."));
#if PLATFORM_WINDOWS
        const FString Directory=Folder(),Path=FPaths::Combine(Directory,Filename(Id));
        if (!IFileManager::Get().MakeDirectory(*Directory,true)) return Refuse(Error,TEXT("The print folder could not be prepared. Your blueprint is unchanged."));
        // Reuse the proven fresh-file path from Motif/Portal. UE5.8's active
        // generic writer does not honor NoReplaceExisting; CREATE_NEW does.
        // No failed fresh file is deleted or reused, including partial bytes.
        Handle File(::CreateFileW(*Path,GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr));
        if (!File.Valid()) return Refuse(Error,TEXT("A fresh print could not be created. Earlier files were not changed."));
        DWORD Written=0; const DWORD Size=static_cast<DWORD>(Bytes.size());
        const bool Wrote=::WriteFile(File.Get(),Bytes.data(),Size,&Written,nullptr)!=0 && Written==Size;
        const bool Flushed=Wrote && ::FlushFileBuffers(File.Get())!=0; const bool Closed=File.Close();
        if (!Wrote || !Flushed || !Closed) return Refuse(Error,TEXT("The print could not be completed. Any fresh file is kept for review; your blueprint stays unchanged."));
        Handle Readback(::CreateFileW(*Path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr));
        if (!Readback.Valid()) return Refuse(Error,TEXT("The print could not be confirmed. The new file is kept for review; your blueprint stays unchanged."));
        LARGE_INTEGER Length={};
        if (!::GetFileSizeEx(Readback.Get(),&Length) || Length.QuadPart!=static_cast<LONGLONG>(Bytes.size()))
            return Refuse(Error,TEXT("Print readback length did not match. The new file is kept for review; no earlier print was changed."));
        std::string Back(Bytes.size(),'\0'); DWORD Received=0;
        const bool Read=::ReadFile(Readback.Get(),&Back[0],Size,&Received,nullptr)!=0 && Received==Size;
        const bool ReadClosed=Readback.Close();
        if (!Read || !ReadClosed || Back!=Bytes) return Refuse(Error,TEXT("Exact print readback was not confirmed. The file is kept for review; your blueprint stays unchanged."));
        return true;
#else
        return Refuse(Error,TEXT("Local blueprint printing needs Windows in this edition. Your workshop remains editable."));
#endif
    }
}

ADaedalusBricksBlueprintPress::ADaedalusBricksBlueprintPress()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    PressRoot=CreateDefaultSubobject<USceneComponent>(TEXT("BlueprintPressRoot")); RootComponent=PressRoot;
    Body->SetupAttachment(PressRoot); Glow->SetupAttachment(PressRoot); Glow->SetIntensity(0.f); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeLocation(FVector(0,0,65)); Body->SetRelativeScale3D(FVector(0.7,1.1,1.1)); Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Readout=CreateDefaultSubobject<UTextRenderComponent>(TEXT("BlueprintPressReadout")); Readout->SetupAttachment(PressRoot);
    Readout->SetRelativeLocation(FVector(40,0,260)); Readout->SetWorldSize(11.f); Readout->SetHorizontalAlignment(EHTA_Center);
    Readout->SetVerticalAlignment(EVRTA_TextTop); Readout->SetTextRenderColor(FColor(25,40,60));
}
bool ADaedalusBricksBlueprintPress::Alive() const
{ return IsInGameThread() && !bEnding && !IsActorBeingDestroyed() && HasActorBegunPlay() && GetWorld(); }
bool ADaedalusBricksBlueprintPress::ViewsReady() const
{ return Alive() && IsValid(Readout) && Readout->GetOwner()==this && Readout->IsRegistered() && IsValid(Body) && Body->GetOwner()==this && Body->IsRegistered() && Body->GetStaticMesh(); }
AActor* ADaedalusBricksBlueprintPress::ChosenSource() const
{
    if (SourceKind==EDaedalusBlueprintPrintSource::Bridge) return Bridge.Get();
    if (SourceKind==EDaedalusBlueprintPrintSource::Skyline) return Skyline.Get();
    return nullptr;
}
bool ADaedalusBricksBlueprintPress::SourceReady() const
{
    if (!Alive() || GetWorld()->GetNetMode()!=NM_Standalone) return false;
    const auto* Source=ChosenSource();
    if (!IsValid(Source) || Source->IsActorBeingDestroyed() || Source->GetWorld()!=GetWorld() || !Source->HasActorBegunPlay() ||
        (bFrozen && (SourceKind!=FrozenKind || FrozenSource.Get()!=Source))) return false;
    return SourceKind==EDaedalusBlueprintPrintSource::Bridge?Bridge->IsWorkshopReady():Skyline->IsWorkshopReady();
}
void ADaedalusBricksBlueprintPress::Refresh(const FString& KeptId)
{
    if (!Alive() || bNotifying) return;
    const uint64 StartEpoch=Epoch;
    const auto HeadingKind=bFrozen?FrozenKind:SourceKind;
    FString Text=HeadingKind==EDaedalusBlueprintPrintSource::Bridge?TEXT("BLUEPRINT PRESS / BRIDGE\n"):TEXT("BLUEPRINT PRESS / SKYLINE\n");
    if (!LastFilename.IsEmpty()) Text+=TEXT("LAST VERIFIED PRINT\n")+LastFilename+TEXT("\n");
    Text+=Notice;
    if (IsValid(Readout) && Readout->GetOwner()==this) Readout->SetText(FText::FromString(DaedalusBlueprintPressLocal::Wrap(Text)));
    if (!Alive() || Epoch!=StartEpoch) return;
    TGuardValue<bool> Notification(bNotifying,true); OnViewChanged.Broadcast(this);
    if (!KeptId.IsEmpty() && Alive() && Epoch==StartEpoch) OnPrintKept.Broadcast(this,KeptId); // No state writes after event.
}
void ADaedalusBricksBlueprintPress::BeginPlay()
{
    bEnding=false; ++Epoch; Super::BeginPlay(); if (!Alive()) return;
    Notice=TEXT("Bind one workshop to print its current blueprint. Each E / X keeps a new SVG copy; the live plan stays editable. No print is made on startup.");
    Refresh();
}
FString ADaedalusBricksBlueprintPress::Prompt(const ADaedalusHero*) const
{
    if (!Alive() || !ViewsReady() || GetWorld()->GetNetMode()!=NM_Standalone) return TEXT("Blueprint press is unavailable here");
    if (bFrozen && (!FrozenSource.IsValid() || FrozenSource.Get()!=ChosenSource() || FrozenKind!=SourceKind)) return TEXT("This press keeps one source's print history. Use a new press for another workshop");
    return SourceReady()?TEXT("E / X: Keep a new SVG print of this workshop's current blueprint"):TEXT("Bind a ready workshop to this press first");
}
bool ADaedalusBricksBlueprintPress::Use(ADaedalusHero* Hero)
{
    const uint64 StartEpoch=Epoch;
    if (!Alive() || bBusy || bNotifying || !DaedalusBlueprintPressLocal::LocalReach(Hero,this)) return false;
    if (!Alive() || Epoch!=StartEpoch) return false;
    TGuardValue<bool> Busy(bBusy,true);
    if (!ViewsReady() || !SourceReady()) { Notice=TEXT("The press or its bound workshop is unavailable. Existing prints and the live blueprint are not changed."); Refresh(); return false; }
    const auto Kind=SourceKind; const TWeakObjectPtr<AActor> Source(ChosenSource());
    const TWeakObjectPtr<ADaedalusHero> Performer(Hero); const TWeakObjectPtr<APlayerController> Player(Cast<APlayerController>(Hero->GetController()));
    int32 Rule=-1,Mask=0; daedalus::skyline::Grid Grid{};
    const bool Copied=Kind==EDaedalusBlueprintPrintSource::Bridge?Bridge->CopyBlueprintSnapshot(Rule,Mask):Skyline->CopyBlueprintSnapshot(Rule,Grid);
    const auto ParticipantsReady=[&]()
    {
        return Alive() && Epoch==StartEpoch && ViewsReady() && SourceReady() && SourceKind==Kind && Source.Get()==ChosenSource() &&
            Player.IsValid() && DaedalusBlueprintPressLocal::LocalReach(Performer.Get(),this,Player.Get()) && Alive() && Epoch==StartEpoch &&
            ViewsReady() && SourceReady() && SourceKind==Kind && Source.Get()==ChosenSource();
    };
    if (!Copied || !ParticipantsReady()) { if (Alive()) { Notice=TEXT("The workshop or walker changed before the snapshot was ready. No print was started."); Refresh(); } return false; }
    const FString Id=FGuid::NewGuid().ToString(EGuidFormats::DigitsLower);
    const daedalus::blueprintprint::Identity Identity{DaedalusBlueprintPressLocal::Utf8(Id),LastPrintId}; std::string Bytes;
    const bool Prepared=Kind==EDaedalusBlueprintPrintSource::Bridge?daedalus::blueprintprint::RenderBridgeSvg(Rule,Mask,Identity,Bytes):
        daedalus::blueprintprint::RenderSkylineSvg(Rule,Grid,Identity,Bytes);
    if (!Prepared || !ParticipantsReady()) { if (Alive()) { Notice=TEXT("The frozen blueprint could not be prepared. No print was started; the live plan is unchanged."); Refresh(); } return false; }
    FString Error; const bool Kept=DaedalusBlueprintPressLocal::WriteNewVerified(Id,Bytes,Error);
    // Once writing starts a fresh file may exist even if this actor ends.
    // Never claim that no effect occurred or delete a failed/uncertain print.
    if (!Alive() || Epoch!=StartEpoch) return false;
    if (!Kept) { Notice=Error; Refresh(); return false; }
    LastPrintId=Identity.Id; LastFilename=DaedalusBlueprintPressLocal::Filename(Id); FrozenSource=Source; FrozenKind=Kind; bFrozen=true;
    Notice=SourceReady()?TEXT("New print saved and verified from the frozen model. Find it in Saved/Daedalus/BlueprintPrints. Each file keeps its own rules and snapshot; the live plan stays editable."):
        TEXT("The frozen print was saved and verified. The bound source changed or ended after capture; use a new press for another source. Find this print in Saved/Daedalus/BlueprintPrints.");
    Refresh(Id); return Alive();
}
void ADaedalusBricksBlueprintPress::EndPlay(const EEndPlayReason::Type Reason)
{ bEnding=true; ++Epoch; OnViewChanged.Broadcast(this); Super::EndPlay(Reason); }
