UCLASS()
class ABadLayers : public AActor
{
	GENERATED_BODY()
	UPROPERTY() TArray<TObjectPtr<UHierarchicalInstancedStaticMeshComponent>> IsleLayers;
};
