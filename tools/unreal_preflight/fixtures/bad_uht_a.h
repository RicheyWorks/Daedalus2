#pragma once
// P10 canary, first half: the #285 bench, a struct and a delegate.
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FBenchBrewed, int32, Tier);
UCLASS()
class SAMPLE_API ABench : public AActor
{
	GENERATED_BODY()
};
USTRUCT(BlueprintType)
struct FKettle
{
	GENERATED_BODY()
};
