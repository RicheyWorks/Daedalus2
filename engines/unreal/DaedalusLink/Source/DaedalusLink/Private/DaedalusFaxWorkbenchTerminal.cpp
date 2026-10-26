// SPDX-License-Identifier: MIT
#include "DaedalusFaxWorkbenchTerminal.h"
#include "DaedalusFaxWorkbenchFiles.h"
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

namespace { TWeakObjectPtr<ADaedalusFaxWorkbenchTerminal> ActiveWorkbench; }

ADaedalusFaxWorkbenchTerminal::ADaedalusFaxWorkbenchTerminal()
{
    bReplicates = false;
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bTickEvenWhenPaused = true;
    Tags.Add(TEXT("DaedalusPracticalApp"));
    Tags.Add(TEXT("FaxWorkbenchTerminal"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded())
    {
        Body->SetStaticMesh(Cube.Object);
        Body->SetRelativeScale3D(FVector(0.7f, 0.45f, 0.35f));
    }
}

bool ADaedalusFaxWorkbenchTerminal::CanUseLocally(const ADaedalusHero* Hero) const
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

bool ADaedalusFaxWorkbenchTerminal::HasLocalPanelOwner() const
{
    const ADaedalusHero* Hero = PanelHero.Get();
    const APlayerController* Controller = PanelController.Get();
    return bPanelOpen && CanUseLocally(Hero) && Controller && Hero->GetController() == Controller
        && Controller->GetPawn() == Hero && Hero->RealmNow() == PanelRealm && PanelViewport.IsValid()
        && GetWorld()->GetGameViewport() == PanelViewport.Get()
        && Controller->GetLocalPlayer()->ViewportClient == PanelViewport.Get();
}

bool ADaedalusFaxWorkbenchTerminal::AllowsNativeFileAction(uint64 ExpectedGeneration) const
{
    return PanelGeneration == ExpectedGeneration && HasLocalPanelOwner() && Panel.IsValid() && Panel->HasApprovedDocument();
}
uint64 ADaedalusFaxWorkbenchTerminal::GetDocumentGeneration() const
{ return Panel.IsValid() ? Panel->GetDocumentGeneration() : 0; }

FString ADaedalusFaxWorkbenchTerminal::Prompt(const ADaedalusHero* Hero) const
{
    if (!CanUseLocally(Hero)) return TEXT("Fax private workbench requires your nearby local player (Windows)");
    return bPanelOpen ? TEXT("Close Fax private workbench") : TEXT("Use Fax private workbench");
}

bool ADaedalusFaxWorkbenchTerminal::Use(ADaedalusHero* Hero)
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
    LocalMessage = TEXT("Approve a separate USER workbench or ADMIN statistics grant in desktop Fax Trident, then paste its private link here.");
    ++PanelGeneration;
    WorkspaceBridge = NewObject<UDaedalusFaxWorkbenchBridge>(this);
    WorkspaceBridge->Initialize(this, PanelGeneration);
    const TWeakObjectPtr<ADaedalusFaxWorkbenchTerminal> WeakOwner(this);
    const TWeakObjectPtr<UDaedalusFaxWorkbenchBridge> WeakBridge(WorkspaceBridge.Get());
    TSharedRef<FDaedalusWorkbenchPanelCallbacks> Callbacks = MakeShared<FDaedalusWorkbenchPanelCallbacks>();
    Callbacks->IsOwnerValid = [WeakOwner] { const auto* Owner = WeakOwner.Get(); return Owner && Owner->HasLocalPanelOwner(); };
    Callbacks->Pair = [WeakOwner](const FString& Link) { auto* Owner = WeakOwner.Get(); return Owner && Owner->PairLocalApp(Link); };
    Callbacks->Close = [WeakOwner] { if (auto* Owner = WeakOwner.Get()) Owner->ClosePanel(); };
    Callbacks->Invalidate = [WeakBridge] { if (auto* Bridge = WeakBridge.Get()) Bridge->Invalidate(); };
    Callbacks->GetMessage = [WeakOwner] { const auto* Owner = WeakOwner.Get(); return Owner ? Owner->GetLocalMessage() : FString(TEXT("Workbench closed.")); };
    Callbacks->SetMessage = [WeakOwner](const FString& Message) { if (auto* Owner = WeakOwner.Get()) Owner->SetLocalMessage(Message); };
    SAssignNew(Panel, SDaedalusSynapseWorkbenchPanel).Profile(EDaedalusWorkbenchProfile::Fax)
        .NativeWorkspace(WorkspaceBridge.Get()).Callbacks(Callbacks);
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

void ADaedalusFaxWorkbenchTerminal::Tick(float DeltaSeconds)
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

void ADaedalusFaxWorkbenchTerminal::ClosePanel()
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

bool ADaedalusFaxWorkbenchTerminal::PairLocalApp(const FString& Link)
{
    const double PairStarted = FPlatformTime::Seconds();
    if (!HasLocalPanelOwner() || !Panel.IsValid() || !WorkspaceBridge || !Panel->Pair(Link)) return false;
    WorkspaceBridge->MarkPaired(PairStarted);
    return true;
}
void ADaedalusFaxWorkbenchTerminal::SetLocalMessage(const FString& Message) { LocalMessage = Message; }
void ADaedalusFaxWorkbenchTerminal::EndPlay(const EEndPlayReason::Type Reason)
{
    ClosePanel();
    Super::EndPlay(Reason);
}
