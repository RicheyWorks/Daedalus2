// SPDX-License-Identifier: MIT
#include "DaedalusGallerySpectrumTable.h"
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

namespace DaedalusSpectrumLocal
{
    FVector Source(int32 Router) { return FVector(-75,250,110+60*Router); }
    FVector Window(int32 Index) { return FVector(-75,-200,125+85*Index); }
    FVector ControlAt(int32 Index)
    { return Index<6?FVector(320+85*(Index/3),160-160*(Index%3),65):FVector(550,240-120*(Index-6),65); }
    EDaedalusSpectrumAction ActionAt(int32 Index)
    { return Index<6?EDaedalusSpectrumAction::Router:static_cast<EDaedalusSpectrumAction>(Index-5); }
    bool ValidAction(EDaedalusSpectrumAction Action,int32 Router)
    {
        if (Action==EDaedalusSpectrumAction::Router) return Router>=0 && Router<6;
        return Router==-1 && static_cast<uint8>(Action)>=1 && static_cast<uint8>(Action)<=5;
    }
    const TCHAR* ShapeName(int32 Index)
    { static const TCHAR* Names[]={TEXT("CIRCLE"),TEXT("SQUARE"),TEXT("TRIANGLE"),TEXT("DIAMOND")}; return Names[Index]; }
    FString Tags(int32 Channels)
    {
        FString Out;
        if (Channels&1) Out=TEXT("R");
        if (Channels&2) Out+=Out.IsEmpty()?TEXT("G"):TEXT("+G");
        if (Channels&4) Out+=Out.IsEmpty()?TEXT("B"):TEXT("+B");
        return Out.IsEmpty()?TEXT("none"):Out;
    }
    FLinearColor Colour(int32 Channels)
    {
        if (!Channels) return FLinearColor(0.025f,0.035f,0.05f);
        return FLinearColor((Channels&1)?1.f:0.f,(Channels&2)?1.f:0.f,(Channels&4)?1.f:0.f);
    }
    bool LocalReach(const ADaedalusHero* Hero,const AActor* Actor)
    {
        if (!IsInGameThread() || !IsValid(Hero) || Hero->IsActorBeingDestroyed() || !Hero->HasActorBegunPlay() || !IsValid(Actor) ||
            Actor->IsActorBeingDestroyed() || !Actor->HasActorBegunPlay() || !Actor->GetWorld() || Hero->GetWorld()!=Actor->GetWorld() ||
            Actor->GetWorld()->GetNetMode()!=NM_Standalone || !Hero->IsLocallyControlled() || !FMath::IsFinite(Hero->InteractReach) || Hero->InteractReach<=0.f) return false;
        const auto* Controller=Cast<APlayerController>(Hero->GetController());
        if (!IsValid(Controller) || Controller->IsActorBeingDestroyed() || Controller->GetWorld()!=Actor->GetWorld() || !Controller->IsLocalController() ||
            Controller->GetPawn()!=Hero || !IsValid(Controller->GetLocalPlayer())) return false;
        const double Distance=FVector::DistSquared(Hero->GetActorLocation(),Actor->GetActorLocation());
        return FMath::IsFinite(Distance) && Distance<=static_cast<double>(Hero->InteractReach)*Hero->InteractReach;
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
    struct Ink
    {
        TArray<FVector> Vertices; TArray<int32> Triangles; TArray<FLinearColor> Colours;
        void Triangle(FVector A,FVector B,FVector C,FLinearColor Colour)
        { const int32 At=Vertices.Num(); Vertices.Append({A,B,C}); Triangles.Append({At,At+1,At+2}); Colours.Append({Colour,Colour,Colour}); }
        void Quad(FVector A,FVector B,FVector C,FVector D,FLinearColor Colour)
        { Triangle(A,B,C,Colour); Triangle(A,C,D,Colour); }
        void Line(FVector A,FVector B,double Width,FLinearColor Colour)
        {
            const FVector Direction=(B-A).GetSafeNormal(); const FVector Side(0,-Direction.Z*Width,Direction.Y*Width);
            Quad(A-Side,B-Side,B+Side,A+Side,Colour);
        }
        void Square(FVector At,double Y,double Z,FLinearColor Colour)
        { Quad(At+FVector(0,-Y,-Z),At+FVector(0,Y,-Z),At+FVector(0,Y,Z),At+FVector(0,-Y,Z),Colour); }
        void Shape(FVector At,int32 Kind,double Radius,FLinearColor Colour)
        {
            if (Kind==0)
                for (int32 I=0;I<16;++I)
                {
                    const double A=2*PI*I/16,B=2*PI*(I+1)/16;
                    Triangle(At,At+FVector(0,FMath::Cos(A)*Radius,FMath::Sin(A)*Radius),At+FVector(0,FMath::Cos(B)*Radius,FMath::Sin(B)*Radius),Colour);
                }
            else if (Kind==1) Square(At,Radius,Radius,Colour);
            else if (Kind==2) Triangle(At+FVector(0,0,Radius),At+FVector(0,-Radius,-Radius),At+FVector(0,Radius,-Radius),Colour);
            else Quad(At+FVector(0,0,Radius),At+FVector(0,-Radius,0),At+FVector(0,0,-Radius),At+FVector(0,Radius,0),Colour);
        }
        void Arrow(FVector A,FVector B,FLinearColor Colour)
        {
            const FVector Direction=(B-A).GetSafeNormal(), Side(0,-Direction.Z*3.5,Direction.Y*3.5),Mid=(A+B)*0.5+FVector(0.6,0,0);
            Triangle(Mid+Direction*7,Mid-Direction*5+Side,Mid-Direction*5-Side,Colour);
        }
    };
}

ADaedalusGallerySpectrumTable::ADaedalusGallerySpectrumTable()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    TableRoot=CreateDefaultSubobject<USceneComponent>(TEXT("SpectrumTableRoot")); RootComponent=TableRoot;
    Body->SetupAttachment(TableRoot); Glow->SetupAttachment(TableRoot); Glow->SetIntensity(0.f); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Engine/EngineDebugMaterials/VertexColorMaterial.VertexColorMaterial")); InkMaterial=Material.Object;
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeLocation(FVector(0,0,80)); Body->SetRelativeScale3D(FVector(2.8,6.8,0.18)); Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    auto* Back=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SpectrumBackboard")); Back->SetupAttachment(TableRoot); Back->SetStaticMesh(Cube.Object);
    Back->SetRelativeLocation(FVector(-90,0,260)); Back->SetRelativeScale3D(FVector(0.2,6.8,4.8)); Back->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Diagram=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("RGBChannelDiagram")); Diagram->SetupAttachment(TableRoot);
    Diagram->SetCollisionEnabled(ECollisionEnabled::NoCollision); Diagram->SetCastShadow(false);
    Title=CreateDefaultSubobject<UTextRenderComponent>(TEXT("SpectrumTitle")); Title->SetupAttachment(TableRoot);
    Title->SetRelativeLocation(FVector(-60,0,540)); Title->SetWorldSize(23.f); Title->SetHorizontalAlignment(EHTA_Center); Title->SetTextRenderColor(FColor(25,40,60));
    Readout=CreateDefaultSubobject<UTextRenderComponent>(TEXT("SpectrumReadout")); Readout->SetupAttachment(TableRoot);
    Readout->SetRelativeLocation(FVector(170,480,370)); Readout->SetWorldSize(11.f); Readout->SetHorizontalAlignment(EHTA_Center);
    Readout->SetVerticalAlignment(EVRTA_TextTop); Readout->SetTextRenderColor(FColor(25,40,60));
    for (int32 I=0;I<6;++I)
    {
        auto* Label=CreateDefaultSubobject<UTextRenderComponent>(*FString::Printf(TEXT("RGBSource%d"),I)); Label->SetupAttachment(TableRoot);
        Label->SetRelativeLocation(DaedalusSpectrumLocal::Source(I)+FVector(10,45,0)); Label->SetWorldSize(12.f); Label->SetHorizontalAlignment(EHTA_Center);
        Label->SetVerticalAlignment(EVRTA_TextCenter); Label->SetTextRenderColor(FColor(25,40,60)); SourceLabels.Add(Label);
    }
    for (int32 I=0;I<4;++I)
    {
        auto* Label=CreateDefaultSubobject<UTextRenderComponent>(*FString::Printf(TEXT("RGBWindow%d"),I)); Label->SetupAttachment(TableRoot);
        Label->SetRelativeLocation(DaedalusSpectrumLocal::Window(I)+FVector(16,0,34)); Label->SetWorldSize(9.f); Label->SetHorizontalAlignment(EHTA_Center);
        Label->SetVerticalAlignment(EVRTA_TextTop); Label->SetTextRenderColor(FColor(25,40,60)); WindowLabels.Add(Label);
    }
}

