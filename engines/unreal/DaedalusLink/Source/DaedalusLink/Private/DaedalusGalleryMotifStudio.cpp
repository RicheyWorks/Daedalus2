// SPDX-License-Identifier: MIT
#include "DaedalusGalleryMotifStudio.h"
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
#include "HAL/FileManager.h"
#include "Materials/MaterialInterface.h"
#include "Misc/Guid.h"
#include "Misc/Paths.h"
#include "ProceduralMeshComponent.h"
#include "Templates/UnrealTemplate.h"
#include "UObject/ConstructorHelpers.h"
#if PLATFORM_WINDOWS
#include "Windows/WindowsHWrapper.h"
#endif

namespace DaedalusMotifLocal
{
    constexpr int32 ToolCount=86, MaxFiles=128, MaxBytes=512;
    FVector CellCentre(int32 Cell) { return FVector((Cell/8-3.5)*60,-(Cell%8-3.5)*60,0); }
    FVector PaletteCentre(int32 Colour) { return FVector(-210+60*Colour,-300,0); }
    FVector ToolAt(int32 Index)
    {
        if (Index<64) return CellCentre(Index);
        if (Index<76) return FVector(350+130*((Index-64)/4),180-120*((Index-64)%4),65);
        return Index<84?PaletteCentre(Index-76):Index==84?FVector(610,-300,65):FVector(480,-300,65);
    }
    EDaedalusMotifAction ToolAction(int32 Index)
    { return Index<64?EDaedalusMotifAction::Cell:Index<76?static_cast<EDaedalusMotifAction>(Index-63):Index<84?EDaedalusMotifAction::Palette:Index==84?EDaedalusMotifAction::PickInk:EDaedalusMotifAction::Guide; }
    int32 ToolParameter(int32 Index) { return Index<64?Index:Index<84 && Index>=76?Index-76:-1; }
    int32 ToolIndex(EDaedalusMotifAction Action,int32 Parameter)
    { return Action==EDaedalusMotifAction::Cell?Parameter:Action==EDaedalusMotifAction::Palette?76+Parameter:Action==EDaedalusMotifAction::PickInk?84:Action==EDaedalusMotifAction::Guide?85:63+static_cast<int32>(Action); }
    bool ValidAction(EDaedalusMotifAction Action,int32 Cell)
    {
        if (Action==EDaedalusMotifAction::Cell) return Cell>=0 && Cell<64;
        if (Action==EDaedalusMotifAction::Palette) return Cell>=0 && Cell<8;
        return Cell==-1 && static_cast<uint8>(Action)>=1 && static_cast<uint8>(Action)<=static_cast<uint8>(EDaedalusMotifAction::Guide);
    }
    bool LocalReach(const ADaedalusHero* Hero,const AActor* Actor)
    {
        if (!IsInGameThread() || !IsValid(Hero) || Hero->IsActorBeingDestroyed() || !Hero->HasActorBegunPlay() || !IsValid(Actor) ||
            Actor->IsActorBeingDestroyed() || !Actor->HasActorBegunPlay() || Hero->GetWorld()!=Actor->GetWorld() || !Actor->GetWorld() ||
            Actor->GetWorld()->GetNetMode()!=NM_Standalone || !Hero->IsLocallyControlled() || !FMath::IsFinite(Hero->InteractReach) || Hero->InteractReach<=0.f) return false;
        const auto* Controller=Cast<APlayerController>(Hero->GetController());
        if (!IsValid(Controller) || Controller->IsActorBeingDestroyed() || Controller->GetWorld()!=Actor->GetWorld() || !Controller->IsLocalController() ||
            Controller->GetPawn()!=Hero || !IsValid(Controller->GetLocalPlayer())) return false;
        const double D=FVector::DistSquared(Hero->GetActorLocation(),Actor->GetActorLocation());
        return FMath::IsFinite(D) && D<=static_cast<double>(Hero->InteractReach)*Hero->InteractReach;
    }
    FString Wrap(const FString& Text,int32 Width=42,int32 Limit=0)
    {
        TArray<FString> Lines; Text.ParseIntoArrayLines(Lines,false); FString Out;
        for (int32 I=0;I<Lines.Num();++I)
        {
            if (I) Out+=TEXT("\n"); TArray<FString> Words; Lines[I].ParseIntoArray(Words,TEXT(" "),true); int32 Columns=0;
            for (const auto& Word:Words)
            {
                if (Columns && Columns+1+Word.Len()>Width) { Out+=TEXT("\n"); Columns=0; }
                if (Columns) { Out+=TEXT(" "); ++Columns; } Out+=Word; Columns+=Word.Len();
            }
        }
        if (!Limit) return Out;
        Lines.Reset(); Out.ParseIntoArrayLines(Lines,false); Out.Reset();
        for (int32 I=0;I<FMath::Min(Limit,Lines.Num());++I) { if (I) Out+=TEXT("\n"); Out+=Lines[I]; }
        if (Lines.Num()>Limit) Out+=TEXT("..."); return Out;
    }
    std::string Utf8(const FString& Text)
    { const FTCHARToUTF8 Encoded(*Text,Text.Len()); return std::string(Encoded.Get(),static_cast<size_t>(Encoded.Length())); }
    FString Native(const std::string& Text) { return FString(UTF8_TO_TCHAR(Text.c_str())); }
    bool Id(const FString& Value)
    {
        if (Value.Len()!=32) return false;
        for (TCHAR C:Value) if (!((C>=TEXT('0') && C<=TEXT('9')) || (C>=TEXT('a') && C<=TEXT('f')))) return false;
        return !daedalus::motif::CanonicalId(Utf8(Value)).empty();
    }
    FString Folder()
    { return FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("Daedalus"),TEXT("GalleryMotif"),TEXT("Exports"))); }
    FString Path(const FString& Value) { return FPaths::Combine(Folder(),TEXT("Motif_")+Value+TEXT(".dgm")); }
    bool Basename(const FString& Name,FString& Out)
    {
        if (Name.Len()!=42 || !Name.StartsWith(TEXT("Motif_"),ESearchCase::CaseSensitive) || !Name.EndsWith(TEXT(".dgm"),ESearchCase::CaseSensitive)) return false;
        const FString Candidate=Name.Mid(6,32); if (!Id(Candidate)) return false; Out=Candidate; return true;
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
    bool Read(const FString& Value,std::string& Out,FString& Error)
    {
        if (!Id(Value)) return Refuse(Error,TEXT("The chosen sketch has an invalid local ID. Your draft is unchanged."));
#if PLATFORM_WINDOWS
        Handle File(::CreateFileW(*Path(Value),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr));
        if (!File.Valid()) return Refuse(Error,TEXT("The chosen sketch could not be read. Your draft is unchanged."));
        LARGE_INTEGER Length={};
        if (!::GetFileSizeEx(File.Get(),&Length) || Length.QuadPart<1 || Length.QuadPart>MaxBytes)
            return Refuse(Error,TEXT("The chosen file is empty or too large. Its bytes and your draft are kept."));
        std::string Candidate(static_cast<size_t>(Length.QuadPart),'\0'); DWORD Received=0;
        if (!::ReadFile(File.Get(),&Candidate[0],static_cast<DWORD>(Candidate.size()),&Received,nullptr) || Received!=Candidate.size() || !File.Close())
            return Refuse(Error,TEXT("The chosen sketch could not be completely read. Your draft is unchanged."));
        Out=Candidate; return true;
#else
        return Refuse(Error,TEXT("Local sketch files need Windows in this edition. The canvas and Undo still work."));
#endif
    }
    bool WriteVerified(const FString& Value,const std::string& Bytes,FString& Error)
    {
        if (!Id(Value) || Bytes.empty() || Bytes.size()>MaxBytes) return Refuse(Error,TEXT("This sketch could not be prepared for export. Your draft is unchanged."));
#if PLATFORM_WINDOWS
        if (!IFileManager::Get().MakeDirectory(*Folder(),true)) return Refuse(Error,TEXT("The export folder could not be prepared. Your draft is unchanged."));
        // UE5.8 FileManagerGeneric.cpp:95-127 ignores NoReplaceExisting;
        // WindowsPlatformFile.cpp:1644 reaches CREATE_ALWAYS. Use CREATE_NEW
        // directly, as the existing Portal save helper does for fresh files.
        // Never delete a failed fresh export: even partial bytes are preserved.
        Handle File(::CreateFileW(*Path(Value),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr));
        if (!File.Valid()) return Refuse(Error,TEXT("A fresh export could not be created. Existing files and your draft are unchanged."));
        DWORD Written=0;
        const bool Wrote=::WriteFile(File.Get(),Bytes.data(),static_cast<DWORD>(Bytes.size()),&Written,nullptr)!=0 && Written==Bytes.size();
        const bool Flushed=Wrote && ::FlushFileBuffers(File.Get())!=0; const bool Closed=File.Close();
        if (!Wrote || !Flushed || !Closed) return Refuse(Error,TEXT("Export could not be completed. The fresh file is kept; your draft stays. Try Export again for a new file."));
        std::string Back;
        if (!Read(Value,Back,Error) || Back!=Bytes) return Refuse(Error,TEXT("Export readback could not be confirmed. The file is kept; your draft stays. Try Export again."));
        return true;
#else
        return Refuse(Error,TEXT("Local sketch files need Windows in this edition. The canvas and Undo still work."));
#endif
    }
    bool List(TArray<FString>& Out,FString& Error)
    {
#if PLATFORM_WINDOWS
        if (!IFileManager::Get().DirectoryExists(*Folder())) { Out.Reset(); return true; }
        TArray<FString> Candidates; int32 Examined=0; bool Overflow=false;
        const bool Complete=IFileManager::Get().IterateDirectory(*Folder(),[&](const TCHAR* Filename,bool Directory)
        {
            if (++Examined>MaxFiles) { Overflow=true; return false; }
            if (!Directory)
            {
                FString Value;
                if (Basename(FPaths::GetCleanFilename(Filename),Value)) Candidates.Add(Value);
            }
            return true;
        });
        if (Overflow) return Refuse(Error,TEXT("This folder has more than 128 entries, so browsing stopped. No files or drafts changed."));
        if (!Complete) return Refuse(Error,TEXT("Saved sketches could not be completely listed. Your selection and draft are unchanged."));
        Candidates.Sort(); Out=MoveTemp(Candidates); return true;
#else
        return Refuse(Error,TEXT("Local sketch files need Windows in this edition. The canvas and Undo still work."));
#endif
    }
    FLinearColor Colour(int32 Index)
    {
        static const FLinearColor Colours[]={FLinearColor(0.95f,0.93f,0.85f),FLinearColor(0.035f,0.055f,0.08f),FLinearColor(0.95f,0.22f,0.18f),
            FLinearColor(1.f,0.72f,0.03f),FLinearColor(0.07f,0.58f,0.23f),FLinearColor(0.04f,0.36f,0.92f),FLinearColor(0.48f,0.19f,0.78f),FLinearColor(0.02f,0.65f,0.64f)};
        return Index>=0 && Index<8?Colours[Index]:Colours[0];
    }
    struct Ink
    {
        TArray<FVector> Vertices; TArray<int32> Triangles; TArray<FLinearColor> Colours;
        void Quad(FVector A,FVector B,FVector C,FVector D,FLinearColor Colour)
        { const int32 At=Vertices.Num(); Vertices.Append({A,B,C,D}); Triangles.Append({At,At+1,At+2,At,At+2,At+3}); Colours.Append({Colour,Colour,Colour,Colour}); }
        void Tile(FVector Centre,double Radius,FLinearColor Colour)
        { Quad(Centre+FVector(-Radius,-Radius,0),Centre+FVector(Radius,-Radius,0),Centre+FVector(Radius,Radius,0),Centre+FVector(-Radius,Radius,0),Colour); }
        void Line(FVector A,FVector B,double Width,FLinearColor Colour)
        {
            const FVector Direction=(B-A).GetSafeNormal(), Side(-Direction.Y*Width,Direction.X*Width,0);
            Quad(A-Side,B-Side,B+Side,A+Side,Colour);
        }
        void Outline(FVector At,double Radius,FLinearColor Colour)
        {
            const FVector X(Radius,0,0),Y(0,Radius,0);
            Line(At-X-Y,At+X-Y,1,Colour); Line(At+X-Y,At+X+Y,1,Colour); Line(At+X+Y,At-X+Y,1,Colour); Line(At-X+Y,At-X-Y,1,Colour);
        }
    };
}

