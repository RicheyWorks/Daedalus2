// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DaedalusImportedFactorReadLibrary.generated.h"

/** CONDITIONAL SOURCE PROPOSAL. Not staged, compiled, callable or adopted.
 * Native facts only, for two already loaded original materials. The operator
 * must bind this immutable fragment to its SAME operation's actual process
 * generation and before/after preservation evidence before consumer admission.
 */
UCLASS()
class DAEDALUSLINK_API UDaedalusImportedFactorReadLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** No shader evaluation, default promotion, graph traversal, explicit asset
     * loading, authored material edits or save. Official import getters may
     * deserialize transient nodes or perform legacy import-data migration;
     * neither is silently called a material-cache refresh or proven absent.
     * Every native error survives host assembly. */
    /** Same criterion-scoped current-call/roster/factor/parameter projection;
     * no import provenance/materialization. Not a serialized full-graph witness. */
    UFUNCTION(BlueprintCallable, Category="Daedalus|Material Admission", meta=(DevelopmentOnly))
    static FString ReadImportedFactorProtection(const TArray<FString>& MaterialObjectPaths,
        const FString& AllowedPackageRoot);

    UFUNCTION(BlueprintCallable, Category="Daedalus|Material Admission", meta=(DevelopmentOnly))
    static FString ReadImportedFactorBindings(const TArray<FString>& MaterialObjectPaths,
        const FString& AllowedPackageRoot, const FString& PolicyId);

    /** Fresh isolated M0 current graph/source witness only. No sidecar admission,
     * engine graph retention change, load, compile, edit or mesh binding. Allows
     * only this fresh package to be dirty during import-time observation. */
    UFUNCTION(BlueprintCallable, Category="Daedalus|Material Admission", meta=(DevelopmentOnly))
    static FString ReadFreshImportedFactorCurrent(const FString& MaterialObjectPath,
        const FString& AllowedPackageRoot);
};
