// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DaedalusFilm.generated.h"

class ASceneCapture2D;

/**
 * Filming helpers for the trailer kit (tools/trailer). Python cannot spawn actors into the Play world (only the
 * editor world), so this spawns the trailer's SceneCapture2D where the game is running.
 */
UCLASS()
class DAEDALUSLINK_API UDaedalusFilm : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** A SceneCapture2D in WorldContext's world (the Play world when called with a Play actor), not capturing every
	 * frame, final colour LDR. Destroy it when done. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Film", meta = (WorldContext = "WorldContext"))
	static ASceneCapture2D* SpawnFilmCamera(const UObject* WorldContext);

	/** Spawn any actor class into WorldContext's world (the Play world when called with a Play actor): the editor's
	 * Python can only spawn into the editor world. Transient, always spawns. Set properties, then call its Rebuild. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Film", meta = (WorldContext = "WorldContext"))
	static AActor* SpawnInPlay(const UObject* WorldContext, TSubclassOf<AActor> Class, FVector Location, FRotator Rotation);
};