namespace DaedalusMotifNative
{
    bool ReadLocalExport(const FString& Id,daedalus::motif::Document& Out,std::string& Bytes,FString& Error)
    {
        std::string Raw; daedalus::motif::Document Prepared;
        if (!DaedalusMotifLocal::Read(Id,Raw,Error)) return false;
        if (!daedalus::motif::DecodeDocument(Raw,Prepared) || Prepared.Id!=DaedalusMotifLocal::Utf8(Id))
            return DaedalusMotifLocal::Refuse(Error,TEXT("The chosen file does not match this sketch format and ID. Its bytes and your draft are kept."));
        Out=Prepared; Bytes=Raw; return true;
    }
    FLinearColor PaletteColour(int32 Index) { return DaedalusMotifLocal::Colour(Index); }
}

ADaedalusGalleryMotifStudio::ADaedalusGalleryMotifStudio()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    StudioRoot=CreateDefaultSubobject<USceneComponent>(TEXT("MotifStudioRoot")); RootComponent=StudioRoot;
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Engine/EngineDebugMaterials/VertexColorMaterial.VertexColorMaterial")); InkMaterial=Material.Object;
    Canvas=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("MotifFloorCanvas")); Canvas->SetupAttachment(StudioRoot);
    Canvas->SetCollisionEnabled(ECollisionEnabled::NoCollision); Canvas->SetCastShadow(false);
    Preview=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("ChosenMotifPreview")); Preview->SetupAttachment(StudioRoot);
    Preview->SetRelativeLocation(FVector(650,270,90)); Preview->SetCollisionEnabled(ECollisionEnabled::NoCollision); Preview->SetCastShadow(false);
    Readout=CreateDefaultSubobject<UTextRenderComponent>(TEXT("MotifStudioReadout")); Readout->SetupAttachment(StudioRoot);
    Readout->SetRelativeLocation(FVector(285,0,340)); Readout->SetWorldSize(12.f); Readout->SetHorizontalAlignment(EHTA_Center);
    Readout->SetVerticalAlignment(EVRTA_TextTop); Readout->SetTextRenderColor(FColor(25,40,60));
    auto* Title=CreateDefaultSubobject<UTextRenderComponent>(TEXT("MotifStudioTitle")); Title->SetupAttachment(StudioRoot);
    Title->SetRelativeLocation(FVector(285,0,410)); Title->SetWorldSize(26.f); Title->SetHorizontalAlignment(EHTA_Center);
    Title->SetTextRenderColor(FColor(25,40,60)); Title->SetText(FText::FromString(TEXT("MOTIF STUDIO")));
    auto* Caption=CreateDefaultSubobject<UTextRenderComponent>(TEXT("MotifPreviewCaption")); Caption->SetupAttachment(StudioRoot);
    Caption->SetRelativeLocation(FVector(650,270,190)); Caption->SetWorldSize(13.f); Caption->SetHorizontalAlignment(EHTA_Center);
    Caption->SetRelativeRotation(FRotator(0,180,0));
    Caption->SetTextRenderColor(FColor(25,40,60)); Caption->SetText(FText::FromString(TEXT("CHOSEN SKETCH\nPreview / confirm Load to use")));
}

