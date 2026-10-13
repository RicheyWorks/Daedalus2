// SPDX-License-Identifier: MIT
package com.daedalus.world.tactics;

import com.daedalus.world.tactics.AdaptiveDirector.Frame;
import com.daedalus.world.tactics.AdaptiveDirector.Memory;
import com.daedalus.world.tactics.AdaptiveDirector.WeaponStyle;
import com.daedalus.world.tactics.SquadDirector.Unit;
import com.daedalus.world.tactics.TacticalOrders.Vec;
import com.daedalus.world.tactics.TacticalOrders.Verb;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class AdaptiveDirectorTest {
    @TempDir Path temp;
    private static Unit unit(String name, double health) { return new Unit(name, new Vec(100, 0, 0), health, 100, true); }
    private static Frame frame(long tick, List<Unit> units, Vec player, boolean threat) {
        return new Frame("pack-1", "session-1", tick, units, player, new Vec(0, 0, 0), threat, WeaponStyle.LONG_RANGE);
    }
    private static Memory initial() { return Memory.initial("raiders", "session-1"); }

    @Test void threeEnemiesDefendFlankAndRetreatInOneCoordinatedStep() {
        var d = AdaptiveDirector.decide(initial(), frame(0, List.of(unit("a", 100), unit("b", 100), unit("c", 20)), new Vec(1000, 0, 0), true));
        assertThat(d.orders().orders()).extracting(TacticalOrders.Order::verb).containsExactly(Verb.DEFEND, Verb.FLANK, Verb.RETREAT);
        assertThat(d.orders().orders()).allSatisfy(o -> assertThat(o.why()).isNotBlank());
        assertThat(TacticalOrders.parse(TacticalOrders.write(d.orders())).ok()).isTrue();
    }

    @Test void canonicalInputOrderAndDuplicateObservationProduceIdenticalOutput() {
        var units = new ArrayList<>(List.of(unit("c", 80), unit("a", 90), unit("b", 10)));
        var first = AdaptiveDirector.decide(initial(), frame(5, units, new Vec(1000, 0, 500), true));
        Collections.reverse(units);
        var f = frame(5, units, new Vec(1000, 0, 500), true);
        assertThat(AdaptiveDirector.decide(initial(), f)).isEqualTo(first);
        assertThat(AdaptiveDirector.decide(first.memory(), f)).isEqualTo(first);
        assertThatThrownBy(() -> AdaptiveDirector.decide(first.memory(), frame(4, units, f.player(), true))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> AdaptiveDirector.decide(first.memory(), frame(5, units, f.player(), false))).isInstanceOf(IllegalArgumentException.class);
    }

    @Test void objectiveGuardDoesNotConsumeTheOnlyHealthyFlankingRole() {
        var units = List.of(new Unit("guard", new Vec(0, 0, 0), 100, 100, true),
                new Unit("scout", new Vec(200, 0, 0), 100, 100, true),
                new Unit("wounded", new Vec(300, 0, 0), 20, 100, true));
        var d = AdaptiveDirector.decide(initial(), frame(1, units, new Vec(1000, 0, 0), true));
        assertThat(d.orders().orders()).extracting(TacticalOrders.Order::verb)
                .containsExactly(Verb.DEFEND, Verb.FLANK, Verb.RETREAT);
    }

    @Test void factionMemorySurvivesFileRestartAndChangesTheNextEncounter() throws Exception {
        Memory memory = initial();
        var roster = List.of(unit("a", 100), unit("b", 0), unit("c", 0));
        for (int tick = 0; tick < 6; tick++) memory = AdaptiveDirector.decide(memory, frame(tick, roster, new Vec(1000, 0, 600), false)).memory();
        Path file = temp.resolve("faction.dtm");
        Files.write(file, TacticalMemory.encode(memory));
        Memory recovered = TacticalMemory.decode(Files.readAllBytes(file));
        assertThat(recovered).isEqualTo(memory);
        Memory next = recovered.nextEncounter("session-2");
        var f = new Frame("pack-2", "session-2", 0, List.of(unit("a", 100), unit("b", 100), unit("c", 100)),
                new Vec(1000, 0, 0), new Vec(0, 0, 0), false, WeaponStyle.UNKNOWN);
        var learned = AdaptiveDirector.decide(next, f);
        assertThat(learned.orders().orders().getFirst().verb()).isEqualTo(Verb.DEFEND);
        assertThat(learned.retreatBelow()).isGreaterThan(0.30).isLessThanOrEqualTo(0.45);
        assertThatThrownBy(() -> recovered.nextEncounter("session-1")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> AdaptiveDirector.decide(recovered, f)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test void absentContactDoesNotTeachHiddenPlayerElevationOrIssuePursuit() {
        var unseen = new Unit("a", new Vec(0, 0, 0), 10, 100, false);
        var d = AdaptiveDirector.decide(initial(), frame(0, List.of(unseen), new Vec(10, 0, 999), true));
        assertThat(d.memory().elevatedSamples()).isZero();
        assertThat(d.orders().orders().getFirst().verb()).isEqualTo(Verb.HOLD);
        assertThat(d.orders().orders().getFirst().at()).isEqualTo(unseen.at());
    }

    @Test void boundedSquadsNeverExceedWireOrBalanceLimits() {
        for (int count : new int[] {0, 1, 3, 32, 128, 256}) {
            var units = new ArrayList<Unit>();
            for (int i = 0; i < count; i++) units.add(unit("u" + i, i % 7 == 0 ? 0 : 100));
            var d = AdaptiveDirector.decide(initial(), frame(0, units, new Vec(1000, 0, 0), true));
            assertThat(d.unitsEvaluated()).isEqualTo(count);
            assertThat(d.orders().orders().size()).isLessThanOrEqualTo(count);
            assertThat(d.orders().orders().stream().filter(o -> o.verb() == Verb.FLANK).count()).isLessThanOrEqualTo(d.flankBudget());
            assertThat(d.orders().orders().stream().filter(o -> o.verb() == Verb.REINFORCE).count()).isLessThanOrEqualTo(1);
            assertThat(TacticalOrders.parse(TacticalOrders.write(d.orders())).ok()).isTrue();
        }
        assertThatThrownBy(() -> frame(0, Collections.nCopies(257, unit("a", 100)), new Vec(0, 0, 0), false)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test void invalidHealthIdsPositionsAndConflictingRosterFailBeforePlanning() {
        assertThatThrownBy(() -> frame(0, List.of(unit("a", 100), unit("a", 50)), new Vec(0, 0, 0), false)).isInstanceOf(IllegalArgumentException.class);
        for (double hp : new double[] {-1, 101, Double.NaN, Double.POSITIVE_INFINITY}) {
            assertThatThrownBy(() -> frame(0, List.of(unit("a", hp)), new Vec(0, 0, 0), false)).isInstanceOf(IllegalArgumentException.class);
        }
        assertThatThrownBy(() -> frame(-1, List.of(), new Vec(0, 0, 0), false)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> frame(0, List.of(unit("bad id", 100)), new Vec(0, 0, 0), false)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> frame(0, List.of(), new Vec(Double.NaN, 0, 0), false)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test void corruptOrOversizedMemoryFailsClosed() {
        byte[] good = TacticalMemory.encode(initial());
        assertThat(TacticalMemory.decode(good)).isEqualTo(initial());
        good[6] ^= 1;
        assertThatThrownBy(() -> TacticalMemory.decode(good)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TacticalMemory.decode(new byte[513])).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Memory("a", "b", -1, 9, 0, "-")).isInstanceOf(IllegalArgumentException.class);
    }
}
