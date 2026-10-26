#pragma once
// P10 canary, second half: each of these collides with bad_uht_a.h. A comment saying UCLASS() class ABench is ignored.
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FBenchBrewed, int32, Tier, const FString&, Tune);
UCLASS(Blueprintable)
class SAMPLE_API ABench : public AActor
{
	GENERATED_BODY()
};
UCLASS()
class SAMPLE_API UKettle : public UObject
{
	GENERATED_BODY()
};
