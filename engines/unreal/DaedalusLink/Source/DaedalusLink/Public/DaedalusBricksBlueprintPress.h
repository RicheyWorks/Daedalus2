// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusBricksBlueprintPrintCore.h"
#include "DaedalusBricksBlueprintPress.generated.h"

class ADaedalusBricksBlueprintPress;
class ADaedalusBricksBridgeWorkshop;
class ADaedalusBricksSkylineWorkshop;
class USceneComponent;
class UTextRenderComponent;
UENUM(BlueprintType)
enum class EDaedalusBlueprintPrintSource : uint8 { Bridge, Skyline };
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusBlueprintPressView, ADaedalusBricksBlueprintPress*, Press);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusBlueprintPrintKept, ADaedalusBricksBlueprintPress*, Press, FString, PrintId);

/** Explicit one-way local SVG export. Default null bindings are inactive.
 * Source kind/actor freeze on first successful print. No import, profile,
 * canonical reward, world-save, ownership or structural-safety authority. */
UCLASS()
class DAEDALUSLINK_API ADaedalusBricksBlueprintPress : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusBricksBlueprintPress();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Daedalus|BlueprintPress") EDaedalusBlueprintPrintSource SourceKind=EDaedalusBlueprintPrintSource::Bridge;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Daedalus|BlueprintPress") TObjectPtr<ADaedalusBricksBridgeWorkshop> Bridge;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Daedalus|BlueprintPress") TObjectPtr<ADaedalusBricksSkylineWorkshop> Skyline;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Daedalus|BlueprintPress") TObjectPtr<UTextRenderComponent> Readout;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|BlueprintPress") FDaedalusBlueprintPressView OnViewChanged;
    /** Only after fresh-file write/flush/close and exact bounded readback. */
    UPROPERTY(BlueprintAssignable, Category="Daedalus|BlueprintPress") FDaedalusBlueprintPrintKept OnPrintKept;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY() TObjectPtr<USceneComponent> PressRoot;
    UPROPERTY(Transient, DuplicateTransient) TWeakObjectPtr<AActor> FrozenSource;
    EDaedalusBlueprintPrintSource FrozenKind=EDaedalusBlueprintPrintSource::Bridge;
    std::string LastPrintId;
    FString LastFilename,Notice;
    uint64 Epoch=0;
    bool bEnding=false,bBusy=false,bNotifying=false,bFrozen=false;
    bool Alive() const;
    bool ViewsReady() const;
    AActor* ChosenSource() const;
    bool SourceReady() const;
    void Refresh(const FString& KeptId=FString());
};
