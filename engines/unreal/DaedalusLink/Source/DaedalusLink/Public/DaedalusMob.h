// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "UObject/SoftObjectPath.h"

class AActor;
class USceneComponent;
class UStaticMeshComponent;

/**
 * The Blender team's creatures, put together in Unreal (ADR-055). A shipped Mob_<Name> is a set of part meshes
 * (_Body, _Head, _LegFL, _WingL...) with their offsets baked in: every part shares one origin, the model's bottom is at
 * z = 0 and its front faces +Y. So assembling one is attaching every part, untransformed, under one component that is
 * turned -90 degrees to face Unreal's +X.
 */
namespace DaedalusMob
{
	/** The part meshes of /Game/Daedalus/Art/Mob/<Asset> (cached; empty if that creature hasn't shipped). */
	DAEDALUSLINK_API const TArray<FSoftObjectPath>& Parts(const FString& Asset);

	/** Attach Asset's parts under Under (no collision, movable). Returns how many parts were attached; Out gets them. */
	DAEDALUSLINK_API int32 Build(AActor* Owner, USceneComponent* Under, const FString& Asset,
		TArray<UStaticMeshComponent*>* Out = nullptr, float* OutHeight = nullptr);
}
