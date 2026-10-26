// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.letters;

import com.daedalus.world.brew.cellar.RootCellar;
import com.daedalus.world.brew.stones.ChoirStones;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.odds.route.ArkRoute;
import com.daedalus.world.odds.route.Hazard;
import com.daedalus.world.odds.route.RouteLeg;
import java.util.List;
import java.util.Objects;

/**
 * A far island the ark post reaches: who lives there, what they'd love to receive, which supper guest (G85) is
 * their old friend, and the ark route there (G47 {@link ArkRoute}, read-only).
 */
public record Destination(String id, String npc, String name, String favourite, String friendOf, ArkRoute route) {
    /** Crates an ark carries: the route's lifeAboard, used by the G80 underwriter's premium. */
    public static final int CRATES = 10;

    public Destination {
        Objects.requireNonNull(id, "id");
        Objects.requireNonNull(route, "route");
    }

    /** The four far islands, nearest first. */
    public static List<Destination> island() {
        return List.of(
                new Destination("kelp_harbour", "harbourmaster_nell", "Harbourmaster Nell", "fish", "dov",
                        new ArkRoute("Kelp Harbour run", List.of(new RouteLeg("kelp shallows", Hazard.DRIFT, 0.10)),
                                CRATES)),
                new Destination("cinder_reach", "smith_arlo", "Smith Arlo", "Bacon", ChoirStones.MASON,
                        new ArkRoute("Cinder Reach run", List.of(new RouteLeg("ash squalls", Hazard.SQUALL, 0.30),
                                new RouteLeg("cinder belt", Hazard.DEBRIS, 0.15)), CRATES)),
                new Destination("glass_shoals", "lampwright_suse", "Lampwright Suse", "Egg", RootCellar.BRINE,
                        new ArkRoute("Glass Shoals run", List.of(new RouteLeg("still water", Hazard.DRIFT, 0.20),
                                new RouteLeg("glass squalls", Hazard.SQUALL, 0.30),
                                new RouteLeg("shoal drift", Hazard.DRIFT, 0.10)), CRATES)),
                new Destination("far_orchard", "orchard_keeper_bram", "Orchard-keeper Bram", "Moonbean",
                        SeedSongSpring.KEEPER,
                        new ArkRoute("Far Orchard run", List.of(new RouteLeg("rock field", Hazard.DEBRIS, 0.20),
                                new RouteLeg("high squalls", Hazard.SQUALL, 0.40),
                                new RouteLeg("long drift", Hazard.DRIFT, 0.20),
                                new RouteLeg("orchard squalls", Hazard.SQUALL, 0.20)), CRATES)));
    }
}