bool ADaedalusGallerySpectrumTable::IsTableAlive() const
{ return IsInGameThread() && !bEnding && !IsActorBeingDestroyed() && HasActorBegunPlay() && GetWorld(); }
bool ADaedalusGallerySpectrumTable::ViewsReady() const
{
    if (!IsTableAlive() || !InkMaterial || !IsValid(Diagram) || Diagram->GetOwner()!=this || !Diagram->IsRegistered() ||
        !IsValid(Readout) || Readout->GetOwner()!=this || !Readout->IsRegistered() || !IsValid(Title) || Title->GetOwner()!=this || !Title->IsRegistered() ||
        SourceLabels.Num()!=6 || WindowLabels.Num()!=4) return false;
    for (const auto& Label:SourceLabels) if (!IsValid(Label) || Label->GetOwner()!=this || !Label->IsRegistered()) return false;
    for (const auto& Label:WindowLabels) if (!IsValid(Label) || Label->GetOwner()!=this || !Label->IsRegistered()) return false;
    return true;
}
bool ADaedalusGallerySpectrumTable::ToolsReady() const
{
    if (!IsTableAlive() || OwnedControls.Num()!=11) return false;
    for (int32 I=0;I<11;++I)
    {
        const auto* Control=OwnedControls[I].Get();
        if (!IsValid(Control) || Control->IsActorBeingDestroyed() || !Control->HasActorBegunPlay() || Control->GetOwner()!=this || Control->GetWorld()!=GetWorld() ||
            Control->GetActorEnableCollision() || !Control->Matches(this,DaedalusSpectrumLocal::ActionAt(I),I<6?I:-1) ||
            !Control->GetActorTransform().Equals(FTransform(DaedalusSpectrumLocal::ControlAt(I))*GetActorTransform(),0.01)) return false;
    }
    return true;
}
bool ADaedalusGallerySpectrumTable::IsCurrentComplete() const
{ daedalus::spectrum::Evaluation View; return Run.View(View) && View.Complete; }
FString ADaedalusGallerySpectrumTable::Prompt(const ADaedalusHero*) const
{ return IsTableAlive() && Run.Active() && bAvailable?TEXT("E / X: A free shortest-route hint for this colour picture"):TEXT("Spectrum Table is unavailable"); }
bool ADaedalusGallerySpectrumTable::Use(ADaedalusHero* Hero)
{ return Operate(Hero,this,EDaedalusSpectrumAction::Hint); }

