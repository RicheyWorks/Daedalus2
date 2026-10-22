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

#if WITH_EDITOR
    /** Editor-only fresh isolated test: capture live final job attributes and independently
     * translated source. Core UObject boundary keeps generated runtime cross-module
     * declarations independent of editor-only Interchange; implementation strictly
     * casts the object to a node container. Never imports or saves. */
    UFUNCTION(BlueprintCallable, Category="Daedalus|Animation Acceptance", meta=(DevelopmentOnly))
    static FString ReadFreshMineSource(UObject* JobNodes);
#endif

    /** Already-loaded, fixed private Mine fixture only; never loads/imports/saves. */
    UFUNCTION(BlueprintCallable, Category="Daedalus|Animation Acceptance", meta=(DevelopmentOnly))
    static FString ReadFreshMineClip(const FString& AssetPath);
};
