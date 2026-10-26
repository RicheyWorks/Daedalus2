// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.daedalus.world.ecology.CommunityComparison;

/** Independently captured ecology days are explicit; cross-world snapshots are not atomic. */
public record IslandEcologyComparisonResponse(String worldId, int slot, long day,
                                               String otherWorldId, int otherSlot, long otherDay,
                                               CommunityComparison comparison) {
}