bool ADaedalusGalleryMotifStudio::IsStudioAlive() const
{ return IsInGameThread() && !bEnding && !IsActorBeingDestroyed() && HasActorBegunPlay() && GetWorld(); }
bool ADaedalusGalleryMotifStudio::CopyLastKeptSketchId(FString& Out) const
{
    if (!IsStudioAlive() || !Draft.Active()) return false;
    const auto Id=daedalus::motif::CanonicalId(LineageId); if (Id.empty()) return false;
    Out=DaedalusMotifLocal::Native(Id); return true;
}
bool ADaedalusGalleryMotifStudio::ViewsReady() const
{
    return IsStudioAlive() && IsValid(Canvas) && Canvas->GetOwner()==this && Canvas->IsRegistered() &&
        IsValid(Preview) && Preview->GetOwner()==this && Preview->IsRegistered() && IsValid(Readout) && Readout->GetOwner()==this && Readout->IsRegistered() && InkMaterial;
}
bool ADaedalusGalleryMotifStudio::ToolsReady() const
{
    if (!IsStudioAlive() || OwnedTools.Num()!=DaedalusMotifLocal::ToolCount) return false;
    for (int32 I=0;I<OwnedTools.Num();++I)
    {
        const auto* Tool=OwnedTools[I].Get();
        if (!IsValid(Tool) || Tool->IsActorBeingDestroyed() || !Tool->HasActorBegunPlay() || Tool->GetOwner()!=this || Tool->GetWorld()!=GetWorld() ||
            Tool->GetActorEnableCollision() || !Tool->Matches(this,DaedalusMotifLocal::ToolAction(I),DaedalusMotifLocal::ToolParameter(I)) ||
            !Tool->GetActorTransform().Equals(FTransform(DaedalusMotifLocal::ToolAt(I))*GetActorTransform(),0.01)) return false;
    }
    return true;
}
bool ADaedalusGalleryMotifStudio::HasGuideReference() const
{ return !LineageId.empty() && daedalus::motif::CanonicalId(LineageId)==LineageId && daedalus::motif::ValidImage(Baseline); }
void ADaedalusGalleryMotifStudio::DrawCanvas()
{
    if (!ViewsReady() || !Draft.Active()) return;
    DaedalusMotifLocal::Ink Main; Main.Tile(FVector(0,0,1),247,FLinearColor(0.08f,0.13f,0.18f));
    for (int32 Cell=0;Cell<64;++Cell) Main.Tile(DaedalusMotifLocal::CellCentre(Cell)+FVector(0,0,3),29,DaedalusMotifLocal::Colour(Draft.Canvas()[Cell]));
    if (GuideMode && HasGuideReference())
        for (int32 Cell=0;Cell<64;++Cell)
        {
            const FVector At=DaedalusMotifLocal::CellCentre(Cell)+FVector(0,0,3.4);
            if (GuideMode==1 && Baseline[Cell]!=0)
            {
                // Hollow inset marks leave the actual ink/Paper tile visible.
                // No transparent material, sampled ghost ink or canvas write.
                Main.Outline(At,13,FLinearColor(0.08f,0.13f,0.18f));
                Main.Outline(At+FVector(0,0,0.1),10,DaedalusMotifLocal::Colour(Baseline[Cell]));
            }
            else if (GuideMode==2 && Draft.Canvas()[Cell]!=Baseline[Cell])
            {
                Main.Outline(At,19,FLinearColor(0.08f,0.13f,0.18f));
                Main.Outline(At+FVector(0,0,0.1),16,FLinearColor(1.f,0.7f,0.1f));
            }
        }
    for (int32 Colour=0;Colour<8;++Colour)
    {
        const FVector At=DaedalusMotifLocal::PaletteCentre(Colour)+FVector(0,0,3); Main.Tile(At,24,DaedalusMotifLocal::Colour(Colour));
        if (Colour==Ink) { Main.Outline(At+FVector(0,0,0.5),26,FLinearColor::White); Main.Outline(At+FVector(0,0,0.7),22,FLinearColor::Black); }
    }
    daedalus::motif::Selection Targets;
    if (bPicking)
    { if (SelectedCell>=0 && SelectedCell<64) { Targets.Cells[SelectedCell]=true; Targets.Count=1; } }
    else if (bFill) daedalus::motif::FillTargetsFor(Draft.Canvas(),SelectedCell,Mode,Targets);
    else
    {
        daedalus::motif::Orbit Orbit;
        if (daedalus::motif::OrbitFor(SelectedCell,Mode,Orbit))
            for (size_t I=0;I<Orbit.Count;++I) { Targets.Cells[Orbit.Cells[I]]=true; ++Targets.Count; }
    }
    for (int32 Cell=0;Cell<64;++Cell)
        if (Targets.Cells[Cell])
        {
            const FVector At=DaedalusMotifLocal::CellCentre(Cell)+FVector(0,0,4);
            Main.Outline(At,27,FLinearColor::White); Main.Outline(At+FVector(0,0,0.2),25,FLinearColor::Black);
        }
    TArray<FVector> Normals; Normals.Init(FVector::UpVector,Main.Vertices.Num()); TArray<FVector2D> UV; UV.Init(FVector2D::ZeroVector,Main.Vertices.Num()); TArray<FProcMeshTangent> Tangents;
    Canvas->CreateMeshSection_LinearColor(0,Main.Vertices,Main.Triangles,Normals,UV,Main.Colours,Tangents,false);
    if (!ViewsReady()) return; Canvas->SetMaterial(0,InkMaterial);
    if (!ViewsReady()) return;
    DaedalusMotifLocal::Ink Small; Small.Tile(FVector::ZeroVector,43,FLinearColor(0.08f,0.13f,0.18f));
    if (bHasChosen)
        for (int32 Cell=0;Cell<64;++Cell) Small.Tile(FVector((Cell/8-3.5)*10,-(Cell%8-3.5)*10,0.5),4.7,DaedalusMotifLocal::Colour(Chosen.Pixels[Cell]));
    Normals.Init(FVector::UpVector,Small.Vertices.Num()); UV.Init(FVector2D::ZeroVector,Small.Vertices.Num());
    Preview->CreateMeshSection_LinearColor(0,Small.Vertices,Small.Triangles,Normals,UV,Small.Colours,Tangents,false);
    if (ViewsReady()) Preview->SetMaterial(0,InkMaterial);
}
void ADaedalusGalleryMotifStudio::Refresh()
{
    if (!IsStudioAlive() || bNotifying) return;
    FString State=IsDirty()?TEXT("DRAFT CHANGED / EXPORT TO KEEP"):!LineageId.empty()?TEXT("DRAFT MATCHES KEPT SKETCH"):TEXT("BLANK DRAFT / EXPORT TO KEEP");
    FString Text=State+FString::Printf(TEXT("\nInk: %s   /   %s\nBrush: %s   /   Undo %u   Redo %u\nChosen: %s\n"),UTF8_TO_TCHAR(daedalus::motif::ColourName(Ink)),
        UTF8_TO_TCHAR(daedalus::motif::SymmetryName(Mode)),bPicking?TEXT("Pick ink / one square"):bFill?TEXT("Area fill"):TEXT("Point"),static_cast<unsigned>(Draft.UndoCount()),static_cast<unsigned>(Draft.RedoCount()),bHasChosen?*ChosenId.Left(8):TEXT("none / use Next sketch"));
    if (GuideMode && HasGuideReference())
        Text+=FString::Printf(TEXT("Guide: %s / kept-loaded %s\nInset marks are not paint.\n"),GuideMode==1?TEXT("Kept Ghost"):TEXT("Changes"),*DaedalusMotifLocal::Native(LineageId).Left(8));
    Text+=Notice;
    if (ViewsReady()) DrawCanvas();
    if (!IsStudioAlive()) return;
    if (IsValid(Readout) && Readout->GetOwner()==this) Readout->SetText(FText::FromString(DaedalusMotifLocal::Wrap(Text)));
    if (!IsStudioAlive()) return;
    TGuardValue<bool> Notification(bNotifying,true); OnViewChanged.Broadcast(this);
}
bool ADaedalusGalleryMotifStudio::ExportPrepared(const daedalus::motif::Image& Pixels,const std::string& Parent,std::string& ExportedId,FString& Error) const
{
    const FString Fresh=FGuid::NewGuid().ToString(EGuidFormats::DigitsLower);
    const daedalus::motif::Document Prepared{DaedalusMotifLocal::Utf8(Fresh),Parent,Pixels};
    const std::string Bytes=daedalus::motif::EncodeDocument(Prepared); daedalus::motif::Document Checked;
    if (Bytes.empty() || !daedalus::motif::DecodeDocument(Bytes,Checked) || Checked.Id!=Prepared.Id || Checked.Parent!=Prepared.Parent || Checked.Pixels!=Pixels)
    { Error=TEXT("This draft could not be prepared for export. Nothing changed."); return false; }
    if (!DaedalusMotifLocal::WriteVerified(Fresh,Bytes,Error)) return false;
    ExportedId=Prepared.Id; return true;
}
bool ADaedalusGalleryMotifStudio::ReadChosen(daedalus::motif::Document& Out,std::string& Bytes,FString& Error) const
{
    if (!bHasChosen || !DaedalusMotifLocal::Id(ChosenId)) { Error=TEXT("Choose a saved sketch with Next sketch first. Your draft is unchanged."); return false; }
    return DaedalusMotifNative::ReadLocalExport(ChosenId,Out,Bytes,Error);
}
bool ADaedalusGalleryMotifStudio::NextSketch()
{
    const uint64 StartEpoch=Epoch; TArray<FString> Values; FString Error;
    if (!DaedalusMotifLocal::List(Values,Error)) { if (IsStudioAlive()) Notice=Error; return false; }
    if (!IsStudioAlive() || Epoch!=StartEpoch) return false;
    if (Values.IsEmpty()) { Notice=TEXT("No local sketches were found. Export your draft to keep the first one."); return false; }
    int32 Start=Values.IndexOfByKey(ChosenId); Start=Start==INDEX_NONE?0:(Start+1)%Values.Num();
    for (int32 Offset=0;Offset<Values.Num();++Offset)
    {
        const FString Value=Values[(Start+Offset)%Values.Num()]; std::string Bytes; daedalus::motif::Document Prepared;
        if (!DaedalusMotifLocal::Read(Value,Bytes,Error) || !daedalus::motif::DecodeDocument(Bytes,Prepared) || Prepared.Id!=DaedalusMotifLocal::Utf8(Value)) continue;
        if (!IsStudioAlive() || Epoch!=StartEpoch) return false;
        ChosenId=Value; Chosen=Prepared; ChosenBytes=Bytes; bHasChosen=true;
        Notice=TEXT("Chosen sketch preview updated. The floor draft did not change. Save + Load requires confirmation."); return true;
    }
    if (IsStudioAlive()) Notice=TEXT("No readable matching sketches were found. Existing files, preview and draft are unchanged."); return false;
}

