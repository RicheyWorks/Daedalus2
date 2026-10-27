#include "DaedalusExplorationTerrain.h"
#include "DaedalusExplorationTerrainCore.h"
#include "ProceduralMeshComponent.h"
#include "KismetProceduralMeshLibrary.h"

#if WITH_EDITOR
#include "Engine/Level.h"
#include "Engine/World.h"
#include "HAL/PlatformTime.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

namespace
{
// Opt-in read-only diagnostic. This spans this native OnConstruction override,
// not the whole enclosing RerunConstructionScripts scope. No terrain logic changes.
class FTerrainConstructionDiagnostic final
{
public:
    explicit FTerrainConstructionDiagnostic(const AActor& Actor)
    {
        static const bool bRequested = FParse::Param(FCommandLine::Get(), TEXT("DaedalusTraceTerrain"));
        static uint32 Admitted = 0; // game thread only, at most eight records/process
        if (!bRequested || !IsInGameThread() || Admitted >= 8) return;
        const UWorld* World = Actor.GetWorld();
        const ULevel* Level = Actor.GetLevel();
        if (!World || !Level || World->IsGameWorld() ||
            World->GetPathName() != TEXT("/Game/Daedalus/DaedalusWorld.DaedalusWorld")) return;
        ActorPath = Actor.GetPathName();
        ClassPath = Actor.GetClass()->GetPathName();
        LevelPath = Level->GetPathName();
        for (const FString* Name : {&ActorPath, &ClassPath, &LevelPath})
            if (Name->Len() > 1024 || Name->Contains(TEXT("\r")) || Name->Contains(TEXT("\n"))) return;
        Id = ++Admitted;
        Start = FPlatformTime::Seconds();
#if CPUPROFILERTRACE_ENABLED
        bCpuStarted = TRACE_CPUPROFILER_EVENT_MANUAL_IS_ENABLED();
        if (bCpuStarted)
            FCpuProfilerTrace::OutputBeginDynamicEvent(*(TEXT("DaedalusTerrainNative:") + ActorPath), __FILE__, __LINE__);
#endif
        Emit(TEXT("BEGIN"), 0.0);
    }
    ~FTerrainConstructionDiagnostic()
    {
        if (!Id) return;
        const double Duration = FPlatformTime::Seconds() - Start;
#if CPUPROFILERTRACE_ENABLED
        if (bCpuStarted) FCpuProfilerTrace::OutputEndEvent();
#endif
        Emit(TEXT("END"), Duration);
    }
    FTerrainConstructionDiagnostic(const FTerrainConstructionDiagnostic&) = delete;
    FTerrainConstructionDiagnostic& operator=(const FTerrainConstructionDiagnostic&) = delete;
private:
    static FString Csv(const FString& Value) { return TEXT("\"") + Value.Replace(TEXT("\""), TEXT("\"\"")) + TEXT("\""); }
    void Emit(const TCHAR* Event, double Duration) const
    {
        UE_LOG(LogTemp, Display, TEXT("TERRAIN_NATIVE_ATTR_V1,%s,%u,%.9f,%.9f,%d,%s,%s,%s"),
            Event, Id, Start, Duration, bCpuStarted ? 1 : 0, *Csv(ActorPath), *Csv(ClassPath), *Csv(LevelPath));
    }
    uint32 Id = 0;
    double Start = 0.0;
    bool bCpuStarted = false;
    FString ActorPath, ClassPath, LevelPath;
};
}
#endif

ADaedalusExplorationTerrain::ADaedalusExplorationTerrain()
{
    PrimaryActorTick.bCanEverTick=false;
    Surface=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("TerrainSurface"));
    SetRootComponent(Surface);
    Surface->bUseComplexAsSimpleCollision=true;
    Surface->SetCollisionProfileName(TEXT("BlockAll"));
}

void ADaedalusExplorationTerrain::OnConstruction(const FTransform& Transform)
{
#if WITH_EDITOR
    FTerrainConstructionDiagnostic Diagnostic(*this);
#endif
    Super::OnConstruction(Transform);
    Surface->ClearAllMeshSections();
    // Editor metadata is advisory; reject invalid programmatic inputs as well.
    if (Cells<1 || Cells>256 || !FMath::IsFinite(SpacingMetres)
        || SpacingMetres<0.1 || SpacingMetres>100.0
        || !FMath::IsFinite(SampleOriginMetres.X) || !FMath::IsFinite(SampleOriginMetres.Y)
        || FMath::Abs(SampleOriginMetres.X)>1.e8 || FMath::Abs(SampleOriginMetres.Y)>1.e8)
        return;
    using namespace DaedalusExplorationTerrain;
    const auto Patch=Build(bOcean?Realm::Ocean:Realm::Prairie,
                          SampleOriginMetres.X,SampleOriginMetres.Y,
                          static_cast<unsigned>(Cells),SpacingMetres);
    TArray<FVector> Vertices,Normals;
    TArray<int32> Indices;
    TArray<FVector2D> UVs;
    TArray<FProcMeshTangent> Tangents;
    for (const auto& V:Patch.Vertices)
    {
        Vertices.Add(FVector((V.X-SampleOriginMetres.X)*100.0,
                            (V.Y-SampleOriginMetres.Y)*100.0,V.Z*100.0));
        UVs.Add(FVector2D(V.X/4.0,V.Y/4.0));
    }
    // Core uses mathematical CCW; Unreal rendering uses the reverse winding.
    for (std::size_t I=0;I<Patch.Indices.size();I+=3)
    {
        Indices.Add(static_cast<int32>(Patch.Indices[I]));
        Indices.Add(static_cast<int32>(Patch.Indices[I+2]));
        Indices.Add(static_cast<int32>(Patch.Indices[I+1]));
    }
    UKismetProceduralMeshLibrary::CalculateTangentsForMesh(Vertices,Indices,UVs,Normals,Tangents);
    for (int32 I=0;I<Vertices.Num();++I)
    {
        const auto& V=Patch.Vertices[static_cast<std::size_t>(I)];
        const auto N=SurfaceNormal(bOcean?Realm::Ocean:Realm::Prairie,V.X,V.Y);
        Normals[I]=FVector(N.X,N.Y,N.Z);
        // Increasing world U follows +X projected onto the terrain tangent plane.
        const FVector T=(FVector::ForwardVector-Normals[I]*Normals[I].X).GetSafeNormal();
        Tangents[I]=FProcMeshTangent(T,false);
    }
    Surface->CreateMeshSection_LinearColor(0,Vertices,Indices,Normals,UVs,TArray<FLinearColor>(),Tangents,true);
    if (SurfaceMaterial) Surface->SetMaterial(0,SurfaceMaterial);
}
