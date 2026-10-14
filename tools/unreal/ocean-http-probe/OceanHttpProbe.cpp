#include "OceanHttpProbe.h"
#include "Engine/World.h"
AOceanHttpProbe::AOceanHttpProbe() { PrimaryActorTick.bCanEverTick=true; }
void AOceanHttpProbe::BeginPlay()
{
    Super::BeginPlay();
    Origin=FPlatformMisc::GetEnvironmentVariable(TEXT("DAEDALUS_OCEAN_TEST_ORIGIN"));
    Token=FPlatformMisc::GetEnvironmentVariable(TEXT("DAEDALUS_OCEAN_TEST_TOKEN"));
    Client=NewObject<UDaedalusOceanHostClient>(this);AddInstanceComponent(Client);Client->RegisterComponent();
    Client->OnChunk.AddDynamic(this,&AOceanHttpProbe::Received);
    Client->OnFailure.AddDynamic(this,&AOceanHttpProbe::Failed);
    if (!Client->ConfigureSession(Origin,Token) || !Client->RequestChunk(0,-1,0)) Stop();
}
void AOceanHttpProbe::Received(const FDaedalusOceanChunkView& Chunk)
{
    if (Chunk.Blocks.Num()!=4096 || Chunk.Palette[Chunk.Blocks[0]]!=TEXT("WATER")) {Stop();return;}
    if (Phase==0)
    {
        UE_LOG(LogTemp,Display,TEXT("OCEAN_NATIVE_HTTP_WATER"));Phase=1;
        if (!Client->RequestChunk(99,-1,0)) Stop();
    }
    else if (Phase==4)
    {
        UE_LOG(LogTemp,Display,TEXT("OCEAN_NATIVE_HTTP_PASS water=1 bounds404=1 jwt401=1 cancelled_reply_ignored=1 reconnect=1"));
        FPlatformMisc::RequestExitWithStatus(false,0);
    }
    else Stop();
}
void AOceanHttpProbe::Failed(int32 Status,const FString& Reason)
{
    if (Phase==1 && Status==404)
    {
        Phase=2;UE_LOG(LogTemp,Display,TEXT("OCEAN_NATIVE_HTTP_BOUNDS404"));
        if (!Client->ConfigureSession(Origin,TEXT("invalid")) || !Client->RequestChunk(0,-1,0)) Stop();
    }
    else if (Phase==2 && Status==401)
    {
        Phase=3;UE_LOG(LogTemp,Display,TEXT("OCEAN_NATIVE_HTTP_JWT401"));
        if (!Client->ConfigureSession(Origin,Token) || !Client->RequestChunk(0,-1,0)) {Stop();return;}
        Client->ClearSession();
    }
    else Stop();
}
void AOceanHttpProbe::Tick(float Delta)
{
    Super::Tick(Delta);Elapsed+=Delta;
    if (Elapsed>20) {Stop();return;}
    if (Phase==3)
    {
        Wait+=Delta;
        if (Wait>.75f)
        {
            Phase=4;
            if (!Client->ConfigureSession(Origin,Token) || !Client->RequestChunk(0,-1,0)) Stop();
        }
    }
}
void AOceanHttpProbe::Stop()
{
    UE_LOG(LogTemp,Error,TEXT("OCEAN_NATIVE_HTTP_FAIL phase=%d"),Phase);FPlatformMisc::RequestExitWithStatus(false,1);
}
void AOceanHttpGameMode::BeginPlay()
{
    Super::BeginPlay();GetWorld()->SpawnActor<AOceanHttpProbe>();
}
