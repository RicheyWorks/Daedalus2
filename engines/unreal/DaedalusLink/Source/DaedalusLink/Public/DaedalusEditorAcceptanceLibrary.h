// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DaedalusEditorAcceptanceLibrary.generated.h"

UENUM()
enum class EDaedalusAcceptanceValidationOutcome : uint8
{
	Valid,
	Invalid,
	NotValidated
};

/** Isolated native validation input; has no gameplay or startup behavior. */
UCLASS(NotBlueprintable)
class DAEDALUSLINK_API UDaedalusAcceptanceValidationFixture : public UDataAsset
{
	GENERATED_BODY()
public:
	UPROPERTY(EditAnywhere, Category = "Editor Acceptance")
	EDaedalusAcceptanceValidationOutcome Outcome = EDaedalusAcceptanceValidationOutcome::NotValidated;

#if WITH_EDITOR
	virtual EDataValidationResult IsDataValid(FDataValidationContext& Context) const override;
#endif
};

/** Reflected entry points for the existing bridge; no new server or transport. */
UCLASS()
class DAEDALUSLINK_API UDaedalusEditorAcceptanceLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** Validate the explicit loaded-asset set with the canonical native producer. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Editor Acceptance", meta = (DevelopmentOnly))
	static FString ValidateNamedAssets(const TArray<FString>& AssetObjectPaths,
		const FString& AllowedPackageRoot, bool bCancelRequested = false);

	/** Exercise only the disposable virtual Slate button and its cleanup. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Editor Acceptance", meta = (DevelopmentOnly))
	static FString RunSlateButtonFixture();

	/** Bind only the already existing primary level-editor Details panel.
	 * Does not spawn, activate, focus, observe, snapshot, or simulate input. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Editor Acceptance", meta = (DevelopmentOnly))
	static FString BindExistingDetailsPanel();
};
