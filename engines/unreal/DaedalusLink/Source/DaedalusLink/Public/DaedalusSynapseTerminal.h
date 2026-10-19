// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusLocalAppCore.h"
#include "DaedalusSynapseClient.h"
#include "DaedalusSynapseTerminal.generated.h"

class APlayerController;
class UGameViewportClient;
class SDaedalusSynapsePanel;
class SWidget;

/** Local selected-track interface to the running Synapse app. Source-only and unverified.
 * No vault, scheduler, review simulation, replicated data or saved capabilities live here.
 */
UCLASS(Blueprintable)
class DAEDALUSLINK_API ADaedalusSynapseTerminal : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusSynapseTerminal();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    virtual void Tick(float DeltaSeconds) override;

    UFUNCTION(BlueprintCallable, Category="Daedalus|Practical Apps")
    bool PairLocalApp(const FString& Link);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Practical Apps")
    void ClosePanel();
    UFUNCTION(BlueprintPure, Category="Daedalus|Practical Apps")
    bool IsPanelOpen() const { return bPanelOpen; }

    FDaedalusSynapseView GetView() const;
    void RefreshCards();
    void RevealCard();
    void ScoreCard(int32 Score);
    void RetrySameSave();
    void DisconnectApp();

protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    bool CanUseLocally(const ADaedalusHero* Hero) const;
    bool HasLocalPanelOwner() const;

    // Runtime-only local state. Never config, UPROPERTY, replication or transaction data.
    TSharedPtr<FDaedalusSynapseClient, ESPMode::ThreadSafe> Client;
    TSharedPtr<SDaedalusSynapsePanel> Panel;
    TSharedPtr<SWidget> PanelHost;
    TWeakPtr<SWidget> PreviousFocus;
    TWeakObjectPtr<ADaedalusHero> PanelHero;
    TWeakObjectPtr<APlayerController> PanelController;
    TWeakObjectPtr<UGameViewportClient> PanelViewport;
    FString PanelRealm;
    bool bPanelOpen = false;
    bool bCaptureOwned = false;
    bool bPreviousCursor = false;
    bool bPreviousIgnoreInput = false;
    bool bPreviousHideCursorDuringCapture = false;
    int32 SlateUserIndex = 0;
    int32 PreviousCaptureMode = 0;
    int32 PreviousLockMode = 0;
    daedalus::photopdf::LaunchGate OpenGate;
};
