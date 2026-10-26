ABadLayers::ABadLayers()
{
	for (int32 i = 0; i < 6; ++i) IsleLayers.Add(CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(TEXT("L")));
}
