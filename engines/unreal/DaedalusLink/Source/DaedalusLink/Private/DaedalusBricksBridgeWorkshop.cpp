// SPDX-License-Identifier: MIT
#include "DaedalusBricksBridgeWorkshop.h"
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

namespace DaedalusBridgeLocal
{
    FVector ControlAt(int32 Index)
    { return Index<12?FVector(320+120*(Index/4),180-120*(Index%4),65):FVector(720,240-120*(Index-12),65); }
    EDaedalusBridgeAction ActionAt(int32 Index)
    { return Index<12?EDaedalusBridgeAction::Link:static_cast<EDaedalusBridgeAction>(Index-11); }
    bool ValidAction(EDaedalusBridgeAction Action,int32 Link)
    { return Action==EDaedalusBridgeAction::Link?Link>=0 && Link<12:Link==-1 && static_cast<uint8>(Action)>=1 && static_cast<uint8>(Action)<=5; }
    FVector PadAt(int32 Rule,int32 Pad)
    {
        const auto& Blueprint=daedalus::brickbridge::Blueprints[Rule];
        return FVector(-75,250-100*Blueprint.Columns[Pad%3],35+100*Blueprint.Rows[Pad/3]);
    }
    bool LocalReach(const ADaedalusHero* Hero,const AActor* Tool)
    {
        if (!IsInGameThread() || !IsValid(Hero) || Hero->IsActorBeingDestroyed() || !Hero->HasActorBegunPlay() || !IsValid(Tool) ||
            Tool->IsActorBeingDestroyed() || !Tool->HasActorBegunPlay() || !Tool->GetWorld() || Hero->GetWorld()!=Tool->GetWorld() ||
            Tool->GetWorld()->GetNetMode()!=NM_Standalone || !Hero->IsLocallyControlled() || !FMath::IsFinite(Hero->InteractReach) || Hero->InteractReach<=0.f) return false;
        const auto* Player=Cast<APlayerController>(Hero->GetController());
        if (!IsValid(Player) || Player->IsActorBeingDestroyed() || Player->GetWorld()!=Tool->GetWorld() || !Player->IsLocalController() ||
            Player->GetPawn()!=Hero || !IsValid(Player->GetLocalPlayer())) return false;
        const double D=FVector::DistSquared(Hero->GetActorLocation(),Tool->GetActorLocation());
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
    struct Ink
    {
        TArray<FVector> Vertices; TArray<int32> Triangles; TArray<FLinearColor> Colours;
        void Triangle(FVector A,FVector B,FVector C,FLinearColor Colour)
        { const int32 At=Vertices.Num(); Vertices.Append({A,B,C}); Triangles.Append({At,At+1,At+2}); Colours.Append({Colour,Colour,Colour}); }
        void Square(FVector At,double Y,double Z,FLinearColor Colour)
        {
            Triangle(At+FVector(0,-Y,-Z),At+FVector(0,Y,-Z),At+FVector(0,Y,Z),Colour);
            Triangle(At+FVector(0,-Y,-Z),At+FVector(0,Y,Z),At+FVector(0,-Y,Z),Colour);
        }
        void Line(FVector A,FVector B,double Width,FLinearColor Colour)
        {
            const FVector D=(B-A).GetSafeNormal(),S(0,-D.Z*Width,D.Y*Width);
            Triangle(A-S,B-S,B+S,Colour); Triangle(A-S,B+S,A+S,Colour);
        }
        void Stud(FVector At,double Radius,FLinearColor Colour)
        {
            for (int32 I=0;I<12;++I)
            {
                const double A=2*PI*I/12,B=2*PI*(I+1)/12;
                Triangle(At,At+FVector(0,FMath::Cos(A)*Radius,FMath::Sin(A)*Radius),At+FVector(0,FMath::Cos(B)*Radius,FMath::Sin(B)*Radius),Colour);
            }
        }
    };
}

ADaedalusBricksBridgeWorkshop::ADaedalusBricksBridgeWorkshop()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    WorkshopRoot=CreateDefaultSubobject<USceneComponent>(TEXT("BridgeWorkshopRoot")); RootComponent=WorkshopRoot;
    Body->SetupAttachment(WorkshopRoot); Glow->SetupAttachment(WorkshopRoot); Glow->SetIntensity(0.f); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Engine/EngineDebugMaterials/VertexColorMaterial.VertexColorMaterial")); InkMaterial=Material.Object;
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeLocation(FVector(-90,0,300)); Body->SetRelativeScale3D(FVector(0.2,6.5,6)); Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Diagram=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("StuddedBridgeBlueprint")); Diagram->SetupAttachment(WorkshopRoot);
    Diagram->SetCollisionEnabled(ECollisionEnabled::NoCollision); Diagram->SetCastShadow(false);
    Title=CreateDefaultSubobject<UTextRenderComponent>(TEXT("BridgeWorkshopTitle")); Title->SetupAttachment(WorkshopRoot);
    Title->SetRelativeLocation(FVector(-60,0,655)); Title->SetWorldSize(23.f); Title->SetHorizontalAlignment(EHTA_Center); Title->SetTextRenderColor(FColor(25,40,60));
    Readout=CreateDefaultSubobject<UTextRenderComponent>(TEXT("BridgeWorkshopReadout")); Readout->SetupAttachment(WorkshopRoot);
    Readout->SetRelativeLocation(FVector(200,520,500)); Readout->SetWorldSize(11.f); Readout->SetHorizontalAlignment(EHTA_Center);
    Readout->SetVerticalAlignment(EVRTA_TextTop); Readout->SetTextRenderColor(FColor(25,40,60));
    for (int32 I=0;I<9;++I)
    {
        auto* Label=CreateDefaultSubobject<UTextRenderComponent>(*FString::Printf(TEXT("BridgePad%d"),I)); Label->SetupAttachment(WorkshopRoot);
        Label->SetWorldSize(11.f); Label->SetHorizontalAlignment(EHTA_Center); Label->SetVerticalAlignment(EVRTA_TextCenter);
        Label->SetTextRenderColor(FColor(25,40,60)); PadLabels.Add(Label);
    }
    for (int32 I=0;I<12;++I)
    {
        auto* Label=CreateDefaultSubobject<UTextRenderComponent>(*FString::Printf(TEXT("BridgeSpan%d"),I)); Label->SetupAttachment(WorkshopRoot);
        Label->SetWorldSize(10.f); Label->SetHorizontalAlignment(EHTA_Center); Label->SetVerticalAlignment(EVRTA_TextCenter);
        Label->SetTextRenderColor(FColor(25,40,60)); SpanLabels.Add(Label);
    }
}
bool ADaedalusBricksBridgeWorkshop::IsWorkshopAlive() const
{ return IsInGameThread() && !bEnding && !IsActorBeingDestroyed() && HasActorBegunPlay() && GetWorld(); }
bool ADaedalusBricksBridgeWorkshop::ViewsReady() const
{
    if (!IsWorkshopAlive() || !InkMaterial || !IsValid(Diagram) || Diagram->GetOwner()!=this || !Diagram->IsRegistered() ||
        !IsValid(Readout) || Readout->GetOwner()!=this || !Readout->IsRegistered() || !IsValid(Title) || Title->GetOwner()!=this || !Title->IsRegistered() ||
        PadLabels.Num()!=9 || SpanLabels.Num()!=12) return false;
    for (const auto& Label:PadLabels) if (!IsValid(Label) || Label->GetOwner()!=this || !Label->IsRegistered()) return false;
    for (const auto& Label:SpanLabels) if (!IsValid(Label) || Label->GetOwner()!=this || !Label->IsRegistered()) return false;
    return true;
}
bool ADaedalusBricksBridgeWorkshop::ToolsReady() const
{
    if (!IsWorkshopAlive() || OwnedControls.Num()!=17) return false;
    for (int32 I=0;I<17;++I)
    {
        const auto* Control=OwnedControls[I].Get();
        if (!IsValid(Control) || Control->IsActorBeingDestroyed() || !Control->HasActorBegunPlay() || Control->GetOwner()!=this || Control->GetWorld()!=GetWorld() ||
            Control->GetActorEnableCollision() || !Control->Matches(this,DaedalusBridgeLocal::ActionAt(I),I<12?I:-1) ||
            !Control->GetActorTransform().Equals(FTransform(DaedalusBridgeLocal::ControlAt(I))*GetActorTransform(),0.01)) return false;
    }
    return true;
}
bool ADaedalusBricksBridgeWorkshop::IsCurrentComplete() const
{ daedalus::brickbridge::Evaluation View; return Run.View(View) && View.Complete; }
FString ADaedalusBricksBridgeWorkshop::Prompt(const ADaedalusHero*) const
{ return IsWorkshopAlive() && Run.Active() && bAvailable?TEXT("E / X: Hint for this bridge blueprint"):TEXT("Bridge workshop is unavailable"); }
bool ADaedalusBricksBridgeWorkshop::Use(ADaedalusHero* Hero)
{ return Operate(Hero,this,EDaedalusBridgeAction::Hint); }

