#pragma once
#include "DaedalusOrrery.h"
#include "DaedalusOceanDock.generated.h"

class ADaedalusOceanVessel;

/** Dock control point recognized by Hero's existing usable-object interaction. */
UCLASS()
class DAEDALUSLINK_API ADaedalusOceanDockControl : public ADaedalusUsable
{
    GENERATED_BODY()
public:
    ADaedalusOceanDockControl();
    virtual FString Prompt(const ADaedalusHero* Hero) const override;
    virtual bool Use(ADaedalusHero* Hero) override;
    bool ExitVessel(ADaedalusOceanVessel* OccupiedVessel);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Replicated, Category="Daedalus|Ocean") FString DockId;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Replicated, Category="Daedalus|Ocean") TObjectPtr<AActor> TravelHost;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Replicated, Category="Daedalus|Ocean") TObjectPtr<ADaedalusOceanVessel> Vessel;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Replicated, Category="Daedalus|Ocean") float InteractionReachCm=250;
};
