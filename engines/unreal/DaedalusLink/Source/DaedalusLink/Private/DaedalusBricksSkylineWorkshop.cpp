// SPDX-License-Identifier: MIT
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

namespace DaedalusSkylineLocal
{
    FVector CellAt(int32 Cell) { return FVector((Cell/4-1.5)*180,-(Cell%4-1.5)*180,0); }
    FVector ControlAt(int32 I) { return I<16?CellAt(I):I<21?FVector(650,240-120*(I-16),65):FVector(830,240-120*(I-21),65); }
    EDaedalusSkylineAction ActionAt(int32 I) { return I<16?EDaedalusSkylineAction::Cell:I<21?EDaedalusSkylineAction::Height:static_cast<EDaedalusSkylineAction>(I-19); }
    int32 ParameterAt(int32 I) { return I<16?I:I<21?I-16:-1; }
    int32 ControlIndex(EDaedalusSkylineAction Action,int32 Parameter)
    { return Action==EDaedalusSkylineAction::Cell?Parameter:Action==EDaedalusSkylineAction::Height?16+Parameter:19+static_cast<int32>(Action); }
    bool ValidAction(EDaedalusSkylineAction Action,int32 Parameter)
    {
        if (Action==EDaedalusSkylineAction::Cell) return Parameter>=0 && Parameter<16;
        if (Action==EDaedalusSkylineAction::Height) return Parameter>=0 && Parameter<=4;
        return Parameter==-1 && static_cast<uint8>(Action)>=2 && static_cast<uint8>(Action)<=6;
    }
    FLinearColor HeightColour(int32 Height)
    {
        static const FLinearColor Palette[]={FLinearColor(0.93f,0.96f,0.98f),FLinearColor(0.95f,0.33f,0.25f),
            FLinearColor(0.95f,0.72f,0.13f),FLinearColor(0.15f,0.68f,0.58f),FLinearColor(0.6f,0.35f,0.9f)};
        return Palette[Height];
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
        TArray<FVector> Vertices,Normals; TArray<int32> Triangles; TArray<FLinearColor> Colours;
        void Face(FVector A,FVector B,FVector C,FVector D,FVector Normal,FLinearColor Colour)
        {
            const int32 At=Vertices.Num(); Vertices.Append({A,B,C,D}); Triangles.Append({At,At+1,At+2,At,At+2,At+3});
            Normals.Append({Normal,Normal,Normal,Normal}); Colours.Append({Colour,Colour,Colour,Colour});
        }
        void Box(FVector P,FVector E,FLinearColor C)
        {
            const double L=P.X-E.X,R=P.X+E.X,F=P.Y-E.Y,B=P.Y+E.Y,D=P.Z-E.Z,U=P.Z+E.Z;
            Face({R,F,D},{R,B,D},{R,B,U},{R,F,U},{1,0,0},C*0.92f); Face({L,B,D},{L,F,D},{L,F,U},{L,B,U},{-1,0,0},C*0.82f);
            Face({R,B,D},{L,B,D},{L,B,U},{R,B,U},{0,1,0},C*0.88f); Face({L,F,D},{R,F,D},{R,F,U},{L,F,U},{0,-1,0},C*0.95f);
            Face({L,F,U},{R,F,U},{R,B,U},{L,B,U},{0,0,1},C); Face({L,B,D},{R,B,D},{R,F,D},{L,F,D},{0,0,-1},C*0.75f);
        }
        void Outline(FVector P,double Radius,FLinearColor C)
        {
            Box(P+FVector(Radius,0,0),FVector(2,Radius,0.7),C); Box(P-FVector(Radius,0,0),FVector(2,Radius,0.7),C);
            Box(P+FVector(0,Radius,0),FVector(Radius,2,0.7),C); Box(P-FVector(0,Radius,0),FVector(Radius,2,0.7),C);
        }
    };
}

