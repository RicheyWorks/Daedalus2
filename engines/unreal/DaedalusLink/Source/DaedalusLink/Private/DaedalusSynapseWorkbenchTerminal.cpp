// SPDX-License-Identifier: MIT
#include "DaedalusSynapseWorkbenchTerminal.h"
#include "DaedalusSynapseWorkbenchFiles.h"
#include "DaedalusHero.h"
#include "SDaedalusSynapseWorkbenchPanel.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "Framework/Application/SlateUser.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformTime.h"
#include "UObject/ConstructorHelpers.h"
#include "Widgets/SWeakWidget.h"

namespace { TWeakObjectPtr<ADaedalusSynapseWorkbenchTerminal> ActiveWorkbench; }

ADaedalusSynapseWorkbenchTerminal::ADaedalusSynapseWorkbenchTerminal()
{
    bReplicates = false;
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bTickEvenWhenPaused = true;
    Tags.Add(TEXT("DaedalusPracticalApp"));
    Tags.Add(TEXT("SynapseWorkbenchTerminal"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded())
    {
        Body->SetStaticMesh(Cube.Object);
        Body->SetRelativeScale3D(FVector(0.7f, 0.45f, 0.35f));
    }
}

bool ADaedalusSynapseWorkbenchTerminal::CanUseLocally(const ADaedalusHero* Hero) const
{
    const UWorld* World = GetWorld();
    if (!IsInGameThread() || !World || World->IsPaused() || !IsValid(Hero) || IsActorBeingDestroyed()
        || !DaedalusSynapseWorkbenchFiles::Supported()) return false;
    const APlayerController* Controller = Cast<APlayerController>(Hero->GetController());
    const bool bLocal = Hero->IsLocallyControlled() && Controller && Controller->IsLocalPlayerController()
        && Controller->GetPawn() == Hero && Controller->GetLocalPlayer()
        && !Hero->IsSettingsOpen() && !Hero->IsFieldOpen() && !Hero->IsInventoryOpen()
        && !Hero->IsRealmOpen() && !Hero->IsDialogueOpen();
    const float Reach = Hero->InteractReach;
    const double DistanceSquared = FVector::DistSquared(GetActorLocation(), Hero->GetActorLocation());
    const bool bNear = FMath::IsFinite(Reach) && Reach > 0.f && FMath::IsFinite(DistanceSquared)
        && DistanceSquared <= FMath::Square(FMath::Min(Reach, 1000.f));
    return daedalus::photopdf::CanUseChooser(World->IsGameWorld(), World->GetNetMode() == NM_DedicatedServer,
        bLocal, Hero->GetWorld() == World, bNear);
}

bool ADaedalusSynapseWorkbenchTerminal::HasLocalPanelOwner() const
{
    const ADaedalusHero* Hero = PanelHero.Get();
    const APlayerController* Controller = PanelController.Get();
    return bPanelOpen && CanUseLocally(Hero) && Controller && Hero->GetController() == Controller
        && Controller->GetPawn() == Hero && Hero->RealmNow() == PanelRealm && PanelViewport.IsValid()
        && GetWorld()->GetGameViewport() == PanelViewport.Get()
        && Controller->GetLocalPlayer()->ViewportClient == PanelViewport.Get();
}

bool ADaedalusSynapseWorkbenchTerminal::AllowsNativeFileAction(uint64 ExpectedGeneration) const
{
    return PanelGeneration == ExpectedGeneration && HasLocalPanelOwner() && Panel.IsValid() && Panel->HasApprovedDocument();
}

FString ADaedalusSynapseWorkbenchTerminal::Prompt(const ADaedalusHero* Hero) const
{
    if (!CanUseLocally(Hero)) return TEXT("Synapse workbench requires your nearby local player (Windows)");
    return bPanelOpen ? TEXT("Close Synapse workbench") : TEXT("Use Synapse workbench");
}

bool ADaedalusSynapseWorkbenchTerminal::Use(ADaedalusHero* Hero)
{
    if (!CanUseLocally(Hero)) return false;
    if (bPanelOpen) { ClosePanel(); return true; }
    if (ActiveWorkbench.IsValid() && ActiveWorkbench.Get() != this) return false;
    APlayerController* Controller = Cast<APlayerController>(Hero->GetController());
    ULocalPlayer* LocalPlayer = Controller->GetLocalPlayer();
    UGameViewportClient* Viewport = LocalPlayer->ViewportClient;
    if (!Viewport || Viewport != GetWorld()->GetGameViewport() || !FSlateApplication::IsInitialized()
        || !OpenGate.TryBegin(FPlatformTime::Seconds())) return false;
    const TSharedPtr<FSlateUser> SlateUser = LocalPlayer->GetSlateUser();
    if (!SlateUser.IsValid()) return false;
    PanelHero = Hero; PanelController = Controller; PanelViewport = Viewport; PanelRealm = Hero->RealmNow();
    SlateUserIndex = SlateUser->GetUserIndex();
    PreviousFocus = FSlateApplication::Get().GetUserFocusedWidget(SlateUserIndex);
    bPreviousCursor = Controller->bShowMouseCursor;
    bPreviousIgnoreInput = Viewport->IgnoreInput();
    bPreviousHideCursorDuringCapture = Viewport->HideCursorDuringCapture();
    PreviousCaptureMode = static_cast<int32>(Viewport->GetMouseCaptureMode());
    PreviousLockMode = static_cast<int32>(Viewport->GetMouseLockMode());
    LocalMessage = TEXT("Enable Realm workbench in desktop Synapse, choose its permissions, then paste its private link here.");
    ++PanelGeneration;
    WorkspaceBridge = NewObject<UDaedalusSynapseWorkbenchBridge>(this);
    WorkspaceBridge->Initialize(this, PanelGeneration);
    SAssignNew(Panel, SDaedalusSynapseWorkbenchPanel).Terminal(this).Workspace(WorkspaceBridge.Get());
    SAssignNew(PanelHost, SWeakWidget).PossiblyNullContent(Panel.ToSharedRef());
    Viewport->AddViewportWidgetContent(PanelHost.ToSharedRef(), 180);
    bPanelOpen = true; bCaptureOwned = true; ActiveWorkbench = this;
    Controller->bShowMouseCursor = true;
    FInputModeUIOnly Mode;
    Mode.SetWidgetToFocus(Panel.ToSharedRef());
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    Controller->SetInputMode(Mode);
    FSlateApplication::Get().SetUserFocus(SlateUserIndex, Panel.ToSharedRef(), EFocusCause::SetDirectly);
    return true;
}

void ADaedalusSynapseWorkbenchTerminal::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bPanelOpen) return;
    if (!HasLocalPanelOwner()) { ClosePanel(); return; }
    if (FSlateApplication::IsInitialized() && Panel.IsValid())
    {
        const TSharedPtr<SWidget> Focus = FSlateApplication::Get().GetUserFocusedWidget(SlateUserIndex);
        if (Focus.IsValid() && !Panel->OwnsUserFocus(SlateUserIndex)) ClosePanel();
    }
}