void ADaedalusGallerySpectrumTable::DrawTable()
{
    if (!ViewsReady() || !Run.Active()) return;
    daedalus::spectrum::Evaluation View; if (!Run.View(View)) return;
    DaedalusSpectrumLocal::Ink Ink;
    for (int32 I=0;I<6;++I)
    {
        const auto& Router=daedalus::spectrum::Routers[I]; const int32 Position=(Run.Mask()>>I)&1,Destination=Router.Windows[Position];
        const FVector A=DaedalusSpectrumLocal::Source(I)+FVector(0,-18,0),B=DaedalusSpectrumLocal::Window(Destination)+FVector(0,124,-25+10*I);
        Ink.Line(A,B,4.5,FLinearColor(0.05f,0.08f,0.1f)); Ink.Line(A+FVector(0.4,0,0),B+FVector(0.4,0,0),2.7,DaedalusSpectrumLocal::Colour(Router.Channel));
        Ink.Arrow(A,B,FLinearColor::White);
        const FVector At=DaedalusSpectrumLocal::Source(I)+FVector(1.5,0,0);
        Ink.Triangle(At+FVector(0,18,18),At-FVector(0,18,0),At+FVector(0,18,-18),FLinearColor(0.05f,0.08f,0.1f));
        Ink.Triangle(At+FVector(0.3,13,13),At+FVector(0.3,-13,0),At+FVector(0.3,13,-13),DaedalusSpectrumLocal::Colour(Router.Channel));
        if (bHintVisible && ShownHint.RouterIndex==I)
        {
            const FVector X(0,25,0),Z(0,0,25),P=At+FVector(0.6,0,0);
            Ink.Line(P-X-Z,P+X-Z,1.6,FLinearColor(1,0.7f,0)); Ink.Line(P+X-Z,P+X+Z,1.6,FLinearColor(1,0.7f,0));
            Ink.Line(P+X+Z,P-X+Z,1.6,FLinearColor(1,0.7f,0)); Ink.Line(P-X+Z,P-X-Z,1.6,FLinearColor(1,0.7f,0));
        }
        SourceLabels[I]->SetText(FText::FromString(FString::Printf(TEXT("%d [%s]\n%s -> W%d"),I+1,*DaedalusSpectrumLocal::Tags(Router.Channel),Position?TEXT("B"):TEXT("A"),Destination+1)));
        if (!ViewsReady()) return;
    }
    for (int32 I=0;I<4;++I)
    {
        const FVector At=DaedalusSpectrumLocal::Window(I); const int32 Target=daedalus::spectrum::Pictures[Run.CurrentPicture()].Targets[I],Current=View.Channels[I];
        const bool HintWindow=bHintVisible && daedalus::spectrum::Routers[ShownHint.RouterIndex].Windows[ShownHint.ToB?1:0]==I;
        Ink.Square(At+FVector(1,0,0),123,41,HintWindow?FLinearColor(1,0.7f,0):FLinearColor(0.05f,0.08f,0.1f));
        Ink.Square(At+FVector(1.3,0,0),120,38,FLinearColor(0.91f,0.94f,0.95f));
        const FVector Want=At+FVector(2,55,-21),Now=At+FVector(2,-55,-21);
        Ink.Shape(Want,I,16,FLinearColor(0.04f,0.06f,0.09f)); Ink.Shape(Want+FVector(0.3,0,0),I,13,DaedalusSpectrumLocal::Colour(Target));
        Ink.Shape(Now,I,16,FLinearColor(0.04f,0.06f,0.09f)); Ink.Shape(Now+FVector(0.3,0,0),I,13,DaedalusSpectrumLocal::Colour(Current));
        WindowLabels[I]->SetText(FText::FromString(FString::Printf(TEXT("W%d %s / %s\nWANT %s [%s]\nNOW %s [%s]"),I+1,DaedalusSpectrumLocal::ShapeName(I),Target==Current?TEXT("MATCH"):TEXT("MIX"),
            UTF8_TO_TCHAR(daedalus::spectrum::ColourName(Target)),*DaedalusSpectrumLocal::Tags(Target),UTF8_TO_TCHAR(daedalus::spectrum::ColourName(Current)),*DaedalusSpectrumLocal::Tags(Current))));
        if (!ViewsReady()) return;
    }
    TArray<FVector> Normals; Normals.Init(FVector(1,0,0),Ink.Vertices.Num()); TArray<FVector2D> UV; UV.Init(FVector2D::ZeroVector,Ink.Vertices.Num()); TArray<FProcMeshTangent> Tangents;
    Diagram->CreateMeshSection_LinearColor(0,Ink.Vertices,Ink.Triangles,Normals,UV,Ink.Colours,Tangents,false);
    if (ViewsReady()) Diagram->SetMaterial(0,InkMaterial);
}
void ADaedalusGallerySpectrumTable::Refresh(int32 NewlyCompleted)
{
    if (!IsTableAlive() || bNotifying) return;
    FString Text;
    if (Run.Active())
    {
        daedalus::spectrum::Evaluation View; Run.View(View);
        Text=FString::Printf(TEXT("PICTURE %d / 3: %s\n%d / 4 WINDOWS MATCH / %d PICTURES COMPLETED BEFORE\nUndo %u / Redo %u\n"),Run.CurrentPicture()+1,
            UTF8_TO_TCHAR(daedalus::spectrum::Pictures[Run.CurrentPicture()].Name),View.Matched,Run.CompletedCount(),static_cast<unsigned>(Run.UndoCount()),static_cast<unsigned>(Run.RedoCount()));
        if (Run.EverCompleted(Run.CurrentPicture()) && !View.Complete) Text+=TEXT("This picture matched before; current colours remain editable.\n");
        if (ViewsReady())
        {
            Title->SetText(FText::FromString(FString(TEXT("SPECTRUM TABLE / "))+UTF8_TO_TCHAR(daedalus::spectrum::Pictures[Run.CurrentPicture()].Name)));
            if (!IsTableAlive()) return; DrawTable();
        }
    }
    Text+=Notice;
    if (!IsTableAlive()) return;
    if (IsValid(Readout) && Readout->GetOwner()==this) Readout->SetText(FText::FromString(DaedalusSpectrumLocal::Wrap(Text)));
    if (!IsTableAlive()) return;
    TGuardValue<bool> Notification(bNotifying,true); OnViewChanged.Broadcast(this);
    if (!IsTableAlive()) return;
    if (NewlyCompleted>=0) OnPictureCompleted.Broadcast(this,NewlyCompleted); // No gameplay writes after event.
}
FString ADaedalusGallerySpectrumTable::ControlLabel(EDaedalusSpectrumAction Action,int32 Router) const
{
    if (!IsTableAlive() || !Run.Active()) return TEXT("--");
    FString Text;
    if (!bAvailable || !ViewsReady()) Text=TEXT("Table unavailable");
    else if (Action==EDaedalusSpectrumAction::Router && Router>=0 && Router<6)
    {
        const auto& Beam=daedalus::spectrum::Routers[Router]; const bool B=(Run.Mask()&(1<<Router))!=0;
        Text=FString::Printf(TEXT("%d [%s] / %s -> W%d"),Router+1,*DaedalusSpectrumLocal::Tags(Beam.Channel),B?TEXT("B"):TEXT("A"),Beam.Windows[B?1:0]+1);
        if (bHintVisible && ShownHint.RouterIndex==Router) Text+=FString::Printf(TEXT("\n[HINT] -> %s"),ShownHint.ToB?TEXT("B"):TEXT("A"));
    }
    else if (Action==EDaedalusSpectrumAction::NextPicture) Text=TEXT("Next picture\nRoutes are kept");
    else if (Action==EDaedalusSpectrumAction::Hint) Text=bHintVisible?TEXT("Put hint away"):TEXT("Hint / free");
    else if (Action==EDaedalusSpectrumAction::Undo) Text=FString::Printf(TEXT("Undo / %u"),static_cast<unsigned>(Run.UndoCount()));
    else if (Action==EDaedalusSpectrumAction::Redo) Text=FString::Printf(TEXT("Redo / %u"),static_cast<unsigned>(Run.RedoCount()));
    else if (Action==EDaedalusSpectrumAction::Restart) Text=bRestartArmed?TEXT("Confirm restart"):TEXT("Restart this picture");
    else Text=TEXT("--");
    if (bFeedback && Action==FeedbackAction && Router==FeedbackRouter) Text+=TEXT("\n")+DaedalusSpectrumLocal::Wrap(Notice,36,3);
    return Text;
}
FString ADaedalusGallerySpectrumTable::ControlPrompt(EDaedalusSpectrumAction Action,int32 Router) const
{
    if (!IsTableAlive() || !bAvailable || !Run.Active() || !ViewsReady() || !DaedalusSpectrumLocal::ValidAction(Action,Router)) return TEXT("Spectrum tool is unavailable");
    if (Action==EDaedalusSpectrumAction::Router)
    {
        const bool B=(Run.Mask()&(1<<Router))!=0; const auto& Beam=daedalus::spectrum::Routers[Router];
        return FString::Printf(TEXT("E / X: Router %d [%s] %s -> %s (Window %d)"),Router+1,*DaedalusSpectrumLocal::Tags(Beam.Channel),B?TEXT("B"):TEXT("A"),B?TEXT("A"):TEXT("B"),Beam.Windows[B?0:1]+1);
    }
    if (Action==EDaedalusSpectrumAction::NextPicture) return TEXT("E / X: Next picture; every picture keeps its routes, Undo and Redo");
    if (Action==EDaedalusSpectrumAction::Hint) return TEXT("E / X: Free shortest-route hint; a useful turn need not match more windows immediately");
    if (Action==EDaedalusSpectrumAction::Undo) return TEXT("E / X: Undo this picture's last turn");
    if (Action==EDaedalusSpectrumAction::Redo) return TEXT("E / X: Redo this picture's last undone turn");
    return bRestartArmed?TEXT("E / X: Confirm restart of this picture only; first completion stays"):TEXT("E / X: Restart this picture - confirm twice");
}
bool ADaedalusGallerySpectrumTable::Operate(ADaedalusHero* Hero,const AActor* Tool,EDaedalusSpectrumAction Action,int32 Router)
{
    if (!IsTableAlive() || GetWorld()->GetNetMode()!=NM_Standalone || !Run.Active() || bBusy || bNotifying ||
        !DaedalusSpectrumLocal::ValidAction(Action,Router) || !DaedalusSpectrumLocal::LocalReach(Hero,Tool)) return false;
    if (!IsTableAlive() || !IsValid(Tool) || Tool->IsActorBeingDestroyed() || !Tool->HasActorBegunPlay() || Tool->GetWorld()!=GetWorld()) return false;
    if (Tool==this)
    {
        if (Action!=EDaedalusSpectrumAction::Hint || Router!=-1) return false;
    }
    else
    {
        const int32 Slot=Action==EDaedalusSpectrumAction::Router?Router:5+static_cast<int32>(Action);
        const auto* Control=Cast<ADaedalusSpectrumControl>(Tool);
        if (!Control || !OwnedControls.IsValidIndex(Slot) || OwnedControls[Slot].Get()!=Control || Control->GetOwner()!=this ||
            !Control->Matches(this,Action,Router) || !Control->GetActorTransform().Equals(FTransform(DaedalusSpectrumLocal::ControlAt(Slot))*GetActorTransform(),0.01)) return false;
    }
    TGuardValue<bool> Busy(bBusy,true); bFeedback=true; FeedbackAction=Action; FeedbackRouter=Router;
    if (!bAvailable || !ViewsReady() || !ToolsReady())
    { bAvailable=false; Notice=TEXT("A table view or tool is unavailable. All picture routes and history are kept; no turn was made."); Refresh(); return false; }
    if (Action!=EDaedalusSpectrumAction::Restart) bRestartArmed=false;
    if (Action==EDaedalusSpectrumAction::Hint)
    {
        if (bHintVisible) { bHintVisible=false; Notice=TEXT("Hint put away. Different R, G and B channels combine; two red beams still count as red."); }
        else if (Run.Hint(ShownHint))
        {
            bHintVisible=true;
            Notice=FString::Printf(TEXT("Try router %d -> %s. A full picture is %d turns away, including this turn. It need not match more windows immediately."),ShownHint.RouterIndex+1,ShownHint.ToB?TEXT("B"):TEXT("A"),ShownHint.Remaining);
        }
        else Notice=TEXT("All four windows match. You can keep experimenting or choose another picture; first completion stays remembered.");
        Refresh(); return IsTableAlive();
    }
    if (Action==EDaedalusSpectrumAction::Restart && !bRestartArmed)
    {
        bRestartArmed=true; Notice=TEXT("Use Restart once more to restore this picture's starting routes and clear its history. Other pictures and first completions stay; another tool cancels.");
        Refresh(); return false;
    }
    std::array<bool,3> Before{}; for (int32 I=0;I<3;++I) Before[I]=Run.EverCompleted(I);
    bool Changed=false;
    if (Action==EDaedalusSpectrumAction::Router) Changed=Run.Toggle(Router);
    else if (Action==EDaedalusSpectrumAction::NextPicture) Changed=Run.SelectPicture((Run.CurrentPicture()+1)%3);
    else if (Action==EDaedalusSpectrumAction::Undo) Changed=Run.Undo();
    else if (Action==EDaedalusSpectrumAction::Redo) Changed=Run.Redo();
    else if (Action==EDaedalusSpectrumAction::Restart) { Changed=Run.Restart(); bRestartArmed=false; }
    if (!Changed)
    {
        Notice=Action==EDaedalusSpectrumAction::Restart?TEXT("This picture is already at its start with empty history. Nothing changed."):TEXT("There is no turn in that history direction. Try a router or a free Hint.");
        Refresh(); return false;
    }
    bHintVisible=false; daedalus::spectrum::Evaluation View; Run.View(View);
    const int32 Picture=Run.CurrentPicture(); const int32 NewlyCompleted=!Before[Picture] && Run.EverCompleted(Picture)?Picture:-1;
    if (View.Complete) Notice=TEXT("All four window colours match! The picture is complete. You can still turn routes, Undo, Redo or choose another picture.");
    else if (Action==EDaedalusSpectrumAction::NextPicture) Notice=TEXT("Picture changed; its routes and history were kept. Match WANT and NOW names and channel tags on each numbered window.");
    else if (Action==EDaedalusSpectrumAction::Restart) Notice=TEXT("Only this picture restarted. Other routes and all first completions stay remembered.");
    else Notice=FString::Printf(TEXT("%d of four windows match. Colours change together; a helpful turn may leave the same number matched. Undo, Redo and Hint are free."),View.Matched);
    Refresh(NewlyCompleted); return IsTableAlive();
}

