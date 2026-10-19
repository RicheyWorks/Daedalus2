// SPDX-License-Identifier: MIT
#include "DaedalusSynapseTerminal.h"

#include "DaedalusHero.h"
#include "SDaedalusSynapsePanel.h"
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

ADaedalusSynapseTerminal::ADaedalusSynapseTerminal()
{
    bReplicates = false;
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bTickEvenWhenPaused = true;
    Tags.Add(TEXT("DaedalusPracticalApp"));
    Tags.Add(TEXT("SynapseStudyTerminal"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded())
    {
        Body->SetStaticMesh(Cube.Object);
        Body->SetRelativeScale3D(FVector(0.7f, 0.45f, 0.35f));
    }
}

bool ADaedalusSynapseTerminal::CanUseLocally(const ADaedalusHero* Hero) const
{
    const UWorld* World = GetWorld();
    if (!IsInGameThread() || !World || World->IsPaused() || !IsValid(Hero) || IsActorBeingDestroyed()) return false;
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

bool ADaedalusSynapseTerminal::HasLocalPanelOwner() const
{
    const ADaedalusHero* Hero = PanelHero.Get();
    const APlayerController* Controller = PanelController.Get();
    return bPanelOpen && CanUseLocally(Hero) && Controller && Hero->GetController() == Controller
        && Controller->GetPawn() == Hero && Hero->RealmNow() == PanelRealm && PanelViewport.IsValid()
        && GetWorld()->GetGameViewport() == PanelViewport.Get()
        && Controller->GetLocalPlayer()->ViewportClient == PanelViewport.Get();
}

FString ADaedalusSynapseTerminal::Prompt(const ADaedalusHero* Hero) const
{
    if (!CanUseLocally(Hero)) return TEXT("Synapse study desk requires your nearby local player");
    return bPanelOpen ? TEXT("Close Synapse study desk") : TEXT("Use Synapse study desk");
}

bool ADaedalusSynapseTerminal::Use(ADaedalusHero* Hero)
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
    SlateUserIndex = SlateUser->GetUserIndex();
    PreviousFocus = FSlateApplication::Get().GetUserFocusedWidget(SlateUserIndex);
    bPreviousCursor = Controller->bShowMouseCursor;
    bPreviousIgnoreInput = Viewport->IgnoreInput();
    bPreviousHideCursorDuringCapture = Viewport->HideCursorDuringCapture();
    PreviousCaptureMode = static_cast<int32>(Viewport->GetMouseCaptureMode());
    PreviousLockMode = static_cast<int32>(Viewport->GetMouseLockMode());
    Client = MakeShared<FDaedalusSynapseClient, ESPMode::ThreadSafe>();
    SAssignNew(Panel, SDaedalusSynapsePanel).Terminal(this);
    SAssignNew(PanelHost, SWeakWidget).PossiblyNullContent(Panel.ToSharedRef());
    Viewport->AddViewportWidgetContent(PanelHost.ToSharedRef(), 180);
    bPanelOpen = true;
    // UIOnly owns viewport input. Controller restart can reset ignore-input counters;
    // taking/decrementing those counters could consume a later pawn/overlay owner's state.
    bCaptureOwned = true;
    Controller->bShowMouseCursor = true;
    FInputModeUIOnly Mode;
    Mode.SetWidgetToFocus(Panel.ToSharedRef());
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    Controller->SetInputMode(Mode);
    FSlateApplication::Get().SetUserFocus(SlateUserIndex, Panel.ToSharedRef(), EFocusCause::SetDirectly);
    return true;
}

void ADaedalusSynapseTerminal::Tick(float DeltaSeconds)
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

void ADaedalusSynapseTerminal::ClosePanel()
{
    if (!IsInGameThread()) return;
    const bool bOwnedFocus = Panel.IsValid() && FSlateApplication::IsInitialized() && Panel->OwnsUserFocus(SlateUserIndex);
    const bool bNoOtherFocus = FSlateApplication::IsInitialized()
        && !FSlateApplication::Get().GetUserFocusedWidget(SlateUserIndex).IsValid();
    if (Panel.IsValid()) Panel->ClearPairingInput();
    bPanelOpen = false;
    // This stops UI delivery and asks for revocation; it cannot undo an atomic review save.
    if (Client.IsValid()) Client->Shutdown();
    Client.Reset();
    UGameViewportClient* Viewport = PanelViewport.Get();
    if (Viewport && PanelHost.IsValid()) Viewport->RemoveViewportWidgetContent(PanelHost.ToSharedRef());
    APlayerController* Controller = PanelController.Get();
    if (Controller && bCaptureOwned)
    {
        if (bOwnedFocus || bNoOtherFocus)
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
    }
    // The opening controller may be destroyed while its viewport survives for the next player.
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
    PanelHero.Reset(); PanelController.Reset(); PanelViewport.Reset(); PanelRealm.Reset();
}

FDaedalusSynapseView ADaedalusSynapseTerminal::GetView() const
{
    return Client.IsValid() ? Client->GetView() : FDaedalusSynapseView();
}

bool ADaedalusSynapseTerminal::PairLocalApp(const FString& Link)
{
    return HasLocalPanelOwner() && Client.IsValid() && Client->Pair(Link);
}
void ADaedalusSynapseTerminal::RefreshCards()
{
    if (HasLocalPanelOwner() && Client.IsValid()) Client->Refresh();
}
void ADaedalusSynapseTerminal::RevealCard()
{
    if (HasLocalPanelOwner() && Client.IsValid()) Client->Reveal();
}
void ADaedalusSynapseTerminal::ScoreCard(int32 Score)
{
    if (HasLocalPanelOwner() && Client.IsValid()) Client->Score(Score);
}
void ADaedalusSynapseTerminal::RetrySameSave()
{
    if (HasLocalPanelOwner() && Client.IsValid()) Client->RetrySameSave();
}
void ADaedalusSynapseTerminal::DisconnectApp()
{
    if (HasLocalPanelOwner() && Client.IsValid()) Client->Disconnect();
}
void ADaedalusSynapseTerminal::EndPlay(const EEndPlayReason::Type Reason)
{
    ClosePanel();
    Super::EndPlay(Reason);
}
