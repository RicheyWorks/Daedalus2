// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.battlefield.BattlefieldEcology.EventKind;
import com.daedalus.world.tactics.SquadDirector;
import com.daedalus.world.tactics.SquadDirector.CoverRules;
import com.daedalus.world.tactics.SquadDirector.Settings;
import com.daedalus.world.tactics.SquadDirector.Unit;
import com.daedalus.world.tactics.TacticalOrders;
import com.daedalus.world.tactics.TacticalOrders.Order;
import com.daedalus.world.tactics.TacticalOrders.Spec;
import com.daedalus.world.tactics.TacticalOrders.Vec;
import com.daedalus.world.tactics.TacticalOrders.Verb;

import java.util.List;

import org.junit.jupiter.api.Test;

/** The squad director (ADR-060) takes its cover from the live battlefield ecology (ADR-061) via eco::bestCover. */
class DirectorCoverIntegrationTest {

    private static final Vec PLAYER = new Vec(0, 0, 0);
    private static final List<Unit> THREE = List.of(new Unit("foe-a", new Vec(-600, 0, 0), 60, 60, true),
            new Unit("foe-b", new Vec(-900, 300, 0), 60, 60, true),
            new Unit("foe-c", new Vec(-1100, -200, 0), 10, 60, false));

    private static Order find(Spec s, String unit) {
        return s.orders().stream().filter(o -> o.unit().equals(unit)).findFirst().orElseThrow();
    }

    /** Meadow everywhere, an oak wood beside foe-b's baseline flank point. */
    private static BattlefieldEcology field(Vec flank) {
        BattlefieldEcology e = new BattlefieldEcology(60, 60, 100, -3000, -3000, 9);
        for (int j = 0; j < 60; j++) {
            for (int i = 0; i < 60; i++) {
                e.set(i, j, Vegetation.MEADOW);
            }
        }
        int ci = e.cellI(flank.x());
        int cj = e.cellJ(flank.y());
        for (int j = cj - 1; j <= cj + 1; j++) {
            for (int i = ci + 2; i <= ci + 3; i++) {
                e.set(i, j, Vegetation.OAK);
            }
        }
        return e;
    }

    @Test
    void flankerMovesIntoTheOakWood() {
        Vec flank = find(SquadDirector.decide("s", 1, THREE, PLAYER), "foe-b").at();
        BattlefieldEcology eco = field(flank);
        Spec s = SquadDirector.decide("s", 1, THREE, PLAYER, Settings.DEFAULT, eco::bestCover, CoverRules.DEFAULT);
        Order b = find(s, "foe-b");
        assertThat(b.verb()).isEqualTo(Verb.FLANK);
        assertThat(eco.at(b.at().x(), b.at().y())).isEqualTo(Vegetation.OAK);
        assertThat(b.why()).contains("into cover");
        assertThat(TacticalOrders.write(s)).contains("foe-b");
    }

    @Test
    void burningWoodIsNotChosen() {
        Vec flank = find(SquadDirector.decide("s", 1, THREE, PLAYER), "foe-b").at();
        BattlefieldEcology eco = field(flank);
        eco.apply(EventKind.IGNITE, flank.x() + 250, flank.y(), 150);
        Spec s = SquadDirector.decide("s", 1, THREE, PLAYER, Settings.DEFAULT, eco::bestCover, CoverRules.DEFAULT);
        for (Order o : s.orders()) {
            assertThat(eco.burningAt(o.at().x(), o.at().y())).as(o.unit()).isFalse();
        }
    }
}