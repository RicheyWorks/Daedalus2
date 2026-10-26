#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DaedalusOceanInteractor.generated.h"

class ADaedalusHero;
class ADaedalusOceanDockControl;

/** Owned player RPC endpoint; no caller-supplied hero identity. */
UCLASS(ClassGroup=(Daedalus),meta=(BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusOceanInteractor : public UActorComponent
{
    GENERATED_BODY()
public:
    UDaedalusOceanInteractor();
    UFUNCTION(BlueprintCallable,BlueprintAuthorityOnly,Category="Daedalus|Ocean")
    static UDaedalusOceanInteractor* EnsureOnHero(ADaedalusHero* Hero);
    UFUNCTION(Server,Reliable,BlueprintCallable,Category="Daedalus|Ocean")
    void RequestDockUse(ADaedalusOceanDockControl* Dock);
};
