// SPDX-License-Identifier: MIT

package com.daedalus.world.tactics;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.tactics.SquadDirector.CoverField;
import com.daedalus.world.tactics.SquadDirector.CoverRules;
import com.daedalus.world.tactics.SquadDirector.Settings;
import com.daedalus.world.tactics.SquadDirector.Unit;
import com.daedalus.world.tactics.TacticalOrders.Order;
import com.daedalus.world.tactics.TacticalOrders.Spec;
import com.daedalus.world.tactics.TacticalOrders.Vec;
import com.daedalus.world.tactics.TacticalOrders.Verb;

import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.Test;

/** Cover-aware orders: flankers, the hurt and defenders move into nearby cover; attackers don't. */
class CoverAwareDirectorTest {

    private static final Vec PLAYER = new Vec(0, 0, 0);
    private static final List<Unit> THREE = List.of(new Unit("foe-a", new Vec(-600, 0, 0), 60, 60, true),
            new Unit("foe-b", new Vec(-900, 300, 0), 60, 60, true),
            new Unit("foe-c", new Vec(-1100, -200, 0), 10, 60, false));

    /** A field of 100 cm cells, bare (score 0.1) except a thicket square [x0,x1) x [y0,y1) of score 0.8. */
    static CoverField thicket(double x0, double x1, double y0, double y1, List<double[]> calls) {
        return (ux, uy, thx, thy, r) -> {
            calls.add(new double[] {ux, uy, r});
            double best = -1;
            double bx = ux;
            double by = uy;
            for (double x = Math.floor((ux - r) / 100) * 100 + 50; x <= ux + r; x += 100) {
                for (double y = Math.floor((uy - r) / 100) * 100 + 50; y <= uy + r; y += 100) {
                    double d = Math.hypot(x - ux, y - uy);
                    if (d > r) {
                        continue;
                    }
                    double score = (x >= x0 && x < x1 && y >= y0 && y < y1 ? 0.8 : 0.1) - 1e-6 * d;
                    if (score > best) {
                        best = score;
                        bx = x;
                        by = y;
                    }
                }
            }
            return new double[] {bx, by, Math.max(0, best)};
        };
    }

    private static Order find(Spec s, String unit) {
        return s.orders().stream().filter(o -> o.unit().equals(unit)).findFirst().orElseThrow();
    }

    @Test
    void withoutCoverItIsExactlyTheBaseline() {
        Spec base = SquadDirector.decide("s", 1, THREE, PLAYER);
        Spec none = SquadDirector.decide("s", 1, THREE, PLAYER, Settings.DEFAULT, null, CoverRules.DEFAULT);
        assertThat(TacticalOrders.write(none)).isEqualTo(TacticalOrders.write(base));
    }

    @Test
    void aFlankerTakesTheThicketBesideItsFlankPoint() {
        Spec base = SquadDirector.decide("s", 1, THREE, PLAYER);
        Vec flank = find(base, "foe-b").at();
        List<double[]> calls = new ArrayList<>();
        // a thicket starting 150 cm off the flank point, inside the 300 cm flank search
        CoverField f = thicket(flank.x() + 150, flank.x() + 450, flank.y() - 50, flank.y() + 50, calls);
        Spec s = SquadDirector.decide("s", 1, THREE, PLAYER, Settings.DEFAULT, f, CoverRules.DEFAULT);
        Order b = find(s, "foe-b");
        assertThat(b.verb()).isEqualTo(Verb.FLANK);
        assertThat(b.at().x()).isGreaterThanOrEqualTo(flank.x() + 150);
        assertThat(Math.hypot(b.at().x() - flank.x(), b.at().y() - flank.y())).isLessThanOrEqualTo(300);
        assertThat(b.why()).isEqualTo("cut off escape, left, into cover (0.80)");
        assertThat(find(s, "foe-a").at()).isEqualTo(PLAYER);   // the attacker goes for the player, not for cover
        assertThat(find(s, "foe-a").why()).doesNotContain("cover");
    }

    @Test
    void poorCoverIsNotWorthMovingFor() {
        List<double[]> calls = new ArrayList<>();
        CoverField bare = thicket(1e7, 1e7 + 1, 1e7, 1e7 + 1, calls);   // nowhere near: everything scores 0.1
        Spec s = SquadDirector.decide("s", 1, THREE, PLAYER, Settings.DEFAULT, bare, CoverRules.DEFAULT);
        assertThat(TacticalOrders.write(s)).isEqualTo(TacticalOrders.write(SquadDirector.decide("s", 1, THREE, PLAYER)));
        assertThat(calls).hasSize(2);   // asked for the flanker and the retreat; never for the attacker
    }

    @Test
    void theHurtRetreatIntoCoverWithTheWiderSearch() {
        Spec base = SquadDirector.decide("s", 1, THREE, PLAYER);
        Vec back = find(base, "foe-c").at();
        List<double[]> calls = new ArrayList<>();
        CoverField f = thicket(back.x() - 50, back.x() + 50, back.y() + 450, back.y() + 600, calls);
        Spec s = SquadDirector.decide("s", 1, THREE, PLAYER, Settings.DEFAULT, f, CoverRules.DEFAULT);
        Order c = find(s, "foe-c");
        assertThat(c.verb()).isEqualTo(Verb.RETREAT);
        assertThat(c.why()).startsWith("health 16%, into cover");
        assertThat(c.at().y()).isGreaterThanOrEqualTo(back.y() + 450);
        assertThat(calls.stream().anyMatch(k -> k[2] == 600)).isTrue();
    }

    @Test
    void aBrokenFieldIsIgnored() {
        CoverField nan = (ux, uy, thx, thy, r) -> new double[] {Double.NaN, 0, 1};
        CoverField shortArray = (ux, uy, thx, thy, r) -> new double[] {1};
        String base = TacticalOrders.write(SquadDirector.decide("s", 1, THREE, PLAYER));
        assertThat(TacticalOrders.write(SquadDirector.decide("s", 1, THREE, PLAYER, Settings.DEFAULT, nan, CoverRules.DEFAULT))).isEqualTo(base);
        assertThat(TacticalOrders.write(SquadDirector.decide("s", 1, THREE, PLAYER, Settings.DEFAULT, shortArray, CoverRules.DEFAULT))).isEqualTo(base);
        CoverField none = (a, b, c, d, e) -> null;
        assertThat(TacticalOrders.write(SquadDirector.decide("s", 1, THREE, PLAYER, Settings.DEFAULT, none, CoverRules.DEFAULT)))
                .isEqualTo(base);
    }

    @Test
    void coverAwareSpecsStillParseAndAreDeterministic() {
        Spec base = SquadDirector.decide("s", 1, THREE, PLAYER);
        Vec flank = find(base, "foe-b").at();
        CoverField f = thicket(flank.x() + 150, flank.x() + 450, flank.y() - 50, flank.y() + 50, new ArrayList<>());
        String a = TacticalOrders.write(SquadDirector.decide("s", 1, THREE, PLAYER, Settings.DEFAULT, f, CoverRules.DEFAULT));
        String b = TacticalOrders.write(SquadDirector.decide("s", 1, List.of(THREE.get(2), THREE.get(0), THREE.get(1)),
                PLAYER, Settings.DEFAULT, f, CoverRules.DEFAULT));
        assertThat(a).isEqualTo(b);
        assertThat(TacticalOrders.parse(a).ok()).isTrue();
    }
}