void ADaedalusBricksBridgeWorkshop::DrawBlueprint()
{
    if (!ViewsReady() || !Run.Active()) return;
    daedalus::brickbridge::Evaluation View; if (!Run.View(View)) return;
    DaedalusBridgeLocal::Ink Ink; const int32 Rule=Run.CurrentRule();
    for (int32 I=0;I<12;++I)
    {
        const auto& Span=daedalus::brickbridge::Links[I]; const FVector A=DaedalusBridgeLocal::PadAt(Rule,Span.From),B=DaedalusBridgeLocal::PadAt(Rule,Span.To),Mid=(A+B)*0.5;
        const bool Allowed=(daedalus::brickbridge::Blueprints[Rule].AllowedMask&(1<<I))!=0,Selected=(Run.Mask()&(1<<I))!=0;
        if (Allowed)
        {
            Ink.Line(A,B,Selected?6:1.4,Selected?FLinearColor(0.08f,0.65f,0.38f):FLinearColor(0.5f,0.58f,0.65f));
            if (Selected) for (int32 Mark=1;Mark<daedalus::brickbridge::LinkLength(Rule,I);++Mark)
            {
                const FVector P=FMath::Lerp(A,B,static_cast<double>(Mark)/daedalus::brickbridge::LinkLength(Rule,I))+FVector(0.4,0,0);
                Ink.Stud(P,2.2,FLinearColor(0.85f,0.97f,0.9f));
            }
        }
        else
        {
            Ink.Line(Mid+FVector(0,-10,-10),Mid+FVector(0,10,10),2,FLinearColor(0.3f,0.35f,0.4f));
            Ink.Line(Mid+FVector(0,-10,10),Mid+FVector(0,10,-10),2,FLinearColor(0.3f,0.35f,0.4f));
        }
        if (bHintVisible && ShownHint.LinkIndex==I) Ink.Line(A+FVector(1,0,0),B+FVector(1,0,0),2,FLinearColor(1,0.65f,0.05f));
        SpanLabels[I]->SetRelativeLocation(Mid+FVector(10,Span.From%3==Span.To%3?38:0,Span.From/3==Span.To/3?22:0));
        if (!ViewsReady()) return;
        SpanLabels[I]->SetText(FText::FromString(Allowed?FString::Printf(TEXT("%d / %d / %s"),I+1,daedalus::brickbridge::LinkLength(Rule,I),Selected?TEXT("IN"):TEXT("OUT")):FString::Printf(TEXT("%d / CLOSED"),I+1)));
        if (!ViewsReady()) return;
    }
    for (int32 I=0;I<9;++I)
    {
        const FVector At=DaedalusBridgeLocal::PadAt(Rule,I)+FVector(2,0,0);
        Ink.Square(At,22,22,FLinearColor(0.04f,0.1f,0.16f));
        Ink.Square(At+FVector(0.3,0,0),19,19,View.LinkedToHome[I]?FLinearColor(0.15f,0.75f,0.6f):FLinearColor(0.18f,0.5f,0.95f));
        for (int32 Y=-1;Y<=1;Y+=2) for (int32 Z=-1;Z<=1;Z+=2) Ink.Stud(At+FVector(0.7,Y*8,Z*8),3,FLinearColor(0.8f,0.94f,1));
        PadLabels[I]->SetRelativeLocation(At+FVector(12,0,-30)); if (!ViewsReady()) return;
        PadLabels[I]->SetText(FText::FromString(FString::Printf(TEXT("%d %s"),I+1,I==0?TEXT("HOME"):View.LinkedToHome[I]?TEXT("LINKED"):TEXT("PAD"))));
        if (!ViewsReady()) return;
    }
    TArray<FVector> Normals; Normals.Init(FVector(1,0,0),Ink.Vertices.Num()); TArray<FVector2D> UV; UV.Init(FVector2D::ZeroVector,Ink.Vertices.Num()); TArray<FProcMeshTangent> Tangents;
    Diagram->CreateMeshSection_LinearColor(0,Ink.Vertices,Ink.Triangles,Normals,UV,Ink.Colours,Tangents,false);
    if (ViewsReady()) Diagram->SetMaterial(0,InkMaterial);
}

