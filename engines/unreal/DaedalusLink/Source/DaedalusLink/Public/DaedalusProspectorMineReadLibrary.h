#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DaedalusProspectorMineReadLibrary.generated.h"

/** Source-only staging proposal. No installed callable/build is claimed.
 * Reads already loaded exact targets and independently translates the pinned
 * source into transient nodes/payloads; never imports or saves an asset.
 */
UCLASS()
class DAEDALUSLINK_API UDaedalusProspectorMineReadLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Daedalus|Animation Acceptance", meta=(DevelopmentOnly))
    static FString ReadMinePrerequisites(const TArray<double>& SampleTimes);
};
