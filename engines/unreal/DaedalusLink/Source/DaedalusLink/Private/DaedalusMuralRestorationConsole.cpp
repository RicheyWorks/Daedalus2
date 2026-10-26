// SPDX-License-Identifier: MIT
#include "DaedalusMuralRestorationConsole.h"
#include "DaedalusLivingPainting.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "ProceduralMeshComponent.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

namespace DaedalusMuralRestorationLocal
{
    FString WrapReadout(const FString& Text)
    {
        TArray<FString> Lines;
        Text.ParseIntoArrayLines(Lines, false);
        FString Wrapped;
        for (int32 I = 0; I < Lines.Num(); ++I)
        {
            if (I) Wrapped += TEXT("\n");
            TArray<FString> Words;
            Lines[I].ParseIntoArray(Words, TEXT(" "), true);
            int32 Columns = 0;
            for (const FString& Word : Words)
            {
                if (Columns && Columns + 1 + Word.Len() > 42) { Wrapped += TEXT("\n"); Columns = 0; }
                if (Columns) { Wrapped += TEXT(" "); ++Columns; }
                Wrapped += Word; Columns += Word.Len();
            }
        }
        return Wrapped;
    }
    const TCHAR* Colour(int32 Index)
    {
        static const TCHAR* Names[] = {TEXT("Red"), TEXT("Yellow"), TEXT("Blue"), TEXT("Orange"), TEXT("Green"), TEXT("Violet")};
        return Index >= 0 && Index < 6 ? Names[Index] : TEXT("Unknown colour");
    }
    FString ActionName(EDaedalusMuralToolAction Action)
    {
        switch (Action)
        {
        case EDaedalusMuralToolAction::NextCell: return TEXT("Choose next cell");
        case EDaedalusMuralToolAction::PreviousCell: return TEXT("Choose previous cell");
        case EDaedalusMuralToolAction::NextPigment: return TEXT("Choose next colour");
        case EDaedalusMuralToolAction::PreviousPigment: return TEXT("Choose previous colour");
        case EDaedalusMuralToolAction::MixPigment: return TEXT("Mix selected colour");
        case EDaedalusMuralToolAction::WashCell: return TEXT("Wash selected cell");
        case EDaedalusMuralToolAction::RevealCell: return TEXT("Ask Prism Sight");
        }
        return TEXT("Unknown mural tool");
    }
    FString StrokeNotice(const FString& Result, int32 Pigment)
    {
        if (Result == TEXT("RESTORED")) return TEXT("Colour restored. Choose another cell to continue.");
        if (Result == TEXT("SMUDGED")) return TEXT("That colour made a smudge. Wash this cell before painting again.");
        if (Result == TEXT("NEEDS_WASH")) return TEXT("Wash this cell before painting again.");
        if (Result == TEXT("ALREADY_RESTORED")) return TEXT("This cell is already restored. Choose another cell.");
        if (Result == TEXT("NO_PIGMENT")) return FString::Printf(TEXT("No %s pigment left. Choose another colour."), Colour(Pigment));
        if (Result == TEXT("WASHED")) return TEXT("The smudge is washed away. This cell can be painted again.");
        if (Result == TEXT("NOTHING_TO_WASH")) return TEXT("There is no smudge on this cell.");
        return TEXT("This cell is unavailable. Check the connected mural.");
    }
    FString MixNotice(const FString& Result, int32 Pigment)
    {
        daedalus::gallery::Pigment First, Second;
        if (!daedalus::gallery::Components(static_cast<daedalus::gallery::Pigment>(Pigment), First, Second))
            return TEXT("Choose Orange, Green or Violet to mix a colour.");
        const TCHAR* A = Colour(static_cast<int32>(First));
        const TCHAR* B = Colour(static_cast<int32>(Second));
        if (Result == TEXT("OK")) return FString::Printf(TEXT("Mixed one %s from one %s and one %s."), Colour(Pigment), A, B);
        if (Result == TEXT("NOT_KNOWN")) return FString::Printf(TEXT("Learn %s and %s before mixing %s."), A, B, Colour(Pigment));
        if (Result == TEXT("MISSING_PRIMARY")) return FString::Printf(TEXT("Mixing %s needs one %s and one %s."), Colour(Pigment), A, B);
        if (Result == TEXT("FULL")) return FString::Printf(TEXT("The %s pigment pot is full."), Colour(Pigment));
        return TEXT("This colour could not be mixed.");
    }
}

