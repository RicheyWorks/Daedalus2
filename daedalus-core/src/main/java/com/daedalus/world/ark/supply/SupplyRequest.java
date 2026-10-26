// SPDX-License-Identifier: MIT
package com.daedalus.world.ark.supply;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/** One island's request for cargo. {@link #forIsland} rolls the same requests from the same island seed. */
public record SupplyRequest(String requestId, Cargo cargo, int units) {

    public SupplyRequest {
        SupplyRun.key(requestId, "requestId");
        if (cargo == null || units < 1 || units > 200) throw new IllegalArgumentException("cargo and units 1..200");
    }

    /**
     * 2..4 seeded requests for the island raised from {@code islandSeed}: a young island always asks for seed caches
     * first, then water, then whatever else the roll picks (never the same cargo twice).
     */
    public static List<SupplyRequest> forIsland(long islandSeed) {
        SplittableRandom rng = new SplittableRandom(islandSeed);
        int count = 2 + rng.nextInt(3);
        List<Cargo> pool = new ArrayList<>(List.of(Cargo.FODDER_BALE, Cargo.SALVE_JAR, Cargo.TIMBER_BUNDLE));
        List<SupplyRequest> out = new ArrayList<>();
        String prefix = "isle-" + Long.toUnsignedString(islandSeed, 36) + "-";
        out.add(new SupplyRequest(prefix + "0", Cargo.SEED_CACHE, 2 + rng.nextInt(6)));
        out.add(new SupplyRequest(prefix + "1", Cargo.WATER_CASK, 3 + rng.nextInt(8)));
        for (int i = 2; i < count; i++) {
            Cargo c = pool.remove(rng.nextInt(pool.size()));
            out.add(new SupplyRequest(prefix + i, c, 1 + rng.nextInt(c == Cargo.TIMBER_BUNDLE ? 4 : 10)));
        }
        return List.copyOf(out);
    }
}
