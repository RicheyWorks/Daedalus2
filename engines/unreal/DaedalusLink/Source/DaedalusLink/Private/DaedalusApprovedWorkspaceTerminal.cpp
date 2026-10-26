// SPDX-License-Identifier: MIT
#include "DaedalusApprovedWorkspaceTerminal.h"

#include "DaedalusHero.h"
#include "DaedalusPhotoPdfFiles.h"
#include "SDaedalusApprovedWorkspacePanel.h"
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

ADaedalusApprovedWorkspaceTerminal::ADaedalusApprovedWorkspaceTerminal()
{
    bReplicates = false;
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bTickEvenWhenPaused = true;
    Tags.Add(TEXT("DaedalusPracticalApp"));
    Tags.Add(TEXT("ApprovedWorkspaceTerminal"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded())
    {
        Body->SetStaticMesh(Cube.Object);
        Body->SetRelativeScale3D(FVector(0.75f, 0.55f, 0.3f));
    }
}

bool ADaedalusApprovedWorkspaceTerminal::CanUseLocally(const ADaedalusHero* Hero) const
{
    const UWorld* World = GetWorld();
    if (!IsInGameThread() || !World || World->IsPaused() || !IsValid(Hero) || IsActorBeingDestroyed()
        || !DaedalusPhotoPdfFiles::Supported()) return false;
    const APlayerController* Controller = Cast<APlayerController>(Hero->GetController());
    const bool bLocal = Hero->IsLocallyControlled() && Controller && Controller->IsLocalPlayerController()
        && Controller->GetPawn() == Hero && Controller->GetLocalPlayer()
        && !Hero->IsSettingsOpen() && !Hero->IsFieldOpen()
        && !Hero->IsInventoryOpen() && !Hero->IsRealmOpen() && !Hero->IsDialogueOpen();
    const float Reach = Hero->InteractReach;
    const double DistanceSquared = FVector::DistSquared(GetActorLocation(), Hero->GetActorLocation());
    const bool bNear = FMath::IsFinite(Reach) && Reach > 0.f && FMath::IsFinite(DistanceSquared)
        && DistanceSquared <= FMath::Square(FMath::Min(Reach, 1000.f));
    return daedalus::photopdf::CanUseChooser(World->IsGameWorld(), World->GetNetMode() == NM_DedicatedServer,
        bLocal, Hero->GetWorld() == World, bNear);
}

bool ADaedalusApprovedWorkspaceTerminal::HasLocalPanelOwner() const
{
    const ADaedalusHero* Hero = PanelHero.Get();
    const APlayerController* Controller = PanelController.Get();
    return bPanelOpen && BoundApplication == Application && CanUseLocally(Hero) && Controller && Hero->GetController() == Controller
        && Controller->GetPawn() == Hero && Hero->RealmNow() == PanelRealm
        && PanelViewport.IsValid() && GetWorld()->GetGameViewport() == PanelViewport.Get()
        && Controller->GetLocalPlayer()->ViewportClient == PanelViewport.Get();
}

FString ADaedalusApprovedWorkspaceTerminal::Prompt(const ADaedalusHero* Hero) const
{
    if (!CanUseLocally(Hero)) return TEXT("Approved workspace requires your nearby local player (Windows)");
    return bPanelOpen ? TEXT("Close approved workspace") : TEXT("Use approved desktop workspace");
}

bool ADaedalusApprovedWorkspaceTerminal::Use(ADaedalusHero* Hero)
{
    if (!CanUseLocally(Hero)) return false;
    if (bPanelOpen) { ClosePanel(); return true; }
    APlayerController* Controller = Cast<APlayerController>(Hero->GetController());
    ULocalPlayer* LocalPlayer = Controller->GetLocalPlayer();
    UGameViewportClient* Viewport = LocalPlayer->ViewportClient;
    if (!Viewport || Viewport != GetWorld()->GetGameViewport() || !FSlateApplication::IsInitialized()
        || !OpenGate.TryBegin(FPlatformTime::Seconds())) return false;
    const TSharedPtr<FSlateUser> SlateUser = LocalPlayer->GetSlateUser();
    if (!SlateUser.IsValid()) return false;
    PanelHero = Hero;
    PanelController = Controller;
    PanelViewport = Viewport;
    PanelRealm = Hero->RealmNow();
    BoundApplication = Application;
    SlateUserIndex = SlateUser->GetUserIndex();
    PreviousFocus = FSlateApplication::Get().GetUserFocusedWidget(SlateUserIndex);
    bPreviousCursor = Controller->bShowMouseCursor;
    bPreviousIgnoreInput = Viewport->IgnoreInput();
    bPreviousHideCursorDuringCapture = Viewport->HideCursorDuringCapture();
    PreviousCaptureMode = static_cast<int32>(Viewport->GetMouseCaptureMode());
    PreviousLockMode = static_cast<int32>(Viewport->GetMouseLockMode());
    LocalMessage.Reset();
    ++PanelGeneration;
    Client = MakeShared<FDaedalusApprovedWorkspaceClient, ESPMode::ThreadSafe>(Application == EDaedalusApprovedWorkspaceApp::PhotoPdf);
    SAssignNew(Panel, SDaedalusApprovedWorkspacePanel).Terminal(this);
    SAssignNew(PanelHost, SWeakWidget).PossiblyNullContent(Panel.ToSharedRef());
    Viewport->AddViewportWidgetContent(PanelHost.ToSharedRef(), 180);
    bPanelOpen = true;
    // UIOnly owns viewport input. Controller restart can reset ignore-input counters;
    // taking/decrementing them could consume a later pawn/overlay owner's state.
    bCaptureOwned = true;
    Controller->bShowMouseCursor = true;
    FInputModeUIOnly Mode;
    Mode.SetWidgetToFocus(Panel.ToSharedRef());
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    Controller->SetInputMode(Mode);
    FSlateApplication::Get().SetUserFocus(SlateUserIndex, Panel.ToSharedRef(), EFocusCause::SetDirectly);
    return true;
}

void ADaedalusApprovedWorkspaceTerminal::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bPanelOpen) return;
    if (!HasLocalPanelOwner()) { ClosePanel(); return; }
    if (FSlateApplication::IsInitialized() && Panel.IsValid())
    {
        const TSharedPtr<SWidget> Focus = FSlateApplication::Get().GetUserFocusedWidget(SlateUserIndex);
        if (Focus.IsValid() && !Panel->OwnsUserFocus(SlateUserIndex)) { ClosePanel(); return; }
    }
    if (Client.IsValid()) Client->Tick();
}