ADaedalusMuralRestorationConsole::ADaedalusMuralRestorationConsole()
{
    PrimaryActorTick.bCanEverTick = false;
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded()) Body->SetStaticMesh(Cube.Object);
    Body->SetRelativeScale3D(FVector(0.2f, 0.7f, 0.7f));
    Glow->SetIntensity(0.f);
    Readout = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Readout"));
    Readout->SetupAttachment(Body);
    // Absolute scale keeps the inherited button mesh's shape from distorting text/highlight.
    Readout->SetAbsolute(false, false, true);
    Readout->SetRelativeLocation(FVector(60.f, 0.f, 70.f));
    Readout->SetWorldSize(12.f);
    Readout->SetHorizontalAlignment(EHTA_Center);
    Readout->SetVerticalAlignment(EVRTA_TextBottom);
    Readout->SetTextRenderColor(FColor(255, 240, 190));
    Readout->SetText(FText::FromString(TEXT("Mural restoration\nConnect a living painting")));
    CellBorder = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("CellBorder"));
    CellBorder->SetupAttachment(Body);
    CellBorder->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    CellBorder->SetCastShadow(false);
    CellBorder->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Engine/EngineDebugMaterials/VertexColorMaterial.VertexColorMaterial"));
    BorderMaterial = Material.Object;
}

void ADaedalusMuralRestorationConsole::BeginPlay()
{
    Super::BeginPlay();
    bEnding = false;
    SetPainting(Painting);
    // A placed painting may initialize its palette after this actor's BeginPlay.
    // One UObject-bound refresh settles that order without a recurring tick.
    if (UWorld* World = GetWorld()) World->GetTimerManager().SetTimerForNextTick(this, &ADaedalusMuralRestorationConsole::Refresh);
}

void ADaedalusMuralRestorationConsole::UnbindPainting()
{
    if (!IsValid(Painting)) return;
    Painting->OnStroke.RemoveDynamic(this, &ADaedalusMuralRestorationConsole::OnStroke);
    Painting->OnAwake.RemoveDynamic(this, &ADaedalusMuralRestorationConsole::OnAwake);
    Painting->OnDestroyed.RemoveDynamic(this, &ADaedalusMuralRestorationConsole::OnPaintingDestroyed);
    Painting->OnEndPlay.RemoveDynamic(this, &ADaedalusMuralRestorationConsole::OnPaintingEndPlay);
}

void ADaedalusMuralRestorationConsole::SetPainting(ADaedalusLivingPainting* NewPainting)
{
    if (bEnding) return;
    UnbindPainting();
    CellBorder->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    Painting = NewPainting;
    Focus.Configure(-1, 0, 0);
    ClearHint(); Notice.Reset();
    if (IsValid(Painting) && !Painting->IsActorBeingDestroyed())
    {
        Painting->OnStroke.AddDynamic(this, &ADaedalusMuralRestorationConsole::OnStroke);
        Painting->OnAwake.AddDynamic(this, &ADaedalusMuralRestorationConsole::OnAwake);
        Painting->OnDestroyed.AddDynamic(this, &ADaedalusMuralRestorationConsole::OnPaintingDestroyed);
        Painting->OnEndPlay.AddDynamic(this, &ADaedalusMuralRestorationConsole::OnPaintingEndPlay);
        CellBorder->AttachToComponent(Painting->GetRootComponent(), FAttachmentTransformRules::KeepRelativeTransform);
        CellBorder->SetRelativeScale3D(FVector::OneVector);
        CellBorder->SetRelativeRotation(FRotator::ZeroRotator);
    }
    Refresh();
}

