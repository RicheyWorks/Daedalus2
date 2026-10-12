// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"

class ADaedalusHero;

/**
 * The hero's HUD (ADR-042), in Halo Infinite's spirit: a centred reticle (dot and four ticks) that flashes on a hit,
 * and in the corners the weapon, its heat, the camera view and EXP. The reticle shows in first person and over the
 * shoulder, and with the blaster in any view (Settings > Video > Reticle turns it off).
 */
class SDaedalusHud : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SDaedalusHud) {}
		SLATE_ARGUMENT(TWeakObjectPtr<ADaedalusHero>, Hero)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);

private:
	TWeakObjectPtr<ADaedalusHero> Hero;
};
