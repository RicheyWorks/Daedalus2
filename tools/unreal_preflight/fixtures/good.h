UCLASS()
class AGoodIsle : public AActor
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, Category = "Daedalus") int32 Seed = 7;
	UPROPERTY(Transient) TArray<TObjectPtr<UHierarchicalInstancedStaticMeshComponent>> IsleLayers;
	UPROPERTY() TObjectPtr<UTextRenderComponent> Name;
};
const TCHAR* FailureName(daedalus::sol::Error E);
