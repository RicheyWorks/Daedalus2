#pragma once
#include "DaedalusOrrery.h"
#include "DaedalusOceanDock.generated.h"

class ADaedalusOceanVessel;

/** Dock control point recognized by Hero's existing usable-object interaction. */
UCLASS()
class DAEDALUSLINK_API ADaedalusOceanDock : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusOceanDock();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Daedalus|Ocean") FString DockId;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Daedalus|Ocean") TObjectPtr<AActor> TravelHost;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Daedalus|Ocean") TObjectPtr<ADaedalusOceanVessel> Vessel;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Daedalus|Ocean") float InteractionReachCm=250;
};
