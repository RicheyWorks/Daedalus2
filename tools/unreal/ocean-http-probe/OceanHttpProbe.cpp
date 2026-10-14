#include "OceanHttpProbe.h"
#include "Engine/World.h"
#include "ProceduralMeshComponent.h"
#include "DaedalusOceanTravelComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Engine/StaticMeshActor.h"
#include "Components/LightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "ShaderCompiler.h"
#include "UnrealClient.h"
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
    if (Phase==10)
    {
        if (!View->ApplyChunk(Chunk)) {Stop();return;}
        RenderPending=false;RenderLoaded++;Wait=0;
        if (RenderLoaded==RenderKeys.Num()) {Phase=11;UE_LOG(LogTemp,Display,TEXT("OCEAN_RENDER_SECTOR_READY chunks=%d"),RenderLoaded);}
        return;
    }
    if (Phase==5)
    {
        bool Empty=Chunk.Blocks.Num()==4096;
        for (uint8 Value:Chunk.Blocks) Empty=Empty && Value==0;
        if (!Empty || Chunk.Revision<=4096 || !View->ApplyChunk(Chunk) || View->MeshForChunk(1,-1,0)) {Stop();return;}
        UE_LOG(LogTemp,Display,TEXT("OCEAN_NATIVE_CLEARED_MESH_REMOVED revision=%lld"),Chunk.Revision);
        UE_LOG(LogTemp,Display,TEXT("OCEAN_NATIVE_HTTP_PASS water=1 bounds404=1 jwt401=1 cancelled_reply_ignored=1 reconnect=1 cleared_revision=1"));
        if (FParse::Param(FCommandLine::Get(),TEXT("OceanRender"))) BeginRender();
        else FPlatformMisc::RequestExitWithStatus(false,0);
        return;
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
    if (Elapsed>(FParse::Param(FCommandLine::Get(),TEXT("OceanRender"))?150:20)) {Stop();return;}
    if (Phase==10 && !RenderPending)
    {
        Wait+=Delta;
        if (Wait>.075f)
        {
            const auto& Key=RenderKeys[RenderLoaded];RenderPending=true;
            if (!Client->RequestChunk(Key.X,Key.Y,Key.Z)) Stop();
        }
    }
    if (Phase==11)
    {
        Wait+=Delta;
        if (!LightingRecaptured && Wait>2 && (!GShaderCompilingManager || !GShaderCompilingManager->IsCompiling()))
        {RenderSkyLight->RecaptureSky();LightingRecaptured=true;Wait=0;}
        if (LightingRecaptured && !CaptureRequested && Wait>3 && (!GShaderCompilingManager || !GShaderCompilingManager->IsCompiling()))
        {CaptureRequested=true;FScreenshotRequest::RequestScreenshot(CapturePath,false,false);Wait=0;}
        else if (CaptureRequested && Wait>2 && FPaths::FileExists(CapturePath))
        {UE_LOG(LogTemp,Display,TEXT("OCEAN_RENDER_CAPTURED chunks=%d vessels=2"),RenderLoaded);FPlatformMisc::RequestExitWithStatus(false,0);}
    }
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
void AOceanHttpProbe::BeginRender()
{
    View->ClearChunks();
    View->OpaqueMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/DaedalusLink/Ocean/Materials/M_OceanOpaque.M_OceanOpaque"));
    View->WaterMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/DaedalusLink/Ocean/Materials/M_OceanWater.M_OceanWater"));
    auto* Skiff=LoadObject<UStaticMesh>(nullptr,TEXT("/DaedalusLink/Ocean/Vessels/Prop_Ocean_TideSkiff/Prop_Ocean_TideSkiff/StaticMeshes/Prop_Ocean_TideSkiff.Prop_Ocean_TideSkiff"));
    auto* Sub=LoadObject<UStaticMesh>(nullptr,TEXT("/DaedalusLink/Ocean/Vessels/Prop_Ocean_CoralSubmarine/Prop_Ocean_CoralSubmarine/StaticMeshes/Prop_Ocean_CoralSubmarine.Prop_Ocean_CoralSubmarine"));
    auto* Dock=LoadObject<UStaticMesh>(nullptr,TEXT("/DaedalusLink/Ocean/Vessels/Prop_Ocean_HarbourDock/Prop_Ocean_HarbourDock/StaticMeshes/Prop_Ocean_HarbourDock.Prop_Ocean_HarbourDock"));
    if (!View->OpaqueMaterial || !View->WaterMaterial || !Skiff || !Sub || !Dock) {Stop();return;}
    // Inclusive voxel pier cells span [-6,7] by [-3,4] metres.
    auto* DockActor=GetWorld()->SpawnActor<AStaticMeshActor>(FVector(50,50,100),FRotator::ZeroRotator);
    DockActor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);DockActor->GetStaticMeshComponent()->SetStaticMesh(Dock);
    DockActor->SetActorScale3D(FVector(13.f/12.f,7.f/6.f,1));
    DockActor->SetActorEnableCollision(false); // Existing voxel pier remains the collision source.
    UE_LOG(LogTemp,Display,TEXT("OCEAN_ART_BOUNDS skiff=%s submarine=%s dock=%s"),*Skiff->GetBoundingBox().GetSize().ToString(),*Sub->GetBoundingBox().GetSize().ToString(),*Dock->GetBoundingBox().GetSize().ToString());
    auto* Boat=GetWorld()->SpawnActor<ADaedalusOceanVessel>(FVector(-350,-650,100),FRotator(0,-25,0));
    Boat->SeaLevelCm=100;Boat->CurrentRealm=TEXT("Ocean Realm");Boat->VesselMesh->SetStaticMesh(Skiff);
    auto* Submarine=GetWorld()->SpawnActor<ADaedalusOceanVessel>(FVector(420,-650,60),FRotator(0,15,0));
    Submarine->SeaLevelCm=100;Submarine->CurrentRealm=TEXT("Ocean Realm");Submarine->VesselType=EDaedalusOceanVessel::Submarine;Submarine->VesselMesh->SetStaticMesh(Sub);
    auto* Light=GetWorld()->SpawnActor<ADirectionalLight>();Light->GetLightComponent()->SetMobility(EComponentMobility::Movable);Light->SetActorRotation(FRotator(-42,110,0));
    Light->GetLightComponent()->SetIntensity(4);Light->GetLightComponent()->SetLightColor(FLinearColor(1,.98f,.93f));
    auto* Soft=GetWorld()->SpawnActor<ADirectionalLight>();Soft->GetLightComponent()->SetMobility(EComponentMobility::Movable);Soft->SetActorRotation(FRotator(-28,-70,0));
    Soft->GetLightComponent()->SetIntensity(.8f);Soft->GetLightComponent()->SetCastShadows(false);Soft->GetLightComponent()->SetLightColor(FLinearColor(.55f,.75f,1));
    if (UClass* Sky=LoadClass<AActor>(nullptr,TEXT("/Engine/EngineSky/BP_Sky_Sphere.BP_Sky_Sphere_C"))) {
        auto* Sphere=GetWorld()->SpawnActor<AActor>(Sky);TArray<UStaticMeshComponent*> Components;Sphere->GetComponents(Components);
        auto* SkyMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/DaedalusLink/Ocean/Materials/M_OceanSky.M_OceanSky"));
        for (auto* Component:Components) Component->SetMaterial(0,SkyMaterial);
    }
    auto* Fill=GetWorld()->SpawnActor<ASkyLight>();RenderSkyLight=Fill->GetLightComponent();RenderSkyLight->SetMobility(EComponentMobility::Movable);RenderSkyLight->SetIntensity(1.2f);
    auto* Horizon=GetWorld()->SpawnActor<AStaticMeshActor>(FVector(0,0,98),FRotator::ZeroRotator);
    Horizon->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
    Horizon->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Plane.Plane")));
    Horizon->SetActorScale3D(FVector(600,600,1));Horizon->SetActorEnableCollision(false);
    auto* Backdrop=UMaterialInstanceDynamic::Create(View->WaterMaterial,Horizon);Backdrop->SetVectorParameterValue(TEXT("OceanTint"),FLinearColor(.028f,.216f,.687f));
    Horizon->GetStaticMeshComponent()->SetMaterial(0,Backdrop);Horizon->GetStaticMeshComponent()->SetTranslucentSortPriority(-1);
    auto* Camera=GetWorld()->SpawnActor<ACameraActor>();Camera->SetActorLocation(FVector(900,-2300,1450));
    Camera->SetActorRotation((FVector(0,-100,150)-Camera->GetActorLocation()).Rotation());Camera->GetCameraComponent()->SetFieldOfView(52);
    Camera->GetCameraComponent()->PostProcessSettings.bOverride_AutoExposureMethod=true;
    Camera->GetCameraComponent()->PostProcessSettings.AutoExposureMethod=AEM_Manual;
    Camera->GetCameraComponent()->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;
    Camera->GetCameraComponent()->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure=false;
    if (auto* Controller=GetWorld()->GetFirstPlayerController()) {if (Controller->GetPawn()) Controller->GetPawn()->SetActorHiddenInGame(true);Controller->SetViewTarget(Camera);}
    else {Stop();return;}
    CapturePath=FPlatformMisc::GetEnvironmentVariable(TEXT("DAEDALUS_OCEAN_RENDER_PATH"));
    if (CapturePath.IsEmpty()) {Stop();return;}
    for (int32 X=-2;X<=1;X++) for (int32 Y=-3;Y<=0;Y++) for (int32 Z=-2;Z<=1;Z++) RenderKeys.Add(FIntVector(X,Y,Z));
    Phase=10;Wait=0;
}
void AOceanHttpProbe::Stop()
{
    UE_LOG(LogTemp,Error,TEXT("OCEAN_NATIVE_HTTP_FAIL phase=%d"),Phase);FPlatformMisc::RequestExitWithStatus(false,1);
}
void AOceanHttpGameMode::BeginPlay()
{
    Super::BeginPlay();GetWorld()->SpawnActor<AOceanHttpProbe>();
}
