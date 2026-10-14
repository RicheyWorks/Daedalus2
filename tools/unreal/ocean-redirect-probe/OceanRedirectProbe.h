#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/GameModeBase.h"
#include "DaedalusOceanHostClient.h"
#include "OceanRedirectProbe.generated.h"
UCLASS()
class AOceanRedirectProbe : public AActor
{
    GENERATED_BODY()
public:
    AOceanRedirectProbe();
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
    UFUNCTION() void Received(const FDaedalusOceanChunkView& Chunk);
    UFUNCTION() void Failed(int32 Status,const FString& Reason);
private:
    UPROPERTY() TObjectPtr<UDaedalusOceanHostClient> Client;
    float Elapsed=0;
    bool Finished=false;
};
UCLASS()
class AOceanRedirectGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
};