void ADaedalusBricksBridgeWorkshop::Refresh(int32 NewlyStudied)
{
    if (!IsWorkshopAlive() || bNotifying) return;
    FString Text;
    if (Run.Active())
    {
        daedalus::brickbridge::Evaluation View; Run.View(View);
        Text=FString::Printf(TEXT("BLUEPRINT %d / 3: %s\nHOME LINKS %d / 9 PADS\nBeam length %d / %d units\nUndo %u / Redo %u\n%d blueprints finished this visit\n"),Run.CurrentRule()+1,
            UTF8_TO_TCHAR(daedalus::brickbridge::Blueprints[Run.CurrentRule()].Name),View.PadsConnected,View.UsedLength,daedalus::brickbridge::LengthLimit(Run.CurrentRule()),
            static_cast<unsigned>(Run.UndoCount()),static_cast<unsigned>(Run.RedoCount()),Run.CompletedCount());
        if (Run.EverCompleted(Run.CurrentRule()) && !View.Complete) Text+=TEXT("Finished before; this version is still being built.\n");
        if (ViewsReady())
        {
            Title->SetText(FText::FromString(FString(TEXT("BRIDGE WORKSHOP / "))+UTF8_TO_TCHAR(daedalus::brickbridge::Blueprints[Run.CurrentRule()].Name)));
            if (!IsWorkshopAlive()) return; DrawBlueprint();
        }
    }
    Text+=Notice; if (!IsWorkshopAlive()) return;
    if (IsValid(Readout) && Readout->GetOwner()==this) Readout->SetText(FText::FromString(DaedalusBridgeLocal::Wrap(Text)));
    if (!IsWorkshopAlive()) return;
    TGuardValue<bool> Notification(bNotifying,true); OnViewChanged.Broadcast(this);
    if (!IsWorkshopAlive()) return;
    if (NewlyStudied>=0) OnBlueprintStudied.Broadcast(this,NewlyStudied); // No gameplay writes after event.
}
FString ADaedalusBricksBridgeWorkshop::ControlLabel(EDaedalusBridgeAction Action,int32 Link) const
{
    if (!IsWorkshopAlive() || !Run.Active()) return TEXT("--");
    FString Text;
    if (!bAvailable || !ViewsReady()) Text=TEXT("Workshop unavailable");
    else if (Action==EDaedalusBridgeAction::Link && Link>=0 && Link<12)
    {
        const auto& Span=daedalus::brickbridge::Links[Link]; const bool Allowed=(daedalus::brickbridge::Blueprints[Run.CurrentRule()].AllowedMask&(1<<Link))!=0;
        Text=Allowed?FString::Printf(TEXT("%d: PAD %d - %d\n%d units / %s"),Link+1,Span.From+1,Span.To+1,daedalus::brickbridge::LinkLength(Run.CurrentRule(),Link),
            (Run.Mask()&(1<<Link))?TEXT("IN"):TEXT("OUT")):FString::Printf(TEXT("%d / CLOSED SPAN"),Link+1);
        if (bHintVisible && ShownHint.LinkIndex==Link) Text+=ShownHint.ToSelected?TEXT("\n[HINT] ADD"):TEXT("\n[HINT] REMOVE");
    }
    else if (Action==EDaedalusBridgeAction::NextBlueprint) Text=TEXT("Next blueprint\nYour work stays");
    else if (Action==EDaedalusBridgeAction::Hint) Text=bHintVisible?TEXT("Put hint away"):TEXT("Hint / free");
    else if (Action==EDaedalusBridgeAction::Undo) Text=FString::Printf(TEXT("Undo / %u"),static_cast<unsigned>(Run.UndoCount()));
    else if (Action==EDaedalusBridgeAction::Redo) Text=FString::Printf(TEXT("Redo / %u"),static_cast<unsigned>(Run.RedoCount()));
    else if (Action==EDaedalusBridgeAction::Restart) Text=bRestartArmed?TEXT("Confirm restart"):TEXT("Restart blueprint");
    else Text=TEXT("--");
    if (bFeedback && Action==FeedbackAction && Link==FeedbackLink) Text+=TEXT("\n")+DaedalusBridgeLocal::Wrap(Notice,36,3);
    return Text;
}
FString ADaedalusBricksBridgeWorkshop::ControlPrompt(EDaedalusBridgeAction Action,int32 Link) const
{
    if (!IsWorkshopAlive() || !Run.Active() || !bAvailable || !ViewsReady() || !DaedalusBridgeLocal::ValidAction(Action,Link)) return TEXT("Bridge tool is unavailable");
    if (Action==EDaedalusBridgeAction::Link)
    {
        if (!(daedalus::brickbridge::Blueprints[Run.CurrentRule()].AllowedMask&(1<<Link))) return TEXT("This span is closed in this blueprint");
        const auto& Span=daedalus::brickbridge::Links[Link];
        return FString::Printf(TEXT("E / X: %s span %d (pads %d - %d), %d length units"),(Run.Mask()&(1<<Link))?TEXT("Remove"):TEXT("Add"),Link+1,
            Span.From+1,Span.To+1,daedalus::brickbridge::LinkLength(Run.CurrentRule(),Link));
    }
    if (Action==EDaedalusBridgeAction::NextBlueprint) return TEXT("E / X: Next blueprint; each plan keeps its beams and history");
    if (Action==EDaedalusBridgeAction::Hint) return TEXT("E / X: A free shortest-change hint; removing a beam can make room for a better route");
    if (Action==EDaedalusBridgeAction::Undo) return TEXT("E / X: Undo one beam edit in this blueprint");
    if (Action==EDaedalusBridgeAction::Redo) return TEXT("E / X: Redo one beam edit in this blueprint");
    return bRestartArmed?TEXT("E / X: Confirm restart of this blueprint only"):TEXT("E / X: Restart this blueprint - confirm twice");
}
bool ADaedalusBricksBridgeWorkshop::Operate(ADaedalusHero* Hero,const AActor* Tool,EDaedalusBridgeAction Action,int32 Link)
{
    if (!IsWorkshopAlive() || GetWorld()->GetNetMode()!=NM_Standalone || !Run.Active() || bBusy || bNotifying ||
        !DaedalusBridgeLocal::ValidAction(Action,Link) || !DaedalusBridgeLocal::LocalReach(Hero,Tool)) return false;
    if (!IsWorkshopAlive() || !IsValid(Tool) || Tool->IsActorBeingDestroyed() || !Tool->HasActorBegunPlay() || Tool->GetWorld()!=GetWorld()) return false;
    if (Tool==this) { if (Action!=EDaedalusBridgeAction::Hint || Link!=-1) return false; }
    else
    {
        const int32 Slot=Action==EDaedalusBridgeAction::Link?Link:11+static_cast<int32>(Action);
        const auto* Control=Cast<ADaedalusBridgeControl>(Tool);
        if (!Control || !OwnedControls.IsValidIndex(Slot) || OwnedControls[Slot].Get()!=Control || Control->GetOwner()!=this ||
            !Control->Matches(this,Action,Link) || !Control->GetActorTransform().Equals(FTransform(DaedalusBridgeLocal::ControlAt(Slot))*GetActorTransform(),0.01)) return false;
    }
    TGuardValue<bool> Busy(bBusy,true); bFeedback=true; FeedbackAction=Action; FeedbackLink=Link;
    if (!bAvailable || !ViewsReady() || !ToolsReady())
    { bAvailable=false; Notice=TEXT("A blueprint view or tool is unavailable. Your beams and history stay in place."); Refresh(); return false; }
    if (Action!=EDaedalusBridgeAction::Restart) bRestartArmed=false;
    if (Action==EDaedalusBridgeAction::Hint)
    {
        if (bHintVisible) { bHintVisible=false; Notice=TEXT("Hint put away. Connect all nine pads within the length allowance."); }
        else if (Run.Hint(ShownHint))
        {
            bHintVisible=true;
            Notice=FString::Printf(TEXT("Try %s span %d. A complete network is %d edits away, including this step. Removing a beam first can make room."),
                ShownHint.ToSelected?TEXT("adding"):TEXT("removing"),ShownHint.LinkIndex+1,ShownHint.Remaining);
        }
        else Notice=TEXT("All nine pads are connected within the allowance. Try another blueprint, or keep exploring with Undo / Redo.");
        Refresh(); return IsWorkshopAlive();
    }
    if (Action==EDaedalusBridgeAction::Restart && !bRestartArmed)
    {
        bRestartArmed=true; Notice=TEXT("Use Restart once more to remove this plan's beams and history. Other plans and finished-blueprint notes stay. Any other tool cancels.");
        Refresh(); return false;
    }
    std::array<bool,3> Before{}; for (int32 I=0;I<3;++I) Before[I]=Run.EverCompleted(I);
    bool Changed=false;
    if (Action==EDaedalusBridgeAction::Link)
    {
        const auto Result=Run.Toggle(Link); Changed=Result==daedalus::brickbridge::Change::Changed;
        if (!Changed)
        {
            Notice=Result==daedalus::brickbridge::Change::OverLength?TEXT("That beam would exceed the length allowance. Remove a beam or use Undo; Hint can suggest a route."):
                Result==daedalus::brickbridge::Change::Closed?TEXT("This span is closed on this blueprint. Your beams and history are kept."):TEXT("That beam edit is unavailable. Your blueprint is unchanged.");
            Refresh(); return false;
        }
    }
    else if (Action==EDaedalusBridgeAction::NextBlueprint) Changed=Run.SelectRule((Run.CurrentRule()+1)%3);
    else if (Action==EDaedalusBridgeAction::Undo) Changed=Run.Undo();
    else if (Action==EDaedalusBridgeAction::Redo) Changed=Run.Redo();
    else if (Action==EDaedalusBridgeAction::Restart) { Changed=Run.Restart(); bRestartArmed=false; }
    if (!Changed)
    {
        Notice=Action==EDaedalusBridgeAction::Restart?TEXT("This blueprint is already empty with no history. Nothing changed."):TEXT("There is no beam edit in that history direction.");
        Refresh(); return false;
    }
    bHintVisible=false; daedalus::brickbridge::Evaluation View; Run.View(View);
    const int32 Rule=Run.CurrentRule(); const int32 NewlyStudied=!Before[Rule] && Run.EverCompleted(Rule)?Rule:-1;
    if (View.Complete) Notice=TEXT("All nine pads are linked within the length allowance! You can study another plan, or Undo and try a different connection.");
    else if (Action==EDaedalusBridgeAction::NextBlueprint) Notice=TEXT("Blueprint changed. This plan kept its beams, Undo and Redo. Closed spans have an X; labels show span / length / IN or OUT.");
    else if (Action==EDaedalusBridgeAction::Restart) Notice=TEXT("Only this plan restarted. Other beams and finished-blueprint notes stay.");
    else Notice=FString::Printf(TEXT("Home reaches %d of nine pads. Use beam lengths wisely; loops can use room without reaching a new pad. Undo, Redo and Hint are free."),View.PadsConnected);
    Refresh(NewlyStudied); return IsWorkshopAlive();
}