ADaedalusBricksSkylineWorkshop::ADaedalusBricksSkylineWorkshop()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    WorkshopRoot=CreateDefaultSubobject<USceneComponent>(TEXT("SkylineWorkshopRoot")); RootComponent=WorkshopRoot;
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Engine/EngineDebugMaterials/VertexColorMaterial.VertexColorMaterial")); InkMaterial=Material.Object;
    Model=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("StuddedSkylineModel")); Model->SetupAttachment(WorkshopRoot);
    Model->SetCollisionEnabled(ECollisionEnabled::NoCollision); Model->SetCastShadow(false);
    Title=CreateDefaultSubobject<UTextRenderComponent>(TEXT("SkylineTitle")); Title->SetupAttachment(WorkshopRoot);
    Title->SetRelativeLocation(FVector(640,0,500)); Title->SetWorldSize(24.f); Title->SetHorizontalAlignment(EHTA_Center); Title->SetTextRenderColor(FColor(25,40,60));
    Readout=CreateDefaultSubobject<UTextRenderComponent>(TEXT("SkylineReadout")); Readout->SetupAttachment(WorkshopRoot);
    Readout->SetRelativeLocation(FVector(640,620,370)); Readout->SetWorldSize(11.f); Readout->SetHorizontalAlignment(EHTA_Center);
    Readout->SetVerticalAlignment(EVRTA_TextTop); Readout->SetTextRenderColor(FColor(25,40,60));
    for (int32 I=0;I<16;++I)
    {
        auto* Label=CreateDefaultSubobject<UTextRenderComponent>(*FString::Printf(TEXT("SkylineSideClue%d"),I)); Label->SetupAttachment(WorkshopRoot);
        const int32 Side=I/4,Line=I%4;
        Label->SetRelativeLocation(Side==0?FVector((Line-1.5)*180,430,100):Side==1?FVector((Line-1.5)*180,-430,100):Side==2?FVector(-430,-(Line-1.5)*180,100):FVector(430,-(Line-1.5)*180,100));
        Label->SetRelativeRotation(FRotator(0,Side==0?90:Side==1?-90:Side==2?180:0,0));
        Label->SetWorldSize(17.f); Label->SetHorizontalAlignment(EHTA_Center); Label->SetVerticalAlignment(EVRTA_TextCenter); ClueLabels.Add(Label);
    }
}
bool ADaedalusBricksSkylineWorkshop::IsWorkshopAlive() const
{ return IsInGameThread() && !bEnding && !IsActorBeingDestroyed() && HasActorBegunPlay() && GetWorld(); }
bool ADaedalusBricksSkylineWorkshop::ViewsReady() const
{
    if (!IsWorkshopAlive() || !InkMaterial || !IsValid(Model) || Model->GetOwner()!=this || !Model->IsRegistered() ||
        !IsValid(Readout) || Readout->GetOwner()!=this || !Readout->IsRegistered() || !IsValid(Title) || Title->GetOwner()!=this || !Title->IsRegistered() || ClueLabels.Num()!=16) return false;
    for (const auto& Label:ClueLabels) if (!IsValid(Label) || Label->GetOwner()!=this || !Label->IsRegistered()) return false;
    return true;
}
bool ADaedalusBricksSkylineWorkshop::ToolsReady() const
{
    if (!IsWorkshopAlive() || OwnedControls.Num()!=26) return false;
    for (int32 I=0;I<26;++I)
    {
        const auto* Control=OwnedControls[I].Get();
        if (!IsValid(Control) || Control->IsActorBeingDestroyed() || !Control->HasActorBegunPlay() || Control->GetOwner()!=this || Control->GetWorld()!=GetWorld() ||
            Control->GetActorEnableCollision() || !Control->Matches(this,DaedalusSkylineLocal::ActionAt(I),DaedalusSkylineLocal::ParameterAt(I)) ||
            !Control->GetActorTransform().Equals(FTransform(DaedalusSkylineLocal::ControlAt(I))*GetActorTransform(),0.01)) return false;
    }
    return true;
}
bool ADaedalusBricksSkylineWorkshop::IsCurrentComplete() const
{ daedalus::skyline::Evaluation View; return Run.View(View) && View.Complete; }
void ADaedalusBricksSkylineWorkshop::DrawModel()
{
    if (!ViewsReady() || !Run.Active()) return;
    daedalus::skyline::Evaluation View; if (!Run.View(View)) return;
    const auto& Blueprint=daedalus::skyline::Blueprints[Run.CurrentRule()]; DaedalusSkylineLocal::Ink Ink;
    for (int32 Cell=0;Cell<16;++Cell)
    {
        const FVector At=DaedalusSkylineLocal::CellAt(Cell); const int32 Height=Run.Canvas()[Cell];
        Ink.Box(At+FVector(0,0,2),FVector(80,80,1),FLinearColor(0.9f,0.94f,0.97f));
        Ink.Outline(At+FVector(0,0,4),80,View.Conflicts[Cell]?FLinearColor(0.9f,0.15f,0.1f):FLinearColor(0.12f,0.22f,0.3f));
        if (Blueprint.Givens[Cell]) Ink.Box(At+FVector(-66,66,10),FVector(8,8,7),FLinearColor(1,0.72f,0.12f));
        if (SelectedCell==Cell) Ink.Outline(At+FVector(0,0,6),75,FLinearColor::White);
        if (bHintVisible && ShownHint.CellIndex==Cell) Ink.Outline(At+FVector(0,0,8),69,FLinearColor(1,0.65f,0.05f));
        for (int32 Floor=0;Floor<Height;++Floor) Ink.Box(At+FVector(0,0,26+52*Floor),FVector(40,40,22),DaedalusSkylineLocal::HeightColour(Height));
        if (Height) for (int32 X=-1;X<=1;X+=2) for (int32 Y=-1;Y<=1;Y+=2)
            Ink.Box(At+FVector(X*18,Y*18,52*Height),FVector(7,7,4),DaedalusSkylineLocal::HeightColour(Height));
    }
    for (int32 Height=0;Height<=4;++Height)
    {
        const FVector At=DaedalusSkylineLocal::ControlAt(16+Height);
        Ink.Box(At,FVector(22,28,14),DaedalusSkylineLocal::HeightColour(Height));
        if (Height==BrushHeight) Ink.Outline(At+FVector(0,0,16),32,FLinearColor(0.04f,0.12f,0.2f));
    }
    for (int32 I=0;I<16;++I)
    {
        const int32 Side=I/4,Line=I%4;
        const int32 Target=Side==0?Blueprint.Left[Line]:Side==1?Blueprint.Right[Line]:Side==2?Blueprint.Top[Line]:Blueprint.Bottom[Line];
        const int32 Now=Side==0?View.Left[Line]:Side==1?View.Right[Line]:Side==2?View.Top[Line]:View.Bottom[Line];
        const bool Full=Side<2?View.RowFull[Line]:View.ColumnFull[Line]; bool Clean=true; int32 Seen=0;
        // A clue judges its own line. Global cell conflicts can also come from
        // a crossing line and must not turn an otherwise correct clue red.
        for (int32 K=0;K<4;++K)
        {
            const int32 Height=Run.Canvas()[Side<2?Line*4+K:K*4+Line];
            if (Height && (Seen&(1<<Height))) Clean=false;
            if (Height) Seen|=1<<Height;
        }
        const bool Match=Target && Full && Clean && Now==Target;
        ClueLabels[I]->SetTextRenderColor(!Target?FColor(70,85,100):Match?FColor(15,120,70):Full?FColor(165,40,30):FColor(25,40,60));
        if (!ViewsReady()) return;
        ClueLabels[I]->SetText(FText::FromString(Target?FString::Printf(TEXT("WANT %d\nNOW %d / %s"),Target,Now,!Full?TEXT("BUILD"):Match?TEXT("MATCH"):TEXT("CHECK")):
            FString::Printf(TEXT("OPEN VIEW\nNOW %d"),Now)));
        if (!ViewsReady()) return;
    }
    TArray<FVector2D> UV; UV.Init(FVector2D::ZeroVector,Ink.Vertices.Num()); TArray<FProcMeshTangent> Tangents;
    Model->CreateMeshSection_LinearColor(0,Ink.Vertices,Ink.Triangles,Ink.Normals,UV,Ink.Colours,Tangents,false);
    if (ViewsReady()) Model->SetMaterial(0,InkMaterial);
}

