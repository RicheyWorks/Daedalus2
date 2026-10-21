#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DaedalusProspectorMineReadLibrary.generated.h"

class UInterchangeBaseNodeContainer;

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

    /** Fresh isolated test only: capture live final job attributes and independently
     * translated source. This is evidence, not historical metadata recovery. */
    UFUNCTION(BlueprintCallable, Category="Daedalus|Animation Acceptance", meta=(DevelopmentOnly))
    static FString ReadFreshMineSource(UInterchangeBaseNodeContainer* JobNodes);

    /** Already-loaded, fixed private Mine fixture only; never loads/imports/saves. */
    UFUNCTION(BlueprintCallable, Category="Daedalus|Animation Acceptance", meta=(DevelopmentOnly))
    static FString ReadFreshMineClip(const FString& AssetPath);
};
