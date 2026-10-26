// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DaedalusPCGFixtureOwnerLibrary.generated.h"

/** Sole-operator acceptance fixture only. No arbitrary actor/world selectors. */
UCLASS()
class DAEDALUSLINK_API UDaedalusPCGFixtureOwnerLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Daedalus|Editor|PCG")
    static FString CreateOwnedFixture();

    UFUNCTION(BlueprintCallable, Category="Daedalus|Editor|PCG")
    static FString DescribeOwnedFixture();

    UFUNCTION(BlueprintCallable, Category="Daedalus|Editor|PCG")
    static FString DestroyOwnedFixture();
};
