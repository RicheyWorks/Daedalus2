// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"

namespace DaedalusLegacyHlodFixture
{
// Deliberately covers only a new, local Merge tier in a private non-WP world.
// Description-backed actors need a different persistence witness, not a setting change.
inline bool CheckPolicy(bool bForcedSetup, bool bDescriptionActors, bool bPartitioned,
    bool bVacantOwnedPackages, int32 SourceCount, int32 Tier)
{
    return !bForcedSetup && !bDescriptionActors && !bPartitioned
        && bVacantOwnedPackages && SourceCount == 2 && Tier == 0;
}

#if WITH_EDITOR
FString ReadContext();
FString CreateBuildSave();
FString ReadSaved();
#endif
}
