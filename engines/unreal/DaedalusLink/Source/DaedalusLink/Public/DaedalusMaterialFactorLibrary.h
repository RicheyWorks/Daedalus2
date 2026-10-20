// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DaedalusMaterialFactorLibrary.generated.h"

/** Bounded read-only authored material input facts, not shader/pixel evaluation. */
UCLASS()
class DAEDALUSLINK_API UDaedalusMaterialFactorLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	/** Two exact, already loaded, clean UMaterials in an explicit owned subtree.
	 * No loading, compilation, edits, save, recursive graph traversal or getter fallbacks.
	 * Function calls remain held; a separate cached_function_facts diagnostic describes
	 * current public C++ fields without evaluation or refreshing transient bindings. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Material Admission", meta = (DevelopmentOnly))
	static FString ReadMaterialFactors(const TArray<FString>& MaterialObjectPaths,
		const FString& AllowedPackageRoot, const FString& PolicyId);
};