bool ADaedalusGalleryMotifStudio::SaveAndLoad()
{
    const uint64 StartEpoch=Epoch; FString Error; std::string Bytes; daedalus::motif::Document Prepared;
    if (!ReadChosen(Prepared,Bytes,Error)) { if (IsStudioAlive()) { ArmedAction=EDaedalusMotifAction::Cell; Notice=Error; } return false; }
    if (!IsStudioAlive() || Epoch!=StartEpoch) return false;
    if (Bytes!=ChosenBytes || Prepared.Id!=Chosen.Id || Prepared.Parent!=Chosen.Parent || Prepared.Pixels!=Chosen.Pixels)
    {
        Chosen=Prepared; ChosenBytes=Bytes; ArmedAction=EDaedalusMotifAction::Cell;
        Notice=TEXT("The chosen file changed. Its preview was refreshed; loading was cancelled. Review it before confirming again."); return false;
    }
    if (ArmedAction!=EDaedalusMotifAction::SaveLoad || ArmedId!=ChosenId || ArmedBytes!=Bytes)
    {
        ArmedAction=EDaedalusMotifAction::SaveLoad; ArmedId=ChosenId; ArmedBytes=Bytes;
        Notice=TEXT("Confirm Save + Load to use this preview. A changed draft is exported first; old files are never replaced. Any other tool cancels."); return false;
    }
    auto Candidate=Draft;
    if (Candidate.Canvas()!=Prepared.Pixels && !Candidate.Replace(Prepared.Pixels))
    { ArmedAction=EDaedalusMotifAction::Cell; Notice=TEXT("The chosen pattern could not be prepared. Your draft is unchanged."); return false; }
    std::string KeptId;
    if (IsDirty() && !ExportPrepared(Draft.Canvas(),LineageId,KeptId,Error))
    { if (IsStudioAlive()) { ArmedAction=EDaedalusMotifAction::Cell; Notice=Error; } return false; }
    if (!IsStudioAlive() || Epoch!=StartEpoch) return false;
    // Verify the exact previewed source again after preservation, before commit.
    daedalus::motif::Document Again; std::string AgainBytes;
    if (!ReadChosen(Again,AgainBytes,Error))
    { if (IsStudioAlive()) { ArmedAction=EDaedalusMotifAction::Cell; Notice=TEXT("The chosen sketch became unavailable. Loading stopped; your draft and any fresh export are kept."); } return false; }
    if (!IsStudioAlive() || Epoch!=StartEpoch) return false;
    if (AgainBytes!=Bytes || Again.Id!=Prepared.Id || Again.Parent!=Prepared.Parent || Again.Pixels!=Prepared.Pixels)
    {
        Chosen=Again; ChosenBytes=AgainBytes; ArmedAction=EDaedalusMotifAction::Cell;
        Notice=TEXT("The chosen file changed during preservation. Preview refreshed; loading cancelled. Draft, history and earlier files are kept."); return false;
    }
    if (!bAvailable || !ViewsReady() || !ToolsReady())
    { ArmedAction=EDaedalusMotifAction::Cell; Notice=TEXT("The studio changed before loading. Your draft and any fresh export are kept."); return false; }
    Draft=Candidate; Baseline=Prepared.Pixels; LineageId=Prepared.Id; SelectedCell=-1; ArmedAction=EDaedalusMotifAction::Cell;
    Notice=KeptId.empty()?TEXT("Chosen sketch loaded. Existing files are unchanged; Undo can return to the previous drawing."):
        TEXT("Previous draft exported and verified, then chosen sketch loaded. Old files stay; Undo can return to the previous drawing.");
    return true;
}
bool ADaedalusGalleryMotifStudio::SaveAndClear()
{
    if (ArmedAction!=EDaedalusMotifAction::SaveClear)
    {
        ArmedAction=EDaedalusMotifAction::SaveClear;
        Notice=TEXT("Confirm Save + Clear for a blank draft. A changed draft is exported first. Earlier files stay; any other tool cancels."); return false;
    }
    const uint64 StartEpoch=Epoch; const auto PreservedPixels=Draft.Canvas(); auto Candidate=Draft; Candidate.Clear();
    const bool Dirty=IsDirty(); std::string KeptId; FString Error;
    if (Dirty && !ExportPrepared(PreservedPixels,LineageId,KeptId,Error))
    { if (IsStudioAlive()) { ArmedAction=EDaedalusMotifAction::Cell; Notice=Error; } return false; }
    if (!IsStudioAlive() || Epoch!=StartEpoch) return false;
    if (!bAvailable || !ViewsReady() || !ToolsReady())
    { ArmedAction=EDaedalusMotifAction::Cell; Notice=TEXT("The studio changed before clearing. Your draft and any fresh export are kept."); return false; }
    Draft=Candidate;
    if (Dirty) { Baseline=PreservedPixels; LineageId=KeptId; }
    SelectedCell=-1; ArmedAction=EDaedalusMotifAction::Cell;
    Notice=Dirty?TEXT("Previous draft exported and verified. The new draft is blank; Undo can restore the drawing. Export to keep new work."):
        TEXT("A blank draft is ready. Earlier exported files stay unchanged; Undo can restore the previous drawing.");
    return true;
}