void ADaedalusBricksSkylineWorkshop::Refresh(int32 NewlyStudied)
{
    if (!IsWorkshopAlive() || bNotifying) return;
    FString Text;
    if (Run.Active())
    {
        daedalus::skyline::Evaluation View; Run.View(View);
        Text=FString::Printf(TEXT("BLUEPRINT %d / 3: %s\nHeights set %d / 16\nFull side clues matched %d / %d\nBrush: %s\nUndo %u / Redo %u\n%d plans finished this visit\n"),Run.CurrentRule()+1,
            UTF8_TO_TCHAR(daedalus::skyline::Blueprints[Run.CurrentRule()].Name),View.Filled,View.ClueMatches,View.ClueCount,
            BrushHeight?*FString::Printf(TEXT("height %d"),BrushHeight):TEXT("Erase"),static_cast<unsigned>(Run.UndoCount()),static_cast<unsigned>(Run.RedoCount()),Run.CompletedCount());
        if (!View.LatinPossible) Text+=TEXT("A row or column repeats a height. Check the marked pads.\n");
        if (Run.EverCompleted(Run.CurrentRule()) && !View.Complete) Text+=TEXT("Finished before; this skyline is still being built.\n");
        if (daedalus::skyline::SolutionCount(Run.CurrentRule())>1) Text+=TEXT("More than one skyline fits this plan.\n");
        if (ViewsReady())
        {
            Title->SetText(FText::FromString(FString(TEXT("SKYLINE BLUEPRINTS / "))+UTF8_TO_TCHAR(daedalus::skyline::Blueprints[Run.CurrentRule()].Name)));
            if (!IsWorkshopAlive()) return; DrawModel();
        }
    }
    Text+=Notice; if (!IsWorkshopAlive()) return;
    if (IsValid(Readout) && Readout->GetOwner()==this) Readout->SetText(FText::FromString(DaedalusSkylineLocal::Wrap(Text)));
    if (!IsWorkshopAlive()) return;
    TGuardValue<bool> Notification(bNotifying,true); OnViewChanged.Broadcast(this);
    if (!IsWorkshopAlive()) return;
    if (NewlyStudied>=0) OnBlueprintStudied.Broadcast(this,NewlyStudied); // No gameplay writes after event.
}
FString ADaedalusBricksSkylineWorkshop::ControlLabel(EDaedalusSkylineAction Action,int32 Parameter) const
{
    if (!IsWorkshopAlive() || !Run.Active()) return TEXT("--");
    FString Text;
    if (!bAvailable || !ViewsReady()) Text=TEXT("Workshop unavailable");
    else if (Action==EDaedalusSkylineAction::Cell && Parameter>=0 && Parameter<16)
    {
        const int32 Height=Run.Canvas()[Parameter];
        Text=FString::Printf(TEXT("R%d C%d: %s"),Parameter/4+1,Parameter%4+1,Height?*FString::FromInt(Height):TEXT("EMPTY"));
        if (daedalus::skyline::Blueprints[Run.CurrentRule()].Givens[Parameter]) Text+=TEXT(" / FIXED");
        daedalus::skyline::Evaluation View; Run.View(View); if (View.Conflicts[Parameter]) Text+=TEXT("\nCHECK ROW / COLUMN");
        if (bHintVisible && ShownHint.CellIndex==Parameter) Text+=FString::Printf(TEXT("\n[HINT] TRY %d"),ShownHint.Height);
    }
    else if (Action==EDaedalusSkylineAction::Height && Parameter>=0 && Parameter<=4)
    {
        Text=Parameter?FString::Printf(TEXT("Height %d"),Parameter):TEXT("Erase");
        if (Parameter==BrushHeight) Text+=TEXT(" / READY");
        if (bHintVisible && ShownHint.Height==Parameter) Text+=TEXT("\n[HINT] CHOOSE");
    }
    else if (Action==EDaedalusSkylineAction::NextBlueprint) Text=TEXT("Next blueprint\nYour work stays");
    else if (Action==EDaedalusSkylineAction::Hint) Text=bHintVisible?TEXT("Put hint away"):TEXT("Hint / free");
    else if (Action==EDaedalusSkylineAction::Undo) Text=FString::Printf(TEXT("Undo / %u"),static_cast<unsigned>(Run.UndoCount()));
    else if (Action==EDaedalusSkylineAction::Redo) Text=FString::Printf(TEXT("Redo / %u"),static_cast<unsigned>(Run.RedoCount()));
    else if (Action==EDaedalusSkylineAction::Restart) Text=bRestartArmed?TEXT("Confirm restart"):TEXT("Restart blueprint");
    else Text=TEXT("--");
    if (bFeedback && Action==FeedbackAction && Parameter==FeedbackParameter) Text+=TEXT("\n")+DaedalusSkylineLocal::Wrap(Notice,Action==EDaedalusSkylineAction::Cell?26:36,3);
    return Text;
}
FString ADaedalusBricksSkylineWorkshop::ControlPrompt(EDaedalusSkylineAction Action,int32 Parameter) const
{
    if (!IsWorkshopAlive() || !Run.Active() || !bAvailable || !ViewsReady() || !DaedalusSkylineLocal::ValidAction(Action,Parameter)) return TEXT("Skyline tool is unavailable");
    if (Action==EDaedalusSkylineAction::Cell)
    {
        const int32 Given=daedalus::skyline::Blueprints[Run.CurrentRule()].Givens[Parameter];
        if (Given) return FString::Printf(TEXT("R%d C%d is a fixed height %d. Choose another pad."),Parameter/4+1,Parameter%4+1,Given);
        return BrushHeight?FString::Printf(TEXT("E / X: Set R%d C%d to height %d"),Parameter/4+1,Parameter%4+1,BrushHeight):
            FString::Printf(TEXT("E / X: Erase R%d C%d; Undo can restore it"),Parameter/4+1,Parameter%4+1);
    }
    if (Action==EDaedalusSkylineAction::Height) return Parameter?FString::Printf(TEXT("E / X: Choose height %d, then use a pad"),Parameter):TEXT("E / X: Choose Erase, then use a pad");
    if (Action==EDaedalusSkylineAction::NextBlueprint) return TEXT("E / X: Next blueprint; every plan keeps its heights and history");
    if (Action==EDaedalusSkylineAction::Hint) return TEXT("E / X: A free height hint, including repair of a conflicting entry");
    if (Action==EDaedalusSkylineAction::Undo) return TEXT("E / X: Undo this plan's last height edit");
    if (Action==EDaedalusSkylineAction::Redo) return TEXT("E / X: Redo this plan's last undone height edit");
    return bRestartArmed?TEXT("E / X: Confirm restart of this plan only"):TEXT("E / X: Restart this plan - confirm twice");
}
bool ADaedalusBricksSkylineWorkshop::Operate(ADaedalusHero* Hero,const AActor* Tool,EDaedalusSkylineAction Action,int32 Parameter)
{
    if (!IsWorkshopAlive() || GetWorld()->GetNetMode()!=NM_Standalone || !Run.Active() || bBusy || bNotifying ||
        !DaedalusSkylineLocal::ValidAction(Action,Parameter) || !DaedalusSkylineLocal::LocalReach(Hero,Tool)) return false;
    const int32 Slot=DaedalusSkylineLocal::ControlIndex(Action,Parameter); const auto* Control=Cast<ADaedalusSkylineControl>(Tool);
    if (!IsWorkshopAlive() || !Control || !OwnedControls.IsValidIndex(Slot) || OwnedControls[Slot].Get()!=Control || Control->GetOwner()!=this ||
        !Control->Matches(this,Action,Parameter) || !Control->GetActorTransform().Equals(FTransform(DaedalusSkylineLocal::ControlAt(Slot))*GetActorTransform(),0.01)) return false;
    TGuardValue<bool> Busy(bBusy,true); bFeedback=true; FeedbackAction=Action; FeedbackParameter=Parameter;
    if (!bAvailable || !ViewsReady() || !ToolsReady())
    { bAvailable=false; Notice=TEXT("A model view or tool is unavailable. Every plan's heights and history stay in place."); Refresh(); return false; }
    if (Action!=EDaedalusSkylineAction::Restart) bRestartArmed=false;
    if (Action==EDaedalusSkylineAction::Height)
    {
        BrushHeight=Parameter;
        Notice=bHintVisible?FString::Printf(TEXT("%s ready. The hint stays at R%d C%d; use that pad when ready."),BrushHeight?*FString::Printf(TEXT("Height %d"),BrushHeight):TEXT("Erase"),ShownHint.CellIndex/4+1,ShownHint.CellIndex%4+1):
            TEXT("Height brush ready. Use any editable pad; choosing a height does not change Undo / Redo.");
        Refresh(); return IsWorkshopAlive();
    }
    if (Action==EDaedalusSkylineAction::Hint)
    {
        if (bHintVisible) { bHintVisible=false; Notice=TEXT("Hint put away. Each row and column uses heights 1-4 once. Taller towers hide shorter ones behind them."); }
        else if (Run.Hint(ShownHint))
        {
            bHintVisible=true;
            Notice=FString::Printf(TEXT("Try height %d at R%d C%d. %s A matching skyline is %d edits away, including this one. Choose that height, then use the marked pad."),
                ShownHint.Height,ShownHint.CellIndex/4+1,ShownHint.CellIndex%4+1,ShownHint.Repair?TEXT("This repairs a different entry."):TEXT("This fills an empty pad."),ShownHint.Remaining);
        }
        else Notice=TEXT("This skyline matches the plan. You can study another blueprint or keep exploring with Undo / Redo.");
        Refresh(); return IsWorkshopAlive();
    }
    if (Action==EDaedalusSkylineAction::Restart && !bRestartArmed)
    {
        bRestartArmed=true; Notice=TEXT("Use Restart once more to return this plan to its fixed heights and clear its history. Other plans and finished notes stay. Any other tool cancels.");
        Refresh(); return false;
    }
    std::array<bool,3> Before{}; for (int32 I=0;I<3;++I) Before[I]=Run.EverCompleted(I);
    bool Changed=false;
    if (Action==EDaedalusSkylineAction::Cell)
    {
        SelectedCell=Parameter; const auto Result=Run.SetHeight(Parameter,BrushHeight); Changed=Result==daedalus::skyline::Change::Changed;
        if (!Changed)
        {
            Notice=Result==daedalus::skyline::Change::Fixed?TEXT("That height is fixed by the blueprint. Use another pad; no edit was added."):
                Result==daedalus::skyline::Change::Unchanged?TEXT("That pad already has this height. No edit was added; Redo is kept."):TEXT("That edit is unavailable. Your plan is unchanged.");
            Refresh(); return false;
        }
    }
    else if (Action==EDaedalusSkylineAction::NextBlueprint) { Changed=Run.SelectRule((Run.CurrentRule()+1)%3); SelectedCell=-1; }
    else if (Action==EDaedalusSkylineAction::Undo) Changed=Run.Undo();
    else if (Action==EDaedalusSkylineAction::Redo) Changed=Run.Redo();
    else if (Action==EDaedalusSkylineAction::Restart) { Changed=Run.Restart(); bRestartArmed=false; SelectedCell=-1; }
    if (!Changed)
    {
        Notice=Action==EDaedalusSkylineAction::Restart?TEXT("This plan is already at its fixed starting heights with no history."):TEXT("There is no edit in that history direction.");
        Refresh(); return false;
    }
    bHintVisible=false; daedalus::skyline::Evaluation View; Run.View(View);
    const int32 Rule=Run.CurrentRule(); const int32 NewlyStudied=!Before[Rule] && Run.EverCompleted(Rule)?Rule:-1;
    if (View.Complete) Notice=TEXT("Skyline complete! Every row, column and specified side view matches. You can explore other valid skylines or try another plan.");
    else if (Action==EDaedalusSkylineAction::NextBlueprint) Notice=TEXT("This plan kept its heights, Undo and Redo. Fixed heights have a gold marker; OPEN VIEW has no required count.");
    else if (Action==EDaedalusSkylineAction::Restart) Notice=TEXT("Only this blueprint restarted. Other plans and finished notes stay.");
    else Notice=!View.LatinPossible?TEXT("A height repeats in a row or column. Marked pads help you spot it; Undo or a free repair Hint can help."):
        TEXT("Height edited. Side numbers count visible towers, not their sum. Finish a line before checking its WANT / NOW match.");
    Refresh(NewlyStudied); return IsWorkshopAlive();
}

