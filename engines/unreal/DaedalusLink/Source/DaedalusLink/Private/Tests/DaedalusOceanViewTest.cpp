#include "DaedalusOceanSectorView.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "ProceduralMeshComponent.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusOceanViewTest,"Daedalus.Ocean.SectorGeometry",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FDaedalusOceanViewTest::RunTest(const FString& Parameters)
{
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false);
    if (!TestNotNull(TEXT("Scratch world"),World)) return false;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    World->InitializeActorsForPlay(FURL());
    auto* View=World->SpawnActor<ADaedalusOceanSectorView>();
    FDaedalusOceanChunkView Left;Left.Palette={TEXT("AIR"),TEXT("STONE"),TEXT("WATER")};Left.Blocks.Init(1,4096);Left.Revision=1;
    TestTrue(TEXT("Apply solid chunk"),View->ApplyChunk(Left));
    TestEqual(TEXT("Greedy solid cube has 12 triangles"),View->TriangleCount(0,0,0),12);
    TestTrue(TEXT("Opaque collision enabled"),View->MeshForChunk(0,0,0)->GetProcMeshSection(0)->bEnableCollision);
    auto Right=Left;Right.X=1;
    TestTrue(TEXT("Apply adjacent chunk"),View->ApplyChunk(Right));
    TestEqual(TEXT("Left shared face removed"),View->TriangleCount(0,0,0),10);
    TestEqual(TEXT("Right shared face removed"),View->TriangleCount(1,0,0),10);
    TestTrue(TEXT("Remove adjacent chunk"),View->RemoveChunk(1,0,0));
    TestEqual(TEXT("Exposed face restored"),View->TriangleCount(0,0,0),12);
    auto Invalid=Left;Invalid.Blocks[0]=99;
    TestFalse(TEXT("Invalid payload preserves scene"),View->ApplyChunk(Invalid));
    TestEqual(TEXT("Prior geometry retained"),View->TriangleCount(0,0,0),12);
    auto Empty=Left;Empty.Blocks.Init(0,4096);Empty.Revision=2;
    TestTrue(TEXT("Cleared chunk accepted"),View->ApplyChunk(Empty));
    TestNull(TEXT("Cleared chunk removes mesh"),View->MeshForChunk(0,0,0));
    TestFalse(TEXT("Old revision cannot restore terrain"),View->ApplyChunk(Left));
    View->ClearChunks();View->MaxChunks=1;
    Left.X=-1;Left.Blocks.Init(2,4096);
    TestTrue(TEXT("Water chunk accepted"),View->ApplyChunk(Left));
    auto* Water=View->MeshForChunk(-1,0,0);
    TestTrue(TEXT("Water does not collide"),Water && Water->GetProcMeshSection(1) && !Water->GetProcMeshSection(1)->bEnableCollision);
    TestEqual(TEXT("Negative coordinate offset"),Water->GetRelativeLocation().X,-1600.0);
    TestFalse(TEXT("Capacity refusal"),View->ApplyChunk(Right));
    TestEqual(TEXT("Resident count bounded"),View->ResidentCount(),1);
    View->ClearChunks();Left.X=134217727;
    TestTrue(TEXT("Far chunk uses local meshing"),View->ApplyChunk(Left));
    auto* Far=View->MeshForChunk(Left.X,0,0);
    TestEqual(TEXT("Far offset remains double precision"),Far->GetRelativeLocation().X,static_cast<double>(Left.X)*1600);
    TestEqual(TEXT("Far cube still has 12 triangles"),View->TriangleCount(Left.X,0,0),12);
    View->ClearChunks();TestEqual(TEXT("Clear releases residents"),View->ResidentCount(),0);
    World->DestroyWorld(false);GEngine->DestroyWorldContext(World);return true;
}
#endif
