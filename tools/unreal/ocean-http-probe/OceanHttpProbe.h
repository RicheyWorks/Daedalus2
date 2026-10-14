#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/GameModeBase.h"
#include "DaedalusOceanHostClient.h"
#include "DaedalusOceanSectorView.h"
#include "OceanHttpProbe.generated.h"
UCLASS()
class AOceanHttpProbe : public AActor
{
    GENERATED_BODY()
public:
    AOceanHttpProbe();
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
    UFUNCTION() void Received(const FDaedalusOceanChunkView& Chunk);
    UFUNCTION() void Failed(int32 Status,const FString& Reason);
private:
    UPROPERTY() TObjectPtr<UDaedalusOceanHostClient> Client;
    UPROPERTY() TObjectPtr<ADaedalusOceanSectorView> View;
    FString Origin,Token;
    int32 Phase=0;
    float Elapsed=0,Wait=0;
    void Stop();
};
UCLASS()
class AOceanHttpGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
};
