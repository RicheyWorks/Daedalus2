#include "OceanHttpProbe.h"
#include "Engine/World.h"
#include "ProceduralMeshComponent.h"
AOceanHttpProbe::AOceanHttpProbe() { PrimaryActorTick.bCanEverTick=true; }
void AOceanHttpProbe::BeginPlay()
{
    Super::BeginPlay();
    Origin=FPlatformMisc::GetEnvironmentVariable(TEXT("DAEDALUS_OCEAN_TEST_ORIGIN"));
    Token=FPlatformMisc::GetEnvironmentVariable(TEXT("DAEDALUS_OCEAN_TEST_TOKEN"));
    View=GetWorld()->SpawnActor<ADaedalusOceanSectorView>();
    Client=NewObject<UDaedalusOceanHostClient>(this);AddInstanceComponent(Client);Client->RegisterComponent();
    Client->OnChunk.AddDynamic(this,&AOceanHttpProbe::Received);
    Client->OnFailure.AddDynamic(this,&AOceanHttpProbe::Failed);
    if (!Client->ConfigureSession(Origin,Token) || !Client->RequestChunk(0,-1,0)) Stop();
}
void AOceanHttpProbe::Received(const FDaedalusOceanChunkView& Chunk)
{
    if (Phase==5)
    {
        bool Empty=Chunk.Blocks.Num()==4096;
        for (uint8 Value:Chunk.Blocks) Empty=Empty && Value==0;
        if (!Empty || Chunk.Revision<=4096 || !View->ApplyChunk(Chunk) || View->MeshForChunk(1,-1,0)) {Stop();return;}
        UE_LOG(LogTemp,Display,TEXT("OCEAN_NATIVE_CLEARED_MESH_REMOVED revision=%lld"),Chunk.Revision);
        UE_LOG(LogTemp,Display,TEXT("OCEAN_NATIVE_HTTP_PASS water=1 bounds404=1 jwt401=1 cancelled_reply_ignored=1 reconnect=1 cleared_revision=1"));
        FPlatformMisc::RequestExitWithStatus(false,0);return;
    }
    if (Chunk.Blocks.Num()!=4096 || Chunk.Palette[Chunk.Blocks[0]]!=TEXT("WATER")) {Stop();return;}
    if (!View || !View->ApplyChunk(Chunk) || View->TriangleCount(Chunk.X,Chunk.Y,Chunk.Z)<=0) {Stop();return;}
    auto* Mesh=View->MeshForChunk(Chunk.X,Chunk.Y,Chunk.Z);
    if (!Mesh || !Mesh->GetProcMeshSection(1) || Mesh->GetProcMeshSection(1)->bEnableCollision) {Stop();return;}
    if (Phase==0)
    {
        UE_LOG(LogTemp,Display,TEXT("OCEAN_NATIVE_HTTP_WATER"));Phase=1;
        UE_LOG(LogTemp,Display,TEXT("OCEAN_NATIVE_MESH_BUILT triangles=%d residents=%d water_collision=0"),
            View->TriangleCount(Chunk.X,Chunk.Y,Chunk.Z),View->ResidentCount());
        if (!Client->RequestChunk(99,-1,0)) Stop();
    }
    else if (Phase==4)
    {
        auto Old=Chunk;Old.X=1;Old.Revision=1;Old.Blocks.Init(static_cast<uint8>(Old.Palette.Find(TEXT("WATER"))),4096);
        if (!View->ApplyChunk(Old)) {Stop();return;}
        Phase=5;if (!Client->RequestChunk(1,-1,0)) Stop();
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
