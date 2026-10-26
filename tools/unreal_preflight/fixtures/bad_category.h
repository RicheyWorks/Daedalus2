USTRUCT(BlueprintType)
struct FBadState
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame) float TimeOfDay = 9.f;
};