FString ADaedalusGalleryMotifStudio::ToolPrompt(EDaedalusMotifAction Action,int32 Cell) const
{
    if (!IsStudioAlive() || !Draft.Active() || GetWorld()->GetNetMode()!=NM_Standalone || !DaedalusMotifLocal::ValidAction(Action,Cell)) return TEXT("Motif tool is unavailable");
    if (Action==EDaedalusMotifAction::Export) return TEXT("E / X: Export a new local .dgm sketch; existing files are never replaced");
    if (!bAvailable || !ViewsReady() || !ToolsReady()) return TEXT("Studio tools are unavailable. Export can still keep the draft");
    if (Action==EDaedalusMotifAction::Cell)
    {
        if (bPicking) return FString::Printf(TEXT("E / X: Pick %s from row %d col %d, then resume %s. No pixels or drawing-history entries change."),
            UTF8_TO_TCHAR(daedalus::motif::ColourName(Draft.Canvas()[Cell])),Cell/8+1,Cell%8+1,bFill?TEXT("Area fill"):TEXT("Point"));
        if (bFill)
        {
            daedalus::motif::Selection Targets; daedalus::motif::FillTargetsFor(Draft.Canvas(),Cell,Mode,Targets);
            return FString::Printf(TEXT("E / X: Fill matching area at row %d col %d and its symmetry copies: %u squares / %s. Undo restores one fill."),Cell/8+1,Cell%8+1,
                static_cast<unsigned>(Targets.Count),UTF8_TO_TCHAR(daedalus::motif::ColourName(Ink)));
        }
        daedalus::motif::Orbit Orbit; daedalus::motif::OrbitFor(Cell,Mode,Orbit);
        return FString::Printf(TEXT("E / X: Row %d col %d (%s). Paint %s on %u squares / %s"),Cell/8+1,Cell%8+1,
            UTF8_TO_TCHAR(daedalus::motif::ColourName(Draft.Canvas()[Cell])),UTF8_TO_TCHAR(daedalus::motif::ColourName(Ink)),static_cast<unsigned>(Orbit.Count),UTF8_TO_TCHAR(daedalus::motif::SymmetryName(Mode)));
    }
    if (Action==EDaedalusMotifAction::Colour) return TEXT("E / X: Next ink colour; Paper / erase removes ink");
    if (Action==EDaedalusMotifAction::Palette) return FString::Printf(TEXT("E / X: Choose palette %d / %s. No drawing edit."),Cell+1,UTF8_TO_TCHAR(daedalus::motif::ColourName(Cell)));
    if (Action==EDaedalusMotifAction::PickInk) return bPicking?TEXT("E / X: Cancel picking and resume the previous brush"):TEXT("E / X: Pick ink from one floor-draft square, then resume Point / Area fill");
    if (Action==EDaedalusMotifAction::Guide) return HasGuideReference()?TEXT("E / X: Guide Off / Kept Ghost / Changes. Inset reference marks are not paint; Pick and Fill read the actual draft"):TEXT("E / X: Keep or load a sketch before using the reference guide; the drawing stays unchanged");
    if (Action==EDaedalusMotifAction::Symmetry) return TEXT("E / X: Next symmetry; palette and symmetry do not change drawing history");
    if (Action==EDaedalusMotifAction::Brush) return TEXT("E / X: Switch Point / Area fill. Fill uses touching same-colour squares and their symmetry copies; diagonal corners stay separate");
    if (Action==EDaedalusMotifAction::Rotate) return TEXT("E / X: Rotate the whole draft clockwise 90 degrees; Undo restores it. Kept exports stay unchanged");
    if (Action==EDaedalusMotifAction::FlipColumns) return TEXT("E / X: Flip the whole draft left / right; Undo restores it. Kept exports stay unchanged");
    if (Action==EDaedalusMotifAction::FlipRows) return TEXT("E / X: Flip the whole draft near / far; Undo restores it. Kept exports stay unchanged");
    if (Action==EDaedalusMotifAction::Undo) return TEXT("E / X: Undo one drawing edit (latest 64 kept)");
    if (Action==EDaedalusMotifAction::Redo) return TEXT("E / X: Redo one undone drawing edit");
    if (Action==EDaedalusMotifAction::NextSketch) return TEXT("E / X: Browse the next local sketch; preview only, floor draft unchanged");
    if (Action==EDaedalusMotifAction::SaveLoad) return ArmedAction==Action?TEXT("E / X: Confirm Save + Load; preserve changed draft first"):TEXT("E / X: Save changed draft, then load chosen preview - confirm twice");
    return ArmedAction==Action?TEXT("E / X: Confirm Save + Clear; preserve changed draft first"):TEXT("E / X: Save changed draft, then clear - confirm twice");
}
FString ADaedalusGalleryMotifStudio::ToolLabel(EDaedalusMotifAction Action,int32 Cell) const
{
    if (!IsStudioAlive() || !Draft.Active()) return TEXT("--");
    FString Text;
    if (Action==EDaedalusMotifAction::Cell)
    {
        if (Cell!=SelectedCell || Cell<0 || Cell>=64) return FString();
        Text=FString::Printf(TEXT("R%d C%d / %s"),Cell/8+1,Cell%8+1,UTF8_TO_TCHAR(daedalus::motif::ColourName(Draft.Canvas()[Cell])));
    }
    else if (Action==EDaedalusMotifAction::Colour) Text=TEXT("Next colour\n")+FString(UTF8_TO_TCHAR(daedalus::motif::ColourName(Ink)));
    else if (Action==EDaedalusMotifAction::Palette) Text=FString::FromInt(Cell+1)+(Cell==Ink?TEXT(" *"):TEXT(""));
    else if (Action==EDaedalusMotifAction::PickInk) Text=bPicking?TEXT("Pick ink armed\nChoose one square"):TEXT("Pick ink\nFrom floor draft");
    else if (Action==EDaedalusMotifAction::Guide) Text=GuideMode==1?TEXT("Guide: KEPT GHOST\nInset marks only"):GuideMode==2?TEXT("Guide: CHANGES\nDifferent squares"):TEXT("Guide: OFF\nKept / loaded image");
    else if (Action==EDaedalusMotifAction::Symmetry) Text=TEXT("Next symmetry\n")+FString(UTF8_TO_TCHAR(daedalus::motif::SymmetryName(Mode)));
    else if (Action==EDaedalusMotifAction::Undo) Text=FString::Printf(TEXT("Undo / %u"),static_cast<unsigned>(Draft.UndoCount()));
    else if (Action==EDaedalusMotifAction::Redo) Text=FString::Printf(TEXT("Redo / %u"),static_cast<unsigned>(Draft.RedoCount()));
    else if (Action==EDaedalusMotifAction::Export) Text=TEXT("Export to keep");
    else if (Action==EDaedalusMotifAction::NextSketch) Text=TEXT("Next sketch\nPreview only");
    else if (Action==EDaedalusMotifAction::SaveLoad) Text=ArmedAction==Action?TEXT("Confirm Save + Load"):TEXT("Save + Load chosen");
    else if (Action==EDaedalusMotifAction::SaveClear) Text=ArmedAction==Action?TEXT("Confirm Save + Clear"):TEXT("Save + Clear");
    else if (Action==EDaedalusMotifAction::Brush) Text=bFill?TEXT("Brush: Area fill\nSwitch to Point"):TEXT("Brush: Point\nSwitch to Area fill");
    else if (Action==EDaedalusMotifAction::Rotate) Text=TEXT("Rotate picture\nClockwise 90");
    else if (Action==EDaedalusMotifAction::FlipColumns) Text=TEXT("Flip picture\nLeft / right");
    else if (Action==EDaedalusMotifAction::FlipRows) Text=TEXT("Flip picture\nNear / far");
    // Palette chips keep a compact floor label; full feedback remains on the
    // readout/prompt instead of spilling a paragraph across neighbouring chips.
    if (Action!=EDaedalusMotifAction::Palette && bFeedback && Action==FeedbackAction && Cell==FeedbackCell) Text+=TEXT("\n")+DaedalusMotifLocal::Wrap(Notice,36,3);
    return Text;
}
bool ADaedalusGalleryMotifStudio::Operate(ADaedalusHero* Hero,const AActor* Tool,EDaedalusMotifAction Action,int32 Cell)
{
    if (!IsStudioAlive() || bBusy || bNotifying || !Draft.Active() || GetWorld()->GetNetMode()!=NM_Standalone ||
        !DaedalusMotifLocal::ValidAction(Action,Cell) || !DaedalusMotifLocal::LocalReach(Hero,Tool)) return false;
    const auto* Bound=Cast<ADaedalusMotifTool>(Tool);
    const int32 Slot=DaedalusMotifLocal::ToolIndex(Action,Cell);
    if (!Bound || !OwnedTools.IsValidIndex(Slot) || OwnedTools[Slot].Get()!=Bound || Bound->GetOwner()!=this ||
        !Bound->Matches(this,Action,Cell) || !Bound->GetActorTransform().Equals(FTransform(DaedalusMotifLocal::ToolAt(Slot))*GetActorTransform(),0.01) || !IsStudioAlive()) return false;
    TGuardValue<bool> Busy(bBusy,true); bFeedback=true; FeedbackAction=Action; FeedbackCell=Cell;
    if (Action!=ArmedAction) { ArmedAction=EDaedalusMotifAction::Cell; ArmedId.Reset(); ArmedBytes.clear(); }
    if (Action!=EDaedalusMotifAction::Cell && Action!=EDaedalusMotifAction::PickInk && Action!=EDaedalusMotifAction::Guide) bPicking=false;
    if (Action!=EDaedalusMotifAction::Export && (!bAvailable || !ViewsReady() || !ToolsReady()))
    { bAvailable=false; Notice=TEXT("Some studio tools or views are unavailable. The draft is kept; Export can still preserve it."); Refresh(); return false; }
    bool Changed=false;
    if (Action==EDaedalusMotifAction::Cell)
    {
        SelectedCell=Cell; size_t Count=0;
        if (bPicking)
        {
            Ink=Draft.Canvas()[Cell]; bPicking=false; Changed=true;
            Notice=FString::Printf(TEXT("Picked %s. %s resumes. The picture, Undo and Redo are unchanged."),UTF8_TO_TCHAR(daedalus::motif::ColourName(Ink)),bFill?TEXT("Area fill"):TEXT("Point"));
        }
        else
        {
            if (bFill)
            {
                daedalus::motif::Selection Targets; daedalus::motif::FillTargetsFor(Draft.Canvas(),Cell,Mode,Targets); Count=Targets.Count;
                Changed=Draft.Fill(Cell,Ink,Mode);
            }
            else
            {
                daedalus::motif::Orbit Orbit; daedalus::motif::OrbitFor(Cell,Mode,Orbit); Count=Orbit.Count;
                Changed=Draft.Paint(Cell,Ink,Mode);
            }
            Notice=Changed?FString::Printf(TEXT("%s %u target squares with %s in one edit. Undo restores it; Export to keep."),bFill?TEXT("Filled"):TEXT("Painted"),static_cast<unsigned>(Count),UTF8_TO_TCHAR(daedalus::motif::ColourName(Ink))):
                TEXT("Those squares already have this ink. No drawing edit was added; Redo is kept.");
        }
    }
    else if (Action==EDaedalusMotifAction::Colour)
    { Ink=(Ink+1)%daedalus::motif::PaletteCount; Notice=TEXT("Ink changed. Palette choices do not use Undo; use E / X on a square with the chosen brush."); Changed=true; }
    else if (Action==EDaedalusMotifAction::Palette)
    { Ink=Cell; Notice=FString::Printf(TEXT("Palette %d: %s. Point / Area fill resumes with this ink; the drawing and history are unchanged."),Cell+1,UTF8_TO_TCHAR(daedalus::motif::ColourName(Ink))); Changed=true; }
    else if (Action==EDaedalusMotifAction::PickInk)
    { bPicking=!bPicking; Notice=bPicking?TEXT("Choose one floor-draft square to pick its ink. Paper is valid. Picking does not paint or change Undo / Redo; the previous brush resumes."):TEXT("Picking cancelled. Your previous Point / Area fill brush resumes."); Changed=true; }
    else if (Action==EDaedalusMotifAction::Guide)
    {
        if (!HasGuideReference()) Notice=TEXT("Keep or load a sketch first. There is no kept-image reference yet; the drawing, brush and history stay unchanged.");
        else
        {
            GuideMode=(GuideMode+1)%3; Changed=true;
            Notice=GuideMode==1?TEXT("Kept Ghost: hollow inset marks show ink in the last kept / loaded image. They are not paint. Pick still reads actual draft ink; no history or file changes."):
                GuideMode==2?TEXT("Changes: inset gold marks show squares different from the last kept / loaded image. Paper erase and Pick keep their actual draft meaning; no history changes."):
                TEXT("Guide off. The draft, brush, armed Pick and drawing history are unchanged.");
        }
    }
    else if (Action==EDaedalusMotifAction::Symmetry)
    { Mode=static_cast<daedalus::motif::Symmetry>((static_cast<unsigned>(Mode)+1)%daedalus::motif::SymmetryCount); Notice=TEXT("Symmetry changed. The next point or filled region is copied through this symmetry. Outlines show its current targets; the picture is unchanged."); Changed=true; }
    else if (Action==EDaedalusMotifAction::Brush)
    { bFill=!bFill; Notice=bFill?TEXT("Area fill: touching same-colour squares and their symmetry copies. Diagonal corners are separate. One fill uses one Undo edit."):TEXT("Point brush: paint the selected square and its symmetry copies. Brush choice does not use Undo."); Changed=true; }
    else if (Action==EDaedalusMotifAction::Rotate || Action==EDaedalusMotifAction::FlipColumns || Action==EDaedalusMotifAction::FlipRows)
    {
        const auto Transform=Action==EDaedalusMotifAction::Rotate?daedalus::motif::CanvasTransform::Clockwise:
            Action==EDaedalusMotifAction::FlipColumns?daedalus::motif::CanvasTransform::MirrorColumns:daedalus::motif::CanvasTransform::MirrorRows;
        Changed=Draft.Transform(Transform);
        Notice=Changed?TEXT("The whole draft changed in one edit. Undo restores it. Export creates a new version; all kept sketches stay unchanged."):
            TEXT("This picture already matches that transformation. No drawing edit was added; Redo is kept.");
    }
    else if (Action==EDaedalusMotifAction::Undo)
    { Changed=Draft.Undo(); Notice=Changed?TEXT("Drawing edit undone. Export to keep the current picture."):TEXT("There is no earlier drawing edit to undo."); }
    else if (Action==EDaedalusMotifAction::Redo)
    { Changed=Draft.Redo(); Notice=Changed?TEXT("Drawing edit redone. Export to keep the current picture."):TEXT("There is no drawing edit to redo."); }
    else if (Action==EDaedalusMotifAction::Export)
    {
        const uint64 StartEpoch=Epoch; const auto Pixels=Draft.Canvas(); std::string NewId; FString Error;
        Changed=ExportPrepared(Pixels,LineageId,NewId,Error);
        if (!IsStudioAlive() || Epoch!=StartEpoch) return false;
        if (Changed) { Baseline=Pixels; LineageId=NewId; Notice=TEXT("New local sketch exported and readback verified. Earlier files stay unchanged. Your draft is kept."); }
        else Notice=Error;
    }
    else if (Action==EDaedalusMotifAction::NextSketch) Changed=NextSketch();
    else if (Action==EDaedalusMotifAction::SaveLoad) Changed=SaveAndLoad();
    else if (Action==EDaedalusMotifAction::SaveClear) Changed=SaveAndClear();
    if (!IsStudioAlive()) return false;
    Refresh(); return IsStudioAlive() && Changed;
}

