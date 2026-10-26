// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusPhotoPdfClient.h"
#include "DaedalusPhotoPdfCore.h"
#include "DaedalusPhotoPdfTerminal.generated.h"

class APlayerController;
class UGameViewportClient;
class SDaedalusPhotoPdfPanel;
class SWidget;

/** A local native interface to the existing PhotosToPDFPC job service. No converter, save-game
 * documents, replicated capabilities or automatic directory scans live in this actor.
 * New source is unverified until the sole native operator builds and binds this package.
 */
UCLASS(Blueprintable)
class DAEDALUSLINK_API ADaedalusPhotoPdfTerminal : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusPhotoPdfTerminal();
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

    FDaedalusPhotoPdfView GetView() const;
    void ChoosePhotos();
    void SubmitOrRetry();
    void RefreshJob();
    void CancelJob();
    void DisconnectApp();
    void ExportPdf(int32 Index);

protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    bool CanUseLocally(const ADaedalusHero* Hero) const;
    bool HasLocalPanelOwner() const;
    void SetLocalMessage(const FString& Message);

    // Ordinary runtime-only C++ state: not UPROPERTY, config, replication or transaction data.
    TSharedPtr<FDaedalusPhotoPdfClient, ESPMode::ThreadSafe> Client;
    TSharedPtr<SDaedalusPhotoPdfPanel> Panel;
    TSharedPtr<SWidget> PanelHost;
    TWeakPtr<SWidget> PreviousFocus;
    TWeakObjectPtr<ADaedalusHero> PanelHero;
    TWeakObjectPtr<APlayerController> PanelController;
    TWeakObjectPtr<UGameViewportClient> PanelViewport;
    FString PanelRealm;
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
