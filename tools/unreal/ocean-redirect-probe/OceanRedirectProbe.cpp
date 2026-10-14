#include "OceanRedirectProbe.h"
#include "Engine/World.h"
AOceanRedirectProbe::AOceanRedirectProbe()
{
    PrimaryActorTick.bCanEverTick=true;
    Client=CreateDefaultSubobject<UDaedalusOceanHostClient>(TEXT("OceanClient"));
}
void AOceanRedirectProbe::BeginPlay()
{
    Super::BeginPlay();
    Client->OnChunk.AddDynamic(this,&AOceanRedirectProbe::Received);
    Client->OnFailure.AddDynamic(this,&AOceanRedirectProbe::Failed);
    const FString Origin=FPlatformMisc::GetEnvironmentVariable(TEXT("DAEDALUS_REDIRECT_ORIGIN"));
    const FString Token=FPlatformMisc::GetEnvironmentVariable(TEXT("DAEDALUS_REDIRECT_TOKEN"));
    if (!Client->ConfigureSession(Origin,Token) || !Client->RequestChunk(0,0,0))
    {UE_LOG(LogTemp,Error,TEXT("OCEAN_REDIRECT_SETUP_FAILED"));FPlatformMisc::RequestExitWithStatus(false,1);}
}
void AOceanRedirectProbe::Received(const FDaedalusOceanChunkView& Chunk)
{
    if (Finished) return;Finished=true;
    UE_LOG(LogTemp,Display,TEXT("OCEAN_REDIRECT_PAYLOAD_ACCEPTED"));
    FPlatformMisc::RequestExitWithStatus(false,0);
}
void AOceanRedirectProbe::Failed(int32 Status,const FString& Reason)
{
    if (Finished) return;Finished=true;
    UE_LOG(LogTemp,Display,TEXT("OCEAN_REDIRECT_PAYLOAD_REFUSED status=%d"),Status);
    FPlatformMisc::RequestExitWithStatus(false,0);
}
void AOceanRedirectProbe::Tick(float Delta)
{
    Super::Tick(Delta);Elapsed+=Delta;
    if (!Finished && Elapsed>20)
    {Finished=true;UE_LOG(LogTemp,Error,TEXT("OCEAN_REDIRECT_TIMEOUT"));FPlatformMisc::RequestExitWithStatus(false,1);}
}
void AOceanRedirectGameMode::BeginPlay()
{
    Super::BeginPlay();GetWorld()->SpawnActor<AOceanRedirectProbe>();
}