void ADaedalusMuralRestorationConsole::EndPlay(const EEndPlayReason::Type Reason)
{
    bEnding = true;
    UnbindPainting();
    CellBorder->SetVisibility(false);
    CellBorder->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    Super::EndPlay(Reason);
}

void ADaedalusMuralRestorationConsole::OnPaintingDestroyed(AActor*) { SetPainting(nullptr); }
void ADaedalusMuralRestorationConsole::OnPaintingEndPlay(AActor*, EEndPlayReason::Type) { SetPainting(nullptr); }
void ADaedalusMuralRestorationConsole::ClearHint() { bHasHint = false; HintPigment = 0; }

bool ADaedalusMuralRestorationConsole::Synchronize()
{
    if (!IsValid(Painting) || Painting->IsActorBeingDestroyed() || !Painting->HasActorBegunPlay())
    {
        Focus.Configure(-1, 0, 0); ClearHint();
        return false;
    }
    const int32 PreviousX = Focus.X(), PreviousY = Focus.Y();
    const int32 PreviousPigment = Focus.PigmentIndex();
    const bool bChangedMural = ObservedSeed != Painting->Seed || Focus.Width() != Painting->Width || Focus.Height() != Painting->Height;
    if (!Focus.Configure(Painting->Seed, Painting->Width, Painting->Height) ||
        !FMath::IsFinite(Painting->CellSize) || Painting->CellSize <= 0.f)
    { Focus.Configure(-1, 0, 0); ClearHint(); return false; }
    ObservedSeed = Painting->Seed;
    Focus.SelectPigment(static_cast<int32>(Painting->SelectedPigment));
    if (bChangedMural || PreviousX != Focus.X() || PreviousY != Focus.Y() || PreviousPigment != Focus.PigmentIndex()) ClearHint();
    return true;
}

FString ADaedalusMuralRestorationConsole::Prompt(const ADaedalusHero*) const
{
    if (!IsValid(Painting) || !Focus.Valid()) return TEXT("Look at mural controls");
    return FString::Printf(TEXT("Paint cell %d,%d with %s"), Focus.X() + 1, Focus.Y() + 1, DaedalusMuralRestorationLocal::Colour(Focus.PigmentIndex()));
}

bool ADaedalusMuralRestorationConsole::Use(ADaedalusHero*)
{
    PaintSelectedCell();
    return true;
}

bool ADaedalusMuralRestorationConsole::SelectCell(int32 X, int32 Y)
{
    if (!Synchronize()) { Notice = TEXT("No usable mural is connected."); Refresh(); return false; }
    if (!Focus.SetCell(X, Y)) { Notice = TEXT("Choose a cell inside this mural."); Refresh(); return false; }
    ClearHint(); Notice.Reset(); Refresh();
    return true;
}

FString ADaedalusMuralRestorationConsole::PaintSelectedCell()
{
    if (!Synchronize()) { Notice = TEXT("No usable mural is connected."); Refresh(); return TEXT("BAD_CELL"); }
    const int32 Pigment = Focus.PigmentIndex();
    const FString Result = Painting->Paint(Focus.X(), Focus.Y(), static_cast<EDaedalusPigment>(Pigment));
    ClearHint();
    Notice = Painting->ProgressPm() == 1000 ? TEXT("Every cell is restored.") : DaedalusMuralRestorationLocal::StrokeNotice(Result, Pigment);
    Refresh();
    return Result;
}

