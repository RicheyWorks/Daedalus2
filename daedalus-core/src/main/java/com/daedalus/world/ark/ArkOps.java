// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.island.IslandOps;
import com.daedalus.world.island.IslandTraits;

/** Where arks moor. Pure arithmetic on the island lane and an island's dock trait. */
public final class ArkOps {

    private ArkOps() {
    }

    /** The cube a passenger steps onto at the pier tip of the island in {@code slot}. */
    public static BlockCoordinate berth(int slot, IslandTraits traits) {
        BlockCoordinate origin = IslandOps.slot(slot);
        return new BlockCoordinate(origin.x() + traits.dockX(), origin.y() + traits.dockY() + 1,
                origin.z() + traits.dockZ());
    }

    /** The ark an island launches, moored at home. */
    public static Ark launch(int slot, IslandTraits traits) {
        return new Ark(Ark.idFor(slot), ArkNames.of(traits.seed()), slot, slot, berth(slot, traits));
    }
}