void ADaedalusBricksBridgeWorkshop::SpawnControls()
{
    if (!IsWorkshopAlive() || bToolsAttempted) return;
    bToolsAttempted=true; const uint64 StartEpoch=Epoch; const TWeakObjectPtr<ADaedalusBricksBridgeWorkshop> Self(this);
    for (int32 I=0;I<17 && IsWorkshopAlive();++I)
    {
        const auto Action=DaedalusBridgeLocal::ActionAt(I); const int32 Link=I<12?I:-1;
        const FTransform Expected=FTransform(DaedalusBridgeLocal::ControlAt(I))*GetActorTransform();
        TWeakObjectPtr<ADaedalusBridgeControl> Staged;
        FActorSpawnParameters Parameters; Parameters.Owner=this; Parameters.ObjectFlags=RF_Transient|RF_DuplicateTransient; Parameters.bDeferConstruction=true;
        Parameters.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        Parameters.CustomPreSpawnInitialization=[Self,StartEpoch,I,&Staged](AActor* Actor)
        {
            Actor->SetActorEnableCollision(false); auto* Workshop=Self.Get(); auto* Control=Cast<ADaedalusBridgeControl>(Actor); Staged=Control;
            if (!Workshop || !Workshop->IsWorkshopAlive() || Workshop->Epoch!=StartEpoch || !Control || Workshop->OwnedControls.Num()!=I) return;
            Workshop->OwnedControls.Add(Control); Control->OnEndPlay.AddUniqueDynamic(Workshop,&ADaedalusBricksBridgeWorkshop::ControlEnded);
        };
        auto* Control=GetWorld()->SpawnActor<ADaedalusBridgeControl>(ADaedalusBridgeControl::StaticClass(),Expected,Parameters);
        auto Valid=[&]()
        { return IsWorkshopAlive() && Epoch==StartEpoch && IsValid(Control) && !Control->IsActorBeingDestroyed() && Staged.Get()==Control &&
            OwnedControls.IsValidIndex(I) && OwnedControls[I].Get()==Control && Control->GetOwner()==this && Control->GetWorld()==GetWorld(); };
        auto Fail=[&]()
        {
            TArray<TWeakObjectPtr<ADaedalusBridgeControl>> Effects; if (IsValid(Control)) Effects.AddUnique(TWeakObjectPtr<ADaedalusBridgeControl>(Control));
            if (Staged.IsValid()) Effects.AddUnique(Staged);
            auto Earlier=[&](const ADaedalusBridgeControl* Actor)
            { for (int32 J=0;J<I && J<OwnedControls.Num();++J) if (OwnedControls[J].Get()==Actor) return true; return false; };
            for (const auto& Effect:Effects) if (auto* Actor=Effect.Get()) if (!Earlier(Actor)) Actor->OnEndPlay.RemoveDynamic(this,&ADaedalusBricksBridgeWorkshop::ControlEnded);
            for (const auto& Effect:Effects) if (auto* Actor=Effect.Get())
                if (!Earlier(Actor) && !Actor->IsActorBeingDestroyed() && Actor->GetOwner()==this) Actor->Destroy();
            if (IsWorkshopAlive()) bAvailable=false;
        };
        if (!Valid() || !Control->ConfigureWorkshop(this,Action,Link) || !Valid()) { Fail(); return; }
        Control->FinishSpawning(Expected);
        if (!Valid() || !Control->HasActorBegunPlay()) { Fail(); return; }
        Control->AttachToActor(this,FAttachmentTransformRules::KeepWorldTransform);
        if (!Valid() || !Control->GetActorTransform().Equals(Expected,0.01)) { Fail(); return; }
    }
    if (IsWorkshopAlive() && !ToolsReady()) bAvailable=false;
}
void ADaedalusBricksBridgeWorkshop::BeginPlay()
{
    bEnding=false; ++Epoch; Super::BeginPlay(); if (!IsWorkshopAlive()) return;
    if (GetWorld()->GetNetMode()!=NM_Standalone || !ViewsReady() || !Run.Begin())
    { bAvailable=false; Notice=TEXT("This bridge workshop is unavailable here."); Refresh(); return; }
    TGuardValue<bool> Preparing(bBusy,true); SpawnControls(); if (!IsWorkshopAlive()) return;
    Notice=bAvailable?TEXT("Connect all nine pads to HOME within the beam-length allowance. Switch spans IN / OUT; each label gives its length. X means closed. Three plans keep separate work; Hint and Undo help."):
        TEXT("Some workshop tools could not be prepared. Your blueprint is kept; the controls are unavailable.");
    Refresh();
}
void ADaedalusBricksBridgeWorkshop::ControlEnded(AActor* Actor,EEndPlayReason::Type)
{
    if (!IsWorkshopAlive() || !Actor) return;
    bool Found=false; for (const auto& Control:OwnedControls) if (Control.Get()==Actor) { Found=true; break; } if (!Found) return;
    bAvailable=false; bRestartArmed=false; Notice=TEXT("A workshop tool is unavailable. Every blueprint's beams and history stay in place.");
    if (!bBusy && !bNotifying) Refresh();
}
void ADaedalusBricksBridgeWorkshop::ReleaseControls()
{
    const auto Controls=OwnedControls; OwnedControls.Reset();
    for (const auto& Control:Controls) if (IsValid(Control)) Control->OnEndPlay.RemoveDynamic(this,&ADaedalusBricksBridgeWorkshop::ControlEnded);
    for (const auto& Control:Controls) if (IsValid(Control) && !Control->IsActorBeingDestroyed() && Control->GetOwner()==this) Control->Destroy();
}
void ADaedalusBricksBridgeWorkshop::EndPlay(const EEndPlayReason::Type Reason)
{ bEnding=true; ++Epoch; ReleaseControls(); OnViewChanged.Broadcast(this); Super::EndPlay(Reason); }

