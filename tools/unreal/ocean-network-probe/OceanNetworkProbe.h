// Test fixture only. Copy into an isolated validation module, never a game build.
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "OceanNetworkProbe.generated.h"

UCLASS()
class AOceanProbeController : public APlayerController
{
    GENERATED_BODY()
public:
    AOceanProbeController();
    virtual void Tick(float Dt) override;
private:
    float Elapsed=0;
    float AttackClock=0;
    bool AttackLogged=false;
    bool IdentityLogged=false;
    bool KeysPressed=false;
    bool KeysReleased=false;
    bool DockRequested=false;
    bool BoardClientLogged=false;
};

UCLASS()
class AOceanProbeGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AOceanProbeGameMode();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    virtual APawn* SpawnDefaultPawnAtTransform_Implementation(AController* Player, const FTransform& Transform) override;
private:
    float Elapsed=0;
    float StillTime=0;
    FVector Previous=FVector::ZeroVector;
    bool Moved=false;
    TWeakObjectPtr<class ADaedalusOceanVessel> Target;
    TWeakObjectPtr<class ADaedalusHero> DockHero;
    float BoardTime=0;
};
