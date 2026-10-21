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
	 * Function calls remain held. The separate v3 cached diagnostic captures a
	 * <=128 GUID manifest, <=3 selected outputs from <=16 outputs, and <=3 uniquely
	 * matched rich inputs in one pre-append-budgeted 512KiB envelope; no evaluation. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Material Admission", meta = (DevelopmentOnly))
	static FString ReadMaterialFactors(const TArray<FString>& MaterialObjectPaths,
		const FString& AllowedPackageRoot, const FString& PolicyId);

 /** Distinct current proof for the three observed MF_Default_Body switch roots.
  * Independently capture selectors; resolve only bounded cached plain/named
  * reroutes and GUID-bound function input/output frames to typed constants.
  * At most32 steps/lane,4 nested frames/depth4,128 inputs/16 outputs/frame,
  * 3 parameter queries/material and a prospective512KiB whole-envelope cap.
  * No graph evaluator/load/refresh/compile/edit/save. Unknowns remain held. */
 UFUNCTION(BlueprintCallable, Category = "Daedalus|Material Admission", meta = (DevelopmentOnly))
 static FString ReadMaterialSwitchProof(const TArray<FString>& MaterialObjectPaths,
  const FString& AllowedPackageRoot, const FString& PolicyId);
};
