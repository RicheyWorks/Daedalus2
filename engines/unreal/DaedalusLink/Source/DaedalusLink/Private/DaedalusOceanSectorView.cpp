#include "DaedalusOceanSectorView.h"
#include "DaedalusMeshCore.h"
#include "ProceduralMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Materials/MaterialInterface.h"
#include "DaedalusOceanPalette.inl"

namespace
{
const FIntVector Neighbours[]={FIntVector(1,0,0),FIntVector(-1,0,0),FIntVector(0,1,0),FIntVector(0,-1,0),FIntVector(0,0,1),FIntVector(0,0,-1)};
const DaedalusOceanPalette::Entry* FindType(const FString& Name)
{
    for (const auto& Entry:DaedalusOceanPalette::Entries) if (Name==UTF8_TO_TCHAR(Entry.Name)) return &Entry;
    return nullptr;
}
}
ADaedalusOceanSectorView::ADaedalusOceanSectorView()
{
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("OceanRoot"));
}
bool ADaedalusOceanSectorView::ApplyChunk(const FDaedalusOceanChunkView& Chunk)
{
    if (!IsInGameThread() || !GetWorld() || MaxChunks<1 || MaxChunks>256 || Chunk.Blocks.Num()!=4096
        || Chunk.Palette.IsEmpty() || Chunk.Palette.Num()>256 || Chunk.Palette[0]!=TEXT("AIR") || Chunk.Revision<0) return false;
    for (int32 Axis:{Chunk.X,Chunk.Y,Chunk.Z}) if (Axis<-134217728 || Axis>134217727) return false;
    TSet<FString> Names;
    for (const FString& Name:Chunk.Palette) { if (!FindType(Name) || Names.Contains(Name)) return false;Names.Add(Name); }
    for (uint8 Type:Chunk.Blocks) if (Type>=Chunk.Palette.Num()) return false;
    const FIntVector Key(Chunk.X,Chunk.Y,Chunk.Z);
    if (!Chunks.Contains(Key) && Chunks.Num()>=MaxChunks) return false;
    if (!PaletteNames.IsEmpty() && PaletteNames!=Chunk.Palette) return false;
    if (const auto* Previous=Chunks.Find(Key)) {
        if (Chunk.Revision<Previous->Revision) return false;
        if (Chunk.Revision==Previous->Revision) return Chunk.Blocks==Previous->Blocks;
    }
    PaletteNames=Chunk.Palette;Chunks.Add(Key,Chunk);Rebuild(Key);RebuildNeighbours(Key);return true;
}
bool ADaedalusOceanSectorView::RemoveChunk(int32 X,int32 Y,int32 Z)
{
    const FIntVector Key(X,Y,Z);
    if (!Chunks.Remove(Key)) return false;
    DropMesh(Key);RebuildNeighbours(Key);if (Chunks.IsEmpty()) PaletteNames.Empty();return true;
}
void ADaedalusOceanSectorView::ClearChunks()
{
    TArray<FIntVector> Keys;Meshes.GetKeys(Keys);for (const auto& Key:Keys) DropMesh(Key);
    Chunks.Empty();PaletteNames.Empty();
}
void ADaedalusOceanSectorView::DropMesh(const FIntVector& Key)
{
    if (auto* Mesh=MeshForChunk(Key.X,Key.Y,Key.Z)) Mesh->DestroyComponent();
    Meshes.Remove(Key);
}
UProceduralMeshComponent* ADaedalusOceanSectorView::MeshForChunk(int32 X,int32 Y,int32 Z) const
{
    const auto* Found=Meshes.Find(FIntVector(X,Y,Z));return Found?Found->Get():nullptr;
}
int32 ADaedalusOceanSectorView::TriangleCount(int32 X,int32 Y,int32 Z) const
{
    auto* Mesh=MeshForChunk(X,Y,Z);int32 Count=0;
    if (Mesh) for (int32 I=0;I<2;I++) if (const auto* Section=Mesh->GetProcMeshSection(I)) Count+=Section->ProcIndexBuffer.Num()/3;
    return Count;
}
void ADaedalusOceanSectorView::RebuildNeighbours(const FIntVector& Key)
{
    for (const auto& Offset:Neighbours) if (Chunks.Contains(Key+Offset)) Rebuild(Key+Offset);
}
void ADaedalusOceanSectorView::Rebuild(const FIntVector& Key)
{
    if (!Chunks.Contains(Key)) return;
    // Mesh in chunk-local coordinates. Avoid float precision loss and signed
    // global mesher arithmetic at far realm coordinates; scene offsets are double.
    daedalus::ChunkStore Store;
    auto Add=[&](const FIntVector& Absolute,const FIntVector& Local) {
        if (const auto* Found=Chunks.Find(Absolute)) {
            daedalus::ChunkStore::Cubes Cubes;
            FMemory::Memcpy(Cubes.data(),Found->Blocks.GetData(),4096);
            Store.Put({Local.X,Local.Y,Local.Z},Cubes);
        }
    };
    Add(Key,FIntVector::ZeroValue);for (const auto& Offset:Neighbours) Add(Key+Offset,Offset);
    daedalus::Palette Palette;
    for (const FString& Name:PaletteNames) {const auto* T=FindType(Name);Palette.Types.push_back({T->Name,T->Rgb,T->Translucent,T->SeeThrough});}
    daedalus::Part Opaque,Water;daedalus::MeshChunkGreedy(Store,Palette,{0,0,0},Opaque,Water);
    if (Opaque.IsEmpty() && Water.IsEmpty()) {DropMesh(Key);return;}
    auto* Mesh=MeshForChunk(Key.X,Key.Y,Key.Z);
    if (!Mesh) {
        Mesh=NewObject<UProceduralMeshComponent>(this);AddInstanceComponent(Mesh);Mesh->SetupAttachment(RootComponent);
        Mesh->bUseAsyncCooking=true;Mesh->SetCollisionProfileName(TEXT("BlockAll"));Mesh->RegisterComponent();Meshes.Add(Key,Mesh);
    }
    Mesh->SetRelativeLocation(FVector(static_cast<double>(Key.X)*1600,static_cast<double>(Key.Z)*1600,static_cast<double>(Key.Y)*1600));
    auto* Fallback=LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/EngineDebugMaterials/VertexColorMaterial.VertexColorMaterial"));
    for (int32 Section=0;Section<2;Section++) {
        const auto& Part=Section==0?Opaque:Water;
        if (Part.IsEmpty()) {Mesh->ClearMeshSection(Section);continue;}
        TArray<FVector> Vertices,Normals;TArray<FLinearColor> Colors;TArray<int32> Indices;TArray<FVector2D> UVs;
        for (int32 I=0;I<Part.VertexCount();I++) {
            const auto* P=&Part.Positions[I*3];const auto* N=&Part.Normals[I*3];const auto* C=&Part.Colors[I*3];
            Vertices.Add(FVector(P[0]*100,P[2]*100,P[1]*100));Normals.Add(FVector(N[0],N[2],N[1]));
            Colors.Add(FLinearColor(C[0],C[1],C[2],1));UVs.Add(FVector2D(P[0]+P[2],P[1]));
        }
        for (uint32 Index:Part.Indices) Indices.Add(static_cast<int32>(Index));
        Mesh->CreateMeshSection_LinearColor(Section,Vertices,Indices,Normals,UVs,Colors,TArray<FProcMeshTangent>(),Section==0);
        auto* Material=Section==0?OpaqueMaterial.Get():WaterMaterial.Get();Mesh->SetMaterial(Section,Material?Material:Fallback);
    }
}