void ADaedalusGallerySpectrumTable::SpawnControls()
{
    if (!IsTableAlive() || bToolsAttempted) return;
    bToolsAttempted=true; const uint64 StartEpoch=Epoch;
    for (int32 I=0;I<11 && IsTableAlive();++I)
    {
        const auto Action=DaedalusSpectrumLocal::ActionAt(I); const int32 Router=I<6?I:-1;
        const FTransform World=FTransform(DaedalusSpectrumLocal::ControlAt(I))*GetActorTransform();
        FActorSpawnParameters Parameters; Parameters.Owner=this; Parameters.ObjectFlags=RF_Transient|RF_DuplicateTransient; Parameters.bDeferConstruction=true;
        Parameters.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        Parameters.CustomPreSpawnInitialization=[](AActor* Actor) { Actor->SetActorEnableCollision(false); };
        auto* Control=GetWorld()->SpawnActor<ADaedalusSpectrumControl>(ADaedalusSpectrumControl::StaticClass(),World,Parameters);
        auto Valid=[&]() { return IsTableAlive() && Epoch==StartEpoch && IsValid(Control) && !Control->IsActorBeingDestroyed() && Control->GetOwner()==this && Control->GetWorld()==GetWorld(); };
        if (!Valid())
        {
            if (IsValid(Control) && Control->GetOwner()==this && !Control->IsActorBeingDestroyed()) Control->Destroy();
            if (IsTableAlive()) bAvailable=false; return;
        }
        OwnedControls.Add(Control); Control->OnEndPlay.AddUniqueDynamic(this,&ADaedalusGallerySpectrumTable::ControlEnded);
        if (!Control->ConfigureTable(this,Action,Router) || !Valid()) { if (IsTableAlive()) bAvailable=false; return; }
        Control->FinishSpawning(World);
        if (!Valid() || !Control->HasActorBegunPlay()) { if (IsTableAlive()) bAvailable=false; return; }
        Control->AttachToActor(this,FAttachmentTransformRules::KeepWorldTransform);
        if (!Valid() || !Control->GetActorTransform().Equals(World,0.01)) { if (IsTableAlive()) bAvailable=false; return; }
    }
    if (IsTableAlive() && !ToolsReady()) bAvailable=false;
}
void ADaedalusGallerySpectrumTable::BeginPlay()
{
    bEnding=false; ++Epoch; Super::BeginPlay(); if (!IsTableAlive()) return;
    if (GetWorld()->GetNetMode()!=NM_Standalone || !ViewsReady() || !Run.Begin())
    { bAvailable=false; Notice=TEXT("This local Spectrum Table is unavailable here. Nothing collides or changes other world objects."); Refresh(); return; }
    TGuardValue<bool> Preparing(bBusy,true); SpawnControls(); if (!IsTableAlive()) return;
    Notice=bAvailable?TEXT("Route six numbered R/G/B beams to match each window's WANT and NOW colour names. Different channels combine; two reds remain red. Hint finds a shortest route. Pictures keep separate history."):
        TEXT("The tool set could not be prepared. All picture states are kept; this table is unavailable.");
    Refresh();
}
void ADaedalusGallerySpectrumTable::ControlEnded(AActor* Actor,EEndPlayReason::Type)
{
    if (!IsTableAlive() || !Actor || Actor->GetOwner()!=this) return;
    bool Found=false; for (const auto& Control:OwnedControls) if (Control.Get()==Actor) { Found=true; break; } if (!Found) return;
    bAvailable=false; bRestartArmed=false; Notice=TEXT("A table tool is unavailable. Every picture's routes and history are kept; controls are inactive.");
    if (!bBusy && !bNotifying) Refresh();
}
void ADaedalusGallerySpectrumTable::ReleaseControls()
{
    const auto Controls=OwnedControls; OwnedControls.Reset();
    for (const auto& Control:Controls) if (IsValid(Control)) Control->OnEndPlay.RemoveDynamic(this,&ADaedalusGallerySpectrumTable::ControlEnded);
    for (const auto& Control:Controls) if (IsValid(Control) && Control->GetOwner()==this && !Control->IsActorBeingDestroyed()) Control->Destroy();
}
void ADaedalusGallerySpectrumTable::EndPlay(const EEndPlayReason::Type Reason)
{ bEnding=true; ++Epoch; ReleaseControls(); OnViewChanged.Broadcast(this); Super::EndPlay(Reason); }