void ADaedalusGalleryMotifStudio::SpawnTools()
{
    if (!IsStudioAlive() || bToolsAttempted) return;
    bToolsAttempted=true; const uint64 StartEpoch=Epoch;
    for (int32 I=0;I<DaedalusMotifLocal::ToolCount && IsStudioAlive();++I)
    {
        const auto Action=DaedalusMotifLocal::ToolAction(I); const int32 Cell=DaedalusMotifLocal::ToolParameter(I);
        const FTransform World=FTransform(DaedalusMotifLocal::ToolAt(I))*GetActorTransform();
        FActorSpawnParameters Parameters; Parameters.Owner=this; Parameters.ObjectFlags=RF_Transient|RF_DuplicateTransient; Parameters.bDeferConstruction=true;
        Parameters.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        Parameters.CustomPreSpawnInitialization=[](AActor* Actor) { Actor->SetActorEnableCollision(false); };
        auto* NewTool=GetWorld()->SpawnActor<ADaedalusMotifTool>(ADaedalusMotifTool::StaticClass(),World,Parameters);
        auto Valid=[&]() { return IsStudioAlive() && Epoch==StartEpoch && IsValid(NewTool) && !NewTool->IsActorBeingDestroyed() && NewTool->GetOwner()==this && NewTool->GetWorld()==GetWorld(); };
        if (!Valid())
        {
            if (IsValid(NewTool) && NewTool->GetOwner()==this && !NewTool->IsActorBeingDestroyed()) NewTool->Destroy();
            if (IsStudioAlive()) bAvailable=false; return;
        }
        OwnedTools.Add(NewTool); NewTool->OnEndPlay.AddUniqueDynamic(this,&ADaedalusGalleryMotifStudio::ToolEnded);
        if (!NewTool->ConfigureStudio(this,Action,Cell) || !Valid()) { if (IsStudioAlive()) bAvailable=false; return; }
        NewTool->FinishSpawning(World);
        if (!Valid() || !NewTool->HasActorBegunPlay()) { if (IsStudioAlive()) bAvailable=false; return; }
        NewTool->AttachToActor(this,FAttachmentTransformRules::KeepWorldTransform);
        if (!Valid() || !NewTool->GetActorTransform().Equals(World,0.01)) { if (IsStudioAlive()) bAvailable=false; return; }
    }
    if (IsStudioAlive() && !ToolsReady()) bAvailable=false;
}
void ADaedalusGalleryMotifStudio::BeginPlay()
{
    bEnding=false; ++Epoch; Super::BeginPlay(); if (!IsStudioAlive()) return;
    // No folder lookup, enumeration, read or write occurs in BeginPlay.
    if (GetWorld()->GetNetMode()!=NM_Standalone || !Draft.Begin() || !ViewsReady())
    { bAvailable=false; Notice=TEXT("This local motif studio is unavailable here."); Refresh(); return; }
    Baseline=Draft.Canvas(); TGuardValue<bool> Preparing(bBusy,true); SpawnTools(); if (!IsStudioAlive()) return;
    Notice=bAvailable?TEXT("Choose ink on numbered palette chips, or Pick ink from the draft. Point / Area fill, Rotate / Flip and 64-step Undo help you draw. Export to keep; there is no autosave."):
        TEXT("The tool set is incomplete. No sketch was changed; a remaining Export tool can preserve a draft.");
    Refresh();
}
void ADaedalusGalleryMotifStudio::ToolEnded(AActor* Actor,EEndPlayReason::Type)
{
    if (!IsStudioAlive() || !Actor || Actor->GetOwner()!=this) return;
    bool Found=false; for (const auto& Tool:OwnedTools) if (Tool.Get()==Actor) { Found=true; break; } if (!Found) return;
    bAvailable=false; ArmedAction=EDaedalusMotifAction::Cell;
    Notice=TEXT("A studio tool is unavailable. Your draft is kept; a remaining Export tool can preserve it.");
    if (!bBusy && !bNotifying) Refresh();
}
void ADaedalusGalleryMotifStudio::ReleaseTools()
{
    const auto Tools=OwnedTools; OwnedTools.Reset();
    for (const auto& Tool:Tools) if (IsValid(Tool)) Tool->OnEndPlay.RemoveDynamic(this,&ADaedalusGalleryMotifStudio::ToolEnded);
    for (const auto& Tool:Tools) if (IsValid(Tool) && Tool->GetOwner()==this && !Tool->IsActorBeingDestroyed()) Tool->Destroy();
}
void ADaedalusGalleryMotifStudio::EndPlay(const EEndPlayReason::Type Reason)
{
    bEnding=true; ++Epoch; ReleaseTools(); OnViewChanged.Broadcast(this); Super::EndPlay(Reason);
}