FString ADaedalusMuralRestorationConsole::PerformTool(EDaedalusMuralToolAction Action)
{
    if (!Synchronize()) { Notice = TEXT("No usable mural is connected."); Refresh(); return TEXT("NO_MURAL"); }
    FString Result = TEXT("OK");
    ClearHint(); Notice.Reset();
    switch (Action)
    {
    case EDaedalusMuralToolAction::NextCell: Focus.Move(1); break;
    case EDaedalusMuralToolAction::PreviousCell: Focus.Move(-1); break;
    case EDaedalusMuralToolAction::NextPigment:
    case EDaedalusMuralToolAction::PreviousPigment:
        Focus.CyclePigment(Action == EDaedalusMuralToolAction::NextPigment ? 1 : -1);
        Painting->SelectedPigment = static_cast<EDaedalusPigment>(Focus.PigmentIndex());
        break;
    case EDaedalusMuralToolAction::MixPigment:
        Result = Painting->Mix(static_cast<EDaedalusPigment>(Focus.PigmentIndex()));
        Notice = DaedalusMuralRestorationLocal::MixNotice(Result, Focus.PigmentIndex());
        break;
    case EDaedalusMuralToolAction::WashCell:
        Result = Painting->Wash(Focus.X(), Focus.Y());
        Notice = DaedalusMuralRestorationLocal::StrokeNotice(Result, Focus.PigmentIndex());
        break;
    case EDaedalusMuralToolAction::RevealCell:
    {
        EDaedalusPigment Pigment = EDaedalusPigment::Red;
        if (Painting->Reveal(Focus.X(), Focus.Y(), Pigment))
        {
            HintPigment = static_cast<int32>(Pigment);
            bHasHint = HintPigment >= 0 && HintPigment < 6;
        }
        if (!bHasHint) { Result = TEXT("LOCKED"); Notice = TEXT("Prism Sight needs learned Red, Yellow and Blue."); }
        break;
    }
    default: Result = TEXT("BAD_TOOL"); Notice = TEXT("This mural tool is unavailable."); break;
    }
    Refresh();
    return Result;
}

FString ADaedalusMuralRestorationConsole::ToolPrompt(EDaedalusMuralToolAction Action) const
{
    return DaedalusMuralRestorationLocal::ActionName(Action);
}

void ADaedalusMuralRestorationConsole::OnStroke(int32 X, int32 Y, const FString& Result)
{
    ClearHint();
    // The existing delegate carries no pigment identity. Only our own Paint call
    // can safely name which pot was empty; another caller may have used a different colour.
    Notice = X == Focus.X() && Y == Focus.Y()
        ? (Result == TEXT("NO_PIGMENT") ? TEXT("That pigment pot is empty.") : DaedalusMuralRestorationLocal::StrokeNotice(Result, Focus.PigmentIndex()))
        : TEXT("Another mural cell changed.");
    Refresh();
}
void ADaedalusMuralRestorationConsole::OnAwake(const FString&)
{
    ClearHint(); Notice = TEXT("Every cell is restored."); Refresh();
}

FString ADaedalusMuralRestorationConsole::ConsoleStatus() const
{
    if (!IsValid(Painting) || !Focus.Valid()) return TEXT("Mural restoration\nNo usable mural is connected.");
    const auto Selected = static_cast<EDaedalusPigment>(Focus.PigmentIndex());
    FString Text = FString::Printf(TEXT("Cell %d,%d of %d × %d\nSelected: %s (%d left)\nRestored: %.1f%%\nR %d  Y %d  B %d  O %d  G %d  V %d\nLearned:"),
        Focus.X() + 1, Focus.Y() + 1, Focus.Width(), Focus.Height(), DaedalusMuralRestorationLocal::Colour(Focus.PigmentIndex()),
        Painting->Units(Selected), Painting->ProgressPm() / 10.f,
        Painting->Units(EDaedalusPigment::Red), Painting->Units(EDaedalusPigment::Yellow), Painting->Units(EDaedalusPigment::Blue),
        Painting->Units(EDaedalusPigment::Orange), Painting->Units(EDaedalusPigment::Green), Painting->Units(EDaedalusPigment::Violet));
    bool bAnyLearned = false;
    for (int32 I = 0; I < 6; ++I)
        if (Painting->Knows(static_cast<EDaedalusPigment>(I))) { Text += TEXT(" "); Text += DaedalusMuralRestorationLocal::Colour(I); bAnyLearned = true; }
    if (!bAnyLearned) Text += TEXT(" none yet");
    if (bHasHint) Text += FString::Printf(TEXT("\nPrism Sight: this cell needs %s."), DaedalusMuralRestorationLocal::Colour(HintPigment));
    if (!Notice.IsEmpty()) Text += TEXT("\n") + Notice;
    Text += BorderMaterial ? TEXT("\nUse this console to paint the outlined cell.") : TEXT("\nCell outline unavailable. Use to paint the selected cell.");
    return Text;
}