void ADaedalusBricksSkylineWorkshop::SpawnControls()
{
    if (!IsWorkshopAlive() || bToolsAttempted) return;
    bToolsAttempted=true; const uint64 StartEpoch=Epoch; const TWeakObjectPtr<ADaedalusBricksSkylineWorkshop> Self(this);
    for (int32 I=0;I<26 && IsWorkshopAlive();++I)
    {
        const auto Action=DaedalusSkylineLocal::ActionAt(I); const int32 Parameter=DaedalusSkylineLocal::ParameterAt(I);
        const FTransform Expected=FTransform(DaedalusSkylineLocal::ControlAt(I))*GetActorTransform();
        TWeakObjectPtr<ADaedalusSkylineControl> Staged;
        FActorSpawnParameters Parameters; Parameters.Owner=this; Parameters.ObjectFlags=RF_Transient|RF_DuplicateTransient; Parameters.bDeferConstruction=true;
        Parameters.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        Parameters.CustomPreSpawnInitialization=[Self,StartEpoch,I,&Staged](AActor* Actor)
        {
            Actor->SetActorEnableCollision(false); auto* Workshop=Self.Get(); auto* Control=Cast<ADaedalusSkylineControl>(Actor); Staged=Control;
            if (!Workshop || !Workshop->IsWorkshopAlive() || Workshop->Epoch!=StartEpoch || !Control || Workshop->OwnedControls.Num()!=I) return;
            Workshop->OwnedControls.Add(Control); Control->OnEndPlay.AddUniqueDynamic(Workshop,&ADaedalusBricksSkylineWorkshop::ControlEnded);
        };
        auto* Control=GetWorld()->SpawnActor<ADaedalusSkylineControl>(ADaedalusSkylineControl::StaticClass(),Expected,Parameters);
        auto Valid=[&]()
        { return IsWorkshopAlive() && Epoch==StartEpoch && IsValid(Control) && !Control->IsActorBeingDestroyed() && Staged.Get()==Control &&
            OwnedControls.IsValidIndex(I) && OwnedControls[I].Get()==Control && Control->GetOwner()==this && Control->GetWorld()==GetWorld(); };
        auto Fail=[&]()
        {
            TArray<TWeakObjectPtr<ADaedalusSkylineControl>> Effects; if (IsValid(Control)) Effects.AddUnique(TWeakObjectPtr<ADaedalusSkylineControl>(Control));
            if (Staged.IsValid()) Effects.AddUnique(Staged);
            auto Earlier=[&](const ADaedalusSkylineControl* Actor)
            { for (int32 J=0;J<I && J<OwnedControls.Num();++J) if (OwnedControls[J].Get()==Actor) return true; return false; };
            for (const auto& Effect:Effects) if (auto* Actor=Effect.Get()) if (!Earlier(Actor)) Actor->OnEndPlay.RemoveDynamic(this,&ADaedalusBricksSkylineWorkshop::ControlEnded);
            for (const auto& Effect:Effects) if (auto* Actor=Effect.Get())
                if (!Earlier(Actor) && !Actor->IsActorBeingDestroyed() && Actor->GetOwner()==this) Actor->Destroy();
            if (IsWorkshopAlive()) bAvailable=false;
        };
        if (!Valid() || !Control->ConfigureWorkshop(this,Action,Parameter) || !Valid()) { Fail(); return; }
        Control->FinishSpawning(Expected);
        if (!Valid() || !Control->HasActorBegunPlay()) { Fail(); return; }
        Control->AttachToActor(this,FAttachmentTransformRules::KeepWorldTransform);
        if (!Valid() || !Control->GetActorTransform().Equals(Expected,0.01)) { Fail(); return; }
    }
    if (IsWorkshopAlive() && !ToolsReady()) bAvailable=false;
}
void ADaedalusBricksSkylineWorkshop::BeginPlay()
{
    bEnding=false; ++Epoch; Super::BeginPlay(); if (!IsWorkshopAlive()) return;
    if (GetWorld()->GetNetMode()!=NM_Standalone || !ViewsReady() || !Run.Begin())
    { bAvailable=false; Notice=TEXT("This skyline workshop is unavailable here."); Refresh(); return; }
    TGuardValue<bool> Preparing(bBusy,true); SpawnControls(); if (!IsWorkshopAlive()) return;
    Notice=bAvailable?TEXT("Choose a height, then use a pad. Each row and column uses 1-4 once. Side numbers count visible towers; taller ones hide shorter ones. Gold markers mean fixed heights. Hint and Undo help."):
        TEXT("Some workshop tools could not be prepared. Your plan is kept; controls are unavailable.");
    Refresh();
}
void ADaedalusBricksSkylineWorkshop::ControlEnded(AActor* Actor,EEndPlayReason::Type)
{
    if (!IsWorkshopAlive() || !Actor) return;
    bool Found=false; for (const auto& Control:OwnedControls) if (Control.Get()==Actor) { Found=true; break; } if (!Found) return;
    bAvailable=false; bRestartArmed=false; Notice=TEXT("A workshop tool is unavailable. Every plan's heights and history stay in place.");
    if (!bBusy && !bNotifying) Refresh();
}
void ADaedalusBricksSkylineWorkshop::ReleaseControls()
{
    const auto Controls=OwnedControls; OwnedControls.Reset();
    for (const auto& Control:Controls) if (IsValid(Control)) Control->OnEndPlay.RemoveDynamic(this,&ADaedalusBricksSkylineWorkshop::ControlEnded);
    for (const auto& Control:Controls) if (IsValid(Control) && !Control->IsActorBeingDestroyed() && Control->GetOwner()==this) Control->Destroy();
}
void ADaedalusBricksSkylineWorkshop::EndPlay(const EEndPlayReason::Type Reason)
{ bEnding=true; ++Epoch; ReleaseControls(); OnViewChanged.Broadcast(this); Super::EndPlay(Reason); }