void ADaedalusApprovedWorkspaceTerminal::ClosePanel()
{
    if (!IsInGameThread()) return;
    const bool bOwnedFocus = Panel.IsValid() && FSlateApplication::IsInitialized()
        && Panel->OwnsUserFocus(SlateUserIndex);
    const bool bNoOtherFocus = FSlateApplication::IsInitialized()
        && !FSlateApplication::Get().GetUserFocusedWidget(SlateUserIndex).IsValid();
    if (Panel.IsValid()) Panel->ClearPairingInput();
    bPanelOpen = false;
    ++PanelGeneration;
    if (Client.IsValid()) Client->Shutdown(); // bounded best-effort LOCAL grant revoke, never a fake cleanup receipt
    Client.Reset();
    UGameViewportClient* Viewport = PanelViewport.Get();
    if (Viewport && PanelHost.IsValid()) Viewport->RemoveViewportWidgetContent(PanelHost.ToSharedRef());
    APlayerController* Controller = PanelController.Get();
    if (Controller && bCaptureOwned)
    {
        if (bOwnedFocus || bNoOtherFocus)
        {
            Controller->bShowMouseCursor = bPreviousCursor;
            // SetInputMode addresses the controller world's viewport. Never mutate a replacement.
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
    }
    // The opening controller may disappear while its viewport survives for a replacement player.
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
    bCaptureOwned = false;
    Panel.Reset(); PanelHost.Reset(); PreviousFocus.Reset();
    PanelHero.Reset(); PanelController.Reset(); PanelViewport.Reset(); PanelRealm.Reset(); LocalMessage.Reset();
}

FDaedalusApprovedWorkspaceView ADaedalusApprovedWorkspaceTerminal::GetView() const
{
    FDaedalusApprovedWorkspaceView View = Client.IsValid() ? Client->GetView() : FDaedalusApprovedWorkspaceView();
    if (!LocalMessage.IsEmpty()) View.Status = LocalMessage;
    return View;
}

void ADaedalusApprovedWorkspaceTerminal::SetLocalMessage(const FString& Message) { LocalMessage = Message; }

bool ADaedalusApprovedWorkspaceTerminal::PairLocalApp(const FString& Link)
{
    if (!HasLocalPanelOwner() || !Client.IsValid()) return false;
    LocalMessage.Reset();
    return Client->Pair(Link);
}

void ADaedalusApprovedWorkspaceTerminal::RefreshJob()
{
    if (HasLocalPanelOwner() && Client.IsValid()) { LocalMessage.Reset(); Client->Refresh(); }
}
void ADaedalusApprovedWorkspaceTerminal::CancelWorkspace()
{
    if (HasLocalPanelOwner() && Client.IsValid()) { ++PanelGeneration; LocalMessage.Reset(); Client->Cancel(); }
}
void ADaedalusApprovedWorkspaceTerminal::DisconnectApp()
{
    if (HasLocalPanelOwner() && Client.IsValid()) { ++PanelGeneration; LocalMessage.Reset(); Client->Disconnect(); }
}
void ADaedalusApprovedWorkspaceTerminal::EndPlay(const EEndPlayReason::Type Reason)
{
    ClosePanel();
    Super::EndPlay(Reason);
}

void ADaedalusApprovedWorkspaceTerminal::StartWorkspace()
{
    if (HasLocalPanelOwner() && Client.IsValid()) { LocalMessage.Reset(); Client->StartOrRetry(); }
}
FString ADaedalusApprovedWorkspaceTerminal::ApplicationLabel() const
{
    return Application == EDaedalusApprovedWorkspaceApp::PhotoPdf ? TEXT("Photo PDF approved workspace") : TEXT("Image Optimizer approved workspace");
}
