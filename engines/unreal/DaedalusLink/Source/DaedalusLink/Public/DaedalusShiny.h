// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"

class AActor;
class USceneComponent;
class UStaticMeshComponent;
class UPointLightComponent;

/**
 * Shiny (ADR-065 rule 9): a very rare roll any creature or avatar can carry. It "increases everything including max
 * level", and in the world it has to be seen at a glance: a slow rainbow-cycling glow and a ring of sparks orbiting the
 * body. The roll itself happens at mint and arrives as a flag; this is only the look and the stat multiplier.
 *
 * One helper for every kind of actor (critters, foes, later the hero's avatar), so every shiny looks the same.
 */
namespace DaedalusShiny
{
	/** How much a shiny multiplies a stat (health, damage, speed, max level). Game balance owns the number (Sol). */
	constexpr float StatBoost = 1.5f;
	/** Shinies stand a little taller. */
	constexpr float ScaleBoost = 1.15f;
	constexpr int32 Sparks = 7;

	struct FState
	{
		TArray<TWeakObjectPtr<UStaticMeshComponent>> Sparks;
		TWeakObjectPtr<UPointLightComponent> Light;
		float Time = 0.f;
		float Size = 100.f;   // cm, the body's height: sparks orbit at ~0.7 of it
	};

	/** Attach the glow and the sparks under Under. Size is the body height in cm. */
	DAEDALUSLINK_API void Attach(AActor* Owner, USceneComponent* Under, float Size, FState& State);
	/** Advance the shimmer: hue cycles over about 4 s, sparks orbit and bob, the light breathes. */
	DAEDALUSLINK_API void Tick(FState& State, float Dt);
	/** The hue at a point in the cycle (0..1), bright enough to read as a glow. */
	DAEDALUSLINK_API FLinearColor Hue(float T);
	/** Remove what Attach made. */
	DAEDALUSLINK_API void Detach(FState& State);
}