ADaedalusSpectrumControl::ADaedalusSpectrumControl()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    ControlRoot=CreateDefaultSubobject<USceneComponent>(TEXT("SpectrumControlRoot")); RootComponent=ControlRoot;
    Body->SetupAttachment(ControlRoot); Glow->SetupAttachment(ControlRoot); Glow->SetIntensity(0.f); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeScale3D(FVector(0.35,0.5,0.25)); Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Label=CreateDefaultSubobject<UTextRenderComponent>(TEXT("SpectrumControlLabel")); Label->SetupAttachment(ControlRoot);
    Label->SetRelativeLocation(FVector(15,0,70)); Label->SetWorldSize(10.f); Label->SetHorizontalAlignment(EHTA_Center);
    Label->SetVerticalAlignment(EVRTA_TextCenter); Label->SetTextRenderColor(FColor(25,40,60)); Label->SetText(FText::FromString(TEXT("--")));
}
void ADaedalusSpectrumControl::BeginPlay()
{ bEnding=false; Super::BeginPlay(); if (!bEnding && !IsActorBeingDestroyed()) ConfigureTable(Table,Action,Router); }
void ADaedalusSpectrumControl::UnbindTable()
{
    if (auto* Previous=ObservedTable.Get()) Previous->OnViewChanged.RemoveDynamic(this,&ADaedalusSpectrumControl::TableViewChanged);
    ObservedTable.Reset();
}
bool ADaedalusSpectrumControl::ConfigureTable(ADaedalusGallerySpectrumTable* NewTable,EDaedalusSpectrumAction NewAction,int32 NewRouter)
{
    if (!IsInGameThread() || bEnding || IsActorBeingDestroyed() || !DaedalusSpectrumLocal::ValidAction(NewAction,NewRouter) ||
        (NewTable && (!IsValid(NewTable) || NewTable->IsActorBeingDestroyed() || NewTable->GetWorld()!=GetWorld()))) return false;
    UnbindTable(); Table=NewTable; Action=NewAction; Router=NewRouter;
    if (IsValid(Table)) { ObservedTable=Table; Table->OnViewChanged.AddUniqueDynamic(this,&ADaedalusSpectrumControl::TableViewChanged); }
    RefreshLabel(); return true;
}
bool ADaedalusSpectrumControl::Matches(const ADaedalusGallerySpectrumTable* Target,EDaedalusSpectrumAction ExpectedAction,int32 ExpectedRouter) const
{ return !bEnding && Table.Get()==Target && Action==ExpectedAction && Router==ExpectedRouter && IsValid(Label) && Label->GetOwner()==this && Label->IsRegistered(); }
void ADaedalusSpectrumControl::RefreshLabel()
{
    if (!bEnding && IsValid(Label)) Label->SetText(FText::FromString(IsValid(Table) && Table->GetWorld()==GetWorld()?Table->ControlLabel(Action,Router):TEXT("--")));
}
void ADaedalusSpectrumControl::TableViewChanged(ADaedalusGallerySpectrumTable* ChangedTable)
{
    if (bEnding || ChangedTable!=Table.Get()) return;
    if (!ChangedTable->IsTableAlive()) { UnbindTable(); Table=nullptr; }
    RefreshLabel();
}
void ADaedalusSpectrumControl::EndPlay(const EEndPlayReason::Type Reason)
{ bEnding=true; UnbindTable(); Table=nullptr; Super::EndPlay(Reason); }
FString ADaedalusSpectrumControl::Prompt(const ADaedalusHero*) const
{ return !bEnding && HasActorBegunPlay() && IsValid(Table) && Table->GetWorld()==GetWorld()?Table->ControlPrompt(Action,Router):TEXT("Spectrum tool is not connected"); }
bool ADaedalusSpectrumControl::Use(ADaedalusHero* Hero)
{ return !bEnding && IsValid(Table) && Table->GetWorld()==GetWorld() && Table->Operate(Hero,this,Action,Router); }
