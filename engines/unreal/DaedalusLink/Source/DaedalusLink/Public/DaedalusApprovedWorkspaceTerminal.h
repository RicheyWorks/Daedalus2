// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusApprovedWorkspaceClient.h"
#include "DaedalusLocalAppCore.h"
#include "DaedalusApprovedWorkspaceTerminal.generated.h"

UENUM(BlueprintType)
enum class EDaedalusApprovedWorkspaceApp : uint8 { PhotoPdf, ImageOptimizer };

class APlayerController;
class UGameViewportClient;
class SDaedalusApprovedWorkspacePanel;
class SWidget;

/** A local native controller for one desktop-approved Photo PDF or Image Optimizer plan. No save-game
 * documents, replicated capabilities or automatic directory scans live in this actor.
 * New source is unverified until the sole native operator builds and binds this package.
 */
UCLASS(Blueprintable)
class DAEDALUSLINK_API ADaedalusApprovedWorkspaceTerminal : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusApprovedWorkspaceTerminal();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    virtual void Tick(float DeltaSeconds) override;

    /** Only accepted in this local player's open panel; never set a pairing on a class default. */
    UFUNCTION(BlueprintCallable, Category="Daedalus|Practical Apps")
    bool PairLocalApp(const FString& Link);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Practical Apps")
    void ClosePanel();
    UFUNCTION(BlueprintPure, Category="Daedalus|Practical Apps")
    bool IsPanelOpen() const { return bPanelOpen; }

    FDaedalusApprovedWorkspaceView GetView() const;
    void RefreshJob();
    void CancelWorkspace();
    void DisconnectApp();
    void StartWorkspace();
    FString ApplicationLabel() const;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Daedalus|Practical Apps")
    EDaedalusApprovedWorkspaceApp Application = EDaedalusApprovedWorkspaceApp::PhotoPdf;

protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    bool CanUseLocally(const ADaedalusHero* Hero) const;
    bool HasLocalPanelOwner() const;
    void SetLocalMessage(const FString& Message);

    // Ordinary runtime-only C++ state: not UPROPERTY, config, replication or transaction data.
    TSharedPtr<FDaedalusApprovedWorkspaceClient, ESPMode::ThreadSafe> Client;
    TSharedPtr<SDaedalusApprovedWorkspacePanel> Panel;
    TSharedPtr<SWidget> PanelHost;
    TWeakPtr<SWidget> PreviousFocus;
    TWeakObjectPtr<ADaedalusHero> PanelHero;
    TWeakObjectPtr<APlayerController> PanelController;
    TWeakObjectPtr<UGameViewportClient> PanelViewport;
    FString PanelRealm;
    EDaedalusApprovedWorkspaceApp BoundApplication = EDaedalusApprovedWorkspaceApp::PhotoPdf;
    FString LocalMessage;
    bool bPanelOpen = false;
    bool bCaptureOwned = false;
    bool bPreviousCursor = false;
    bool bPreviousIgnoreInput = false;
    bool bPreviousHideCursorDuringCapture = false;
    uint64 PanelGeneration = 0;
    int32 SlateUserIndex = 0;
    int32 PreviousCaptureMode = 0;
    int32 PreviousLockMode = 0;
    daedalus::photopdf::LaunchGate OpenGate;
};