void ADaedalusMuralRestorationConsole::Refresh()
{
    if (bEnding) return;
    const bool bReady = Synchronize();
    Readout->SetText(FText::FromString(DaedalusMuralRestorationLocal::WrapReadout(ConsoleStatus())));
    CellBorder->SetVisibility(bReady && BorderMaterial != nullptr);
    if (!bReady || !BorderMaterial) return;
    // Match the existing painting actor's own local cell layout, with no access to its hidden targets.
    const double Size = Painting->CellSize;
    const double CentreY = (Focus.X() + 0.5) * Size - Focus.Width() * Size * 0.5;
    const double CentreZ = Focus.Height() * Size - (Focus.Y() + 0.5) * Size;
    CellBorder->SetRelativeLocation(FVector(2.f, CentreY, CentreZ));
    const double Outer = Size * 0.49, Inner = Size * 0.46;
    TArray<FVector> Vertices;
    TArray<int32> Triangles;
    TArray<FVector> Normals;
    TArray<FLinearColor> Colours;
    auto Strip = [&](double Left, double Right, double Bottom, double Top)
    {
        const int32 Offset = Vertices.Num();
        Vertices.Append({FVector(0, Right, Top), FVector(0, Left, Top), FVector(0, Left, Bottom), FVector(0, Right, Bottom)});
        Triangles.Append({Offset, Offset + 1, Offset + 2, Offset, Offset + 2, Offset + 3});
        for (int32 I = 0; I < 4; ++I) { Normals.Add(FVector::ForwardVector); Colours.Add(FLinearColor::White); }
    };
    Strip(-Outer, Outer, Inner, Outer); Strip(-Outer, Outer, -Outer, -Inner);
    Strip(-Outer, -Inner, -Inner, Inner); Strip(Inner, Outer, -Inner, Inner);
    CellBorder->CreateMeshSection_LinearColor(0, Vertices, Triangles, Normals, TArray<FVector2D>(), Colours, TArray<FProcMeshTangent>(), false);
    CellBorder->SetMaterial(0, BorderMaterial);
}

ADaedalusMuralToolButton::ADaedalusMuralToolButton()
{
    PrimaryActorTick.bCanEverTick = false;
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded()) Body->SetStaticMesh(Cube.Object);
    Body->SetRelativeScale3D(FVector(0.2f, 0.5f, 0.5f));
    Glow->SetIntensity(0.f);
    Label = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Label"));
    Label->SetupAttachment(Body);
    Label->SetAbsolute(false, false, true);
    Label->SetRelativeLocation(FVector(60.f, 0.f, 60.f));
    Label->SetHorizontalAlignment(EHTA_Center);
    Label->SetWorldSize(12.f);
    Label->SetTextRenderColor(FColor(235, 240, 255));
}
void ADaedalusMuralToolButton::BeginPlay()
{
    Super::BeginPlay();
    Label->SetText(FText::FromString(DaedalusMuralRestorationLocal::ActionName(Action)));
}
FString ADaedalusMuralToolButton::Prompt(const ADaedalusHero*) const
{
    return IsValid(Console) ? Console->ToolPrompt(Action) : TEXT("Mural tool is not connected");
}
bool ADaedalusMuralToolButton::Use(ADaedalusHero*)
{
    if (!IsValid(Console)) return false;
    Console->PerformTool(Action);
    return true;
}