void ADaedalusSynapseWorkbenchTerminal::ClosePanel()
{
    if (!IsInGameThread()) return;
    const bool bOwnedFocus = Panel.IsValid() && FSlateApplication::IsInitialized() && Panel->OwnsUserFocus(SlateUserIndex);
    const bool bNoOtherFocus = FSlateApplication::IsInitialized()
        && !FSlateApplication::Get().GetUserFocusedWidget(SlateUserIndex).IsValid();
    bPanelOpen = false; ++PanelGeneration;
    if (WorkspaceBridge) WorkspaceBridge->Invalidate();
    if (Panel.IsValid()) { Panel->ClearPairingInput(); Panel->Shutdown(); }
    UGameViewportClient* Viewport = PanelViewport.Get();
    if (Viewport && PanelHost.IsValid()) Viewport->RemoveViewportWidgetContent(PanelHost.ToSharedRef());
    APlayerController* Controller = PanelController.Get();
    if (Controller && bCaptureOwned && (bOwnedFocus || bNoOtherFocus))
    {
        Controller->bShowMouseCursor = bPreviousCursor;
        if (Viewport && Controller->GetWorld() && Controller->GetWorld()->GetGameViewport() == Viewport)
        {
            if (bPreviousIgnoreInput)
            {
                FInputModeUIOnly Mode;
                if (PreviousFocus.IsValid()) Mode.SetWidgetToFocus(PreviousFocus.Pin());
                Controller->SetInputMode(Mode);
            }
            else if (bPreviousCursor)
            {
                FInputModeGameAndUI Mode;
                if (PreviousFocus.IsValid()) Mode.SetWidgetToFocus(PreviousFocus.Pin());
                Controller->SetInputMode(Mode);
            }
            else Controller->SetInputMode(FInputModeGameOnly());
        }
    }
    if (bCaptureOwned && (bOwnedFocus || bNoOtherFocus))
    {
        if (Viewport)
        {
            Viewport->SetIgnoreInput(bPreviousIgnoreInput);
            Viewport->SetHideCursorDuringCapture(bPreviousHideCursorDuringCapture);
            Viewport->SetMouseCaptureMode(static_cast<EMouseCaptureMode>(PreviousCaptureMode));
            Viewport->SetMouseLockMode(static_cast<EMouseLockMode>(PreviousLockMode));
        }
        if (PreviousFocus.IsValid() && FSlateApplication::IsInitialized())
            FSlateApplication::Get().SetUserFocus(SlateUserIndex, PreviousFocus.Pin(), EFocusCause::SetDirectly);
    }
    if (ActiveWorkbench.Get() == this) ActiveWorkbench.Reset();
    bCaptureOwned = false;
    WorkspaceBridge = nullptr;
    Panel.Reset(); PanelHost.Reset(); PreviousFocus.Reset();
    PanelHero.Reset(); PanelController.Reset(); PanelViewport.Reset(); PanelRealm.Reset(); LocalMessage.Reset();
}

bool ADaedalusSynapseWorkbenchTerminal::PairLocalApp(const FString& Link)
{
    return HasLocalPanelOwner() && Panel.IsValid() && Panel->Pair(Link);
}
void ADaedalusSynapseWorkbenchTerminal::SetLocalMessage(const FString& Message) { LocalMessage = Message; }
void ADaedalusSynapseWorkbenchTerminal::EndPlay(const EEndPlayReason::Type Reason)
{
    ClosePanel();
    Super::EndPlay(Reason);
}