ADaedalusMotifTool::ADaedalusMotifTool()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    ToolRoot=CreateDefaultSubobject<USceneComponent>(TEXT("MotifToolRoot")); RootComponent=ToolRoot;
    Body->SetupAttachment(ToolRoot); Glow->SetupAttachment(ToolRoot); Glow->SetIntensity(0.f); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeScale3D(FVector(0.35,0.5,0.25)); Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Label=CreateDefaultSubobject<UTextRenderComponent>(TEXT("MotifToolLabel")); Label->SetupAttachment(ToolRoot);
    Label->SetRelativeLocation(FVector(15,0,100)); Label->SetWorldSize(10.f); Label->SetHorizontalAlignment(EHTA_Center);
    Label->SetVerticalAlignment(EVRTA_TextCenter); Label->SetTextRenderColor(FColor(25,40,60));
}
void ADaedalusMotifTool::BeginPlay()
{ bEnding=false; Super::BeginPlay(); if (!bEnding && !IsActorBeingDestroyed()) ConfigureStudio(Studio,Action,Cell); }
void ADaedalusMotifTool::UnbindStudio()
{
    if (auto* Previous=ObservedStudio.Get()) Previous->OnViewChanged.RemoveDynamic(this,&ADaedalusMotifTool::StudioViewChanged);
    ObservedStudio.Reset();
}
bool ADaedalusMotifTool::ConfigureStudio(ADaedalusGalleryMotifStudio* NewStudio,EDaedalusMotifAction NewAction,int32 NewCell)
{
    if (!IsInGameThread() || bEnding || IsActorBeingDestroyed() || !DaedalusMotifLocal::ValidAction(NewAction,NewCell) ||
        !IsValid(Body) || Body->GetOwner()!=this || !IsValid(Glow) || Glow->GetOwner()!=this || !IsValid(Label) || Label->GetOwner()!=this ||
        (NewStudio && (!IsValid(NewStudio) || NewStudio->IsActorBeingDestroyed() || NewStudio->GetWorld()!=GetWorld()))) return false;
    UnbindStudio(); Studio=NewStudio; Action=NewAction; Cell=NewCell;
    Body->SetVisibility(Action!=EDaedalusMotifAction::Cell && Action!=EDaedalusMotifAction::Palette); Glow->SetIntensity(0.f); Glow->SetVisibility(false);
    if (Action==EDaedalusMotifAction::Palette)
    {
        Label->SetRelativeLocation(FVector(0,0,8)); Label->SetRelativeRotation(FRotator(90,0,0)); Label->SetWorldSize(8.f);
        const auto Colour=DaedalusMotifLocal::Colour(Cell);
        const float Luminance=0.2126f*Colour.R+0.7152f*Colour.G+0.0722f*Colour.B;
        Label->SetTextRenderColor(Luminance<0.45f?FColor::White:FColor(25,40,60));
    }
    else
    {
        Label->SetRelativeLocation(FVector(15,0,100)); Label->SetRelativeRotation(FRotator::ZeroRotator); Label->SetWorldSize(10.f);
        Label->SetTextRenderColor(FColor(25,40,60));
    }
    if (IsValid(Studio)) { ObservedStudio=Studio; Studio->OnViewChanged.AddUniqueDynamic(this,&ADaedalusMotifTool::StudioViewChanged); }
    RefreshLabel(); return true;
}
bool ADaedalusMotifTool::Matches(const ADaedalusGalleryMotifStudio* Target,EDaedalusMotifAction ExpectedAction,int32 ExpectedCell) const
{ return !bEnding && Studio.Get()==Target && Action==ExpectedAction && Cell==ExpectedCell; }
void ADaedalusMotifTool::RefreshLabel()
{
    if (!bEnding && IsValid(Label)) Label->SetText(FText::FromString(IsValid(Studio) && Studio->GetWorld()==GetWorld()?Studio->ToolLabel(Action,Cell):TEXT("--")));
}
void ADaedalusMotifTool::StudioViewChanged(ADaedalusGalleryMotifStudio* ChangedStudio)
{
    if (bEnding || ChangedStudio!=Studio.Get()) return;
    if (!ChangedStudio->IsStudioAlive()) { UnbindStudio(); Studio=nullptr; }
    RefreshLabel();
}
void ADaedalusMotifTool::EndPlay(const EEndPlayReason::Type Reason)
{ bEnding=true; UnbindStudio(); Studio=nullptr; Super::EndPlay(Reason); }
FString ADaedalusMotifTool::Prompt(const ADaedalusHero*) const
{ return !bEnding && HasActorBegunPlay() && IsValid(Studio) && Studio->GetWorld()==GetWorld()?Studio->ToolPrompt(Action,Cell):TEXT("Motif tool is not connected"); }
bool ADaedalusMotifTool::Use(ADaedalusHero* Hero)
{ return !bEnding && IsValid(Studio) && Studio->GetWorld()==GetWorld() && Studio->Operate(Hero,this,Action,Cell); }
