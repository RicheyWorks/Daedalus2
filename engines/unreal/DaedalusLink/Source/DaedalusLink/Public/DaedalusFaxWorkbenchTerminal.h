// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusPhotoPdfCore.h"
#include "DaedalusFaxWorkbenchTerminal.generated.h"

class APlayerController;
class UGameViewportClient;
class SDaedalusSynapseWorkbenchPanel;
class UDaedalusFaxWorkbenchBridge;
class SWidget;

/** Private Fax Trident workbench, using its existing desktop-approved local role grant. */
UCLASS(Blueprintable)
class DAEDALUSLINK_API ADaedalusFaxWorkbenchTerminal : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusFaxWorkbenchTerminal();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    virtual void Tick(float DeltaSeconds) override;

    UFUNCTION(BlueprintCallable, Category="Daedalus|Practical Apps")
    bool PairLocalApp(const FString& Link);
    UFUNCTION(BlueprintCallable, Category="Daedalus|Practical Apps")
    void ClosePanel();
    bool AllowsNativeFileAction(uint64 ExpectedGeneration) const;
    uint64 GetDocumentGeneration() const;
    FString GetLocalMessage() const { return LocalMessage; }
    void SetLocalMessage(const FString& Message);

protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    bool CanUseLocally(const ADaedalusHero* Hero) const;
    bool HasLocalPanelOwner() const;
    UPROPERTY(Transient)
    TObjectPtr<UDaedalusFaxWorkbenchBridge> WorkspaceBridge;
    TSharedPtr<SDaedalusSynapseWorkbenchPanel> Panel;
    TSharedPtr<SWidget> PanelHost;
    TWeakPtr<SWidget> PreviousFocus;
    TWeakObjectPtr<ADaedalusHero> PanelHero;
    TWeakObjectPtr<APlayerController> PanelController;
    TWeakObjectPtr<UGameViewportClient> PanelViewport;
    FString PanelRealm;
    FString LocalMessage;
    uint64 PanelGeneration = 0;
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