ADaedalusSkylineControl::ADaedalusSkylineControl()
{
    PrimaryActorTick.bCanEverTick=false; bReplicates=false; SetActorEnableCollision(false);
    ControlRoot=CreateDefaultSubobject<USceneComponent>(TEXT("SkylineControlRoot")); RootComponent=ControlRoot;
    Body->SetupAttachment(ControlRoot); Glow->SetupAttachment(ControlRoot); Glow->SetIntensity(0.f); Glow->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    Body->SetStaticMesh(Cube.Object); Body->SetRelativeScale3D(FVector(0.35,0.5,0.25)); Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Label=CreateDefaultSubobject<UTextRenderComponent>(TEXT("SkylineControlLabel")); Label->SetupAttachment(ControlRoot);
    Label->SetWorldSize(9.f); Label->SetHorizontalAlignment(EHTA_Center); Label->SetVerticalAlignment(EVRTA_TextCenter); Label->SetTextRenderColor(FColor(25,40,60));
}
void ADaedalusSkylineControl::BeginPlay()
{ bEnding=false; Super::BeginPlay(); if (!bEnding && !IsActorBeingDestroyed()) ConfigureWorkshop(Workshop,Action,Parameter); }
void ADaedalusSkylineControl::UnbindWorkshop()
{
    if (auto* Previous=ObservedWorkshop.Get()) Previous->OnViewChanged.RemoveDynamic(this,&ADaedalusSkylineControl::WorkshopViewChanged);
    ObservedWorkshop.Reset();
}
bool ADaedalusSkylineControl::ConfigureWorkshop(ADaedalusBricksSkylineWorkshop* NewWorkshop,EDaedalusSkylineAction NewAction,int32 NewParameter)
{
    if (!IsInGameThread() || bEnding || IsActorBeingDestroyed() || !DaedalusSkylineLocal::ValidAction(NewAction,NewParameter) ||
        !IsValid(Body) || Body->GetOwner()!=this || !IsValid(Glow) || Glow->GetOwner()!=this || !IsValid(Label) || Label->GetOwner()!=this ||
        (NewWorkshop && (!IsValid(NewWorkshop) || NewWorkshop->IsActorBeingDestroyed() || NewWorkshop->GetWorld()!=GetWorld()))) return false;
    UnbindWorkshop(); Workshop=NewWorkshop; Action=NewAction; Parameter=NewParameter;
    Body->SetVisibility(Action!=EDaedalusSkylineAction::Cell && Action!=EDaedalusSkylineAction::Height); Glow->SetIntensity(0.f); Glow->SetVisibility(false);
    Label->SetRelativeLocation(Action==EDaedalusSkylineAction::Cell?FVector(65,0,45):FVector(25,0,75));
    if (IsValid(Workshop)) { ObservedWorkshop=Workshop; Workshop->OnViewChanged.AddUniqueDynamic(this,&ADaedalusSkylineControl::WorkshopViewChanged); }
    RefreshLabel(); return true;
}
bool ADaedalusSkylineControl::Matches(const ADaedalusBricksSkylineWorkshop* Target,EDaedalusSkylineAction ExpectedAction,int32 ExpectedParameter) const
{ return !bEnding && Workshop.Get()==Target && Action==ExpectedAction && Parameter==ExpectedParameter && IsValid(Label) && Label->GetOwner()==this && Label->IsRegistered(); }
void ADaedalusSkylineControl::RefreshLabel()
{
    if (!bEnding && IsValid(Label) && Label->GetOwner()==this)
        Label->SetText(FText::FromString(IsValid(Workshop) && Workshop->GetWorld()==GetWorld()?Workshop->ControlLabel(Action,Parameter):TEXT("--")));
}
void ADaedalusSkylineControl::WorkshopViewChanged(ADaedalusBricksSkylineWorkshop* ChangedWorkshop)
{
    if (bEnding || ChangedWorkshop!=Workshop.Get()) return;
    if (!ChangedWorkshop->IsWorkshopAlive()) { UnbindWorkshop(); Workshop=nullptr; }
    RefreshLabel();
}
void ADaedalusSkylineControl::EndPlay(const EEndPlayReason::Type Reason)
{ bEnding=true; UnbindWorkshop(); Workshop=nullptr; Super::EndPlay(Reason); }
FString ADaedalusSkylineControl::Prompt(const ADaedalusHero*) const
{ return !bEnding && HasActorBegunPlay() && IsValid(Workshop) && Workshop->GetWorld()==GetWorld()?Workshop->ControlPrompt(Action,Parameter):TEXT("Skyline tool is not connected"); }
bool ADaedalusSkylineControl::Use(ADaedalusHero* Hero)
{ return !bEnding && IsValid(Workshop) && Workshop->GetWorld()==GetWorld() && Workshop->Operate(Hero,this,Action,Parameter); }