ADaedalusBridgeControl::ADaedalusBridgeControl()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    ControlRoot=CreateDefaultSubobject<USceneComponent>(TEXT("BridgeControlRoot")); RootComponent=ControlRoot;
    Body->SetupAttachment(ControlRoot); Glow->SetupAttachment(ControlRoot); Glow->SetIntensity(0.f); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeScale3D(FVector(0.35,0.5,0.25)); Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Label=CreateDefaultSubobject<UTextRenderComponent>(TEXT("BridgeControlLabel")); Label->SetupAttachment(ControlRoot);
    Label->SetRelativeLocation(FVector(15,0,70)); Label->SetWorldSize(9.f); Label->SetHorizontalAlignment(EHTA_Center);
    Label->SetVerticalAlignment(EVRTA_TextCenter); Label->SetTextRenderColor(FColor(25,40,60));
}
void ADaedalusBridgeControl::BeginPlay()
{ bEnding=false; Super::BeginPlay(); if (!bEnding && !IsActorBeingDestroyed()) ConfigureWorkshop(Workshop,Action,Link); }
void ADaedalusBridgeControl::UnbindWorkshop()
{
    if (auto* Previous=ObservedWorkshop.Get()) Previous->OnViewChanged.RemoveDynamic(this,&ADaedalusBridgeControl::WorkshopViewChanged);
    ObservedWorkshop.Reset();
}
bool ADaedalusBridgeControl::ConfigureWorkshop(ADaedalusBricksBridgeWorkshop* NewWorkshop,EDaedalusBridgeAction NewAction,int32 NewLink)
{
    if (!IsInGameThread() || bEnding || IsActorBeingDestroyed() || !DaedalusBridgeLocal::ValidAction(NewAction,NewLink) ||
        !IsValid(Label) || Label->GetOwner()!=this || (NewWorkshop && (!IsValid(NewWorkshop) || NewWorkshop->IsActorBeingDestroyed() || NewWorkshop->GetWorld()!=GetWorld()))) return false;
    UnbindWorkshop(); Workshop=NewWorkshop; Action=NewAction; Link=NewLink;
    if (IsValid(Workshop)) { ObservedWorkshop=Workshop; Workshop->OnViewChanged.AddUniqueDynamic(this,&ADaedalusBridgeControl::WorkshopViewChanged); }
    RefreshLabel(); return true;
}
bool ADaedalusBridgeControl::Matches(const ADaedalusBricksBridgeWorkshop* Target,EDaedalusBridgeAction ExpectedAction,int32 ExpectedLink) const
{ return !bEnding && Workshop.Get()==Target && Action==ExpectedAction && Link==ExpectedLink && IsValid(Label) && Label->GetOwner()==this && Label->IsRegistered(); }
void ADaedalusBridgeControl::RefreshLabel()
{
    if (!bEnding && IsValid(Label) && Label->GetOwner()==this)
        Label->SetText(FText::FromString(IsValid(Workshop) && Workshop->GetWorld()==GetWorld()?Workshop->ControlLabel(Action,Link):TEXT("--")));
}
void ADaedalusBridgeControl::WorkshopViewChanged(ADaedalusBricksBridgeWorkshop* ChangedWorkshop)
{
    if (bEnding || ChangedWorkshop!=Workshop.Get()) return;
    if (!ChangedWorkshop->IsWorkshopAlive()) { UnbindWorkshop(); Workshop=nullptr; }
    RefreshLabel();
}
void ADaedalusBridgeControl::EndPlay(const EEndPlayReason::Type Reason)
{ bEnding=true; UnbindWorkshop(); Workshop=nullptr; Super::EndPlay(Reason); }
FString ADaedalusBridgeControl::Prompt(const ADaedalusHero*) const
{ return !bEnding && HasActorBegunPlay() && IsValid(Workshop) && Workshop->GetWorld()==GetWorld()?Workshop->ControlPrompt(Action,Link):TEXT("Bridge tool is not connected"); }
bool ADaedalusBridgeControl::Use(ADaedalusHero* Hero)
{ return !bEnding && IsValid(Workshop) && Workshop->GetWorld()==GetWorld() && Workshop->Operate(Hero,this,Action,Link); }
