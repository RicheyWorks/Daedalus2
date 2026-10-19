// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ArkDrydock.Ark;
import com.daedalus.world.forge.ArkDrydock.ArkClass;
import com.daedalus.world.forge.ArkDrydock.Life;
import com.daedalus.world.forge.ArkDrydock.Plate;
import com.daedalus.world.forge.ArkDrydock.Voyage;
import com.daedalus.world.forge.TemperForge.Quench;
import com.daedalus.world.forge.VoidCrossing.Crossing;
import com.daedalus.world.forge.VoidCrossing.Day;
import com.daedalus.world.forge.VoidCrossing.Outcome;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class VoidCrossingTest {

    private static final Voyage KENNEL = new Voyage("Kennel Isle", 6);

    /** A launch-ready skiff (the G24 manifest) with every plate at {@code temper}, water {@code extraDl} over the need. */
    static Ark ark(int temper, Voyage v, int extraDl) {
        List<Plate> plates = new ArrayList<>();
        List<Integer> rivets = new ArrayList<>();
        for (int i = 0; i < ArkClass.SKIFF.plates(); i++) {
            plates.add(new Plate(temper, i == 3 ? Quench.SPRING : Quench.MAGMA, true));
            rivets.add(ArkDrydock.RIVETS_PER_SEAM);
        }
        Map<Life, Integer> m = new EnumMap<>(Life.class);
        m.put(Life.EMBERHEN, 2);
        m.put(Life.ASHGOAT, 2);
        m.put(Life.VENT_BEES, 1);
        m.put(Life.PET, 1);
        m.put(Life.SEED_CRATE, 2);
        Ark dry = new Ark(ArkClass.SKIFF, plates, rivets, m, 0);
        return new Ark(ArkClass.SKIFF, plates, rivets, m, ArkDrydock.waterNeedDl(dry, v) + extraDl);
    }

    /** The first seed whose weather passes {@code ok}. */
    static long seedWhere(Ark a, Voyage v, java.util.function.Predicate<List<Day>> ok) {
        for (long s = 0; s < 10_000; s++) {
            if (ok.test(VoidCrossing.depart(a, v, false, 0, s).weather())) {
                return s;
            }
        }
        throw new AssertionError("no such seed");
    }

    @Test
    void theWeatherIsFixedAtDepartureAndOrdersNeverChangeIt() {
        Ark a = ark(90, KENNEL, 0);
        Crossing x = VoidCrossing.depart(a, KENNEL, false, 6, 21L);
        assertThat(x.weather()).hasSize(6).isEqualTo(VoidCrossing.depart(a, KENNEL, true, 0, 21L).weather());
        assertThat(x.weather()).isNotEqualTo(VoidCrossing.depart(a, KENNEL, false, 6, 22L).weather());
        List<Day> before = x.weather();
        assertThat(x.today()).isEqualTo(before.get(0));
        while (x.outcome() == Outcome.SAILING) {
            x.sail(0);
        }
        assertThat(x.weather()).isEqualTo(before);
        assertThat(x.today()).isNull();
        for (Day d : before) {
            assertThat(d.stormSeam()).isBetween(-1, 5);
            assertThat(d.damage()).isEqualTo(d.stormSeam() < 0 ? 0 : d.damage()).isBetween(0, 40);
        }
    }

    @Test
    void anArkBrannocDidNotClearNeverSails() {
        Ark leaky = ark(90, KENNEL, -1);
        Crossing x = VoidCrossing.depart(leaky, KENNEL, true, 3, 1L);
        assertThat(x.outcome()).isEqualTo(Outcome.NOT_LAUNCHED);
        assertThat(x.sail(0)).isEqualTo(Outcome.NOT_LAUNCHED);
        assertThat(x.day()).isZero();
        assertThat(x.today()).isNull();
        assertThat(x.line()).isEqualTo("Brannoc never cleared her off the slip. Fix the hull first.");
        assertThatThrownBy(() -> VoidCrossing.depart(ark(90, KENNEL, 0), KENNEL, false, 13, 1L))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> VoidCrossing.depart(ark(90, KENNEL, 0), KENNEL, false, -1, 1L))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void aCalmWarmCrossingDrinksExactlyTheDrydockNeed() {
        Ark a = ark(90, KENNEL, 0);
        long s = seedWhere(a, KENNEL, w -> w.stream().noneMatch(d -> d.cold() || d.stormSeam() >= 0));
        Crossing x = VoidCrossing.depart(a, KENNEL, false, 0, s);
        for (int d = 0; d < 5; d++) {
            assertThat(x.sail(-1)).isEqualTo(Outcome.SAILING);
        }
        assertThat(x.sail(-1)).isEqualTo(Outcome.ARRIVED);
        assertThat(x.water()).isZero();
        assertThat(x.minSeam()).isEqualTo(90);
        assertThat(x.line()).isEqualTo("Moored at Kennel Isle, every head aboard. She remembers the forge.");
        assertThat(x.sail(-1)).isEqualTo(Outcome.ARRIVED);
        assertThat(x.day()).isEqualTo(6);
    }

    @Test
    void sparesPatchOnlyDamagedSeamsAndNeverPastLaunchStrength() {
        Ark a = ark(90, KENNEL, 0);
        long s = seedWhere(a, KENNEL, w -> !w.get(0).cold() && w.get(0).stormSeam() >= 0 && !w.get(1).cold()
                && w.get(1).stormSeam() < 0);
        Crossing x = VoidCrossing.depart(a, KENNEL, false, 2, s);
        Day d0 = x.today();
        int other = (d0.stormSeam() + 1) % 6;
        x.sail(other);
        assertThat(x.spares()).isEqualTo(2);
        assertThat(x.seam(d0.stormSeam())).isEqualTo(90 - d0.damage());
        assertThat(x.weakestPatchable()).isEqualTo(d0.stormSeam());
        x.sail(d0.stormSeam());
        assertThat(x.spares()).isEqualTo(1);
        assertThat(x.patches()).isEqualTo(1);
        assertThat(x.seam(d0.stormSeam())).isEqualTo(Math.min(90, 90 - d0.damage() + ArkDrydock.MISSING_RIVET_COST));
        Crossing none = VoidCrossing.depart(a, KENNEL, false, 0, s);
        none.sail(-1);
        none.sail(d0.stormSeam());
        assertThat(none.patches()).isZero();
        assertThat(none.seam(d0.stormSeam())).isEqualTo(90 - d0.damage());
    }

    @Test
    void aColdSnapIdlesTheCrewAndDoublesTheirWaterUnlessTheyDrankTheTonic() {
        Ark a = ark(90, KENNEL, 400);
        long s = seedWhere(a, KENNEL, w -> w.get(0).stormSeam() >= 0 && !w.get(0).cold() && w.get(1).cold()
                && w.get(1).stormSeam() < 0);
        int crew = ArkClass.SKIFF.crew() * ArkDrydock.CREW_DL;
        Crossing cold = VoidCrossing.depart(a, KENNEL, false, 3, s);
        cold.sail(-1);
        int seam = cold.weakestPatchable();
        int w0 = cold.water();
        cold.sail(seam);
        assertThat(cold.idleDays()).isEqualTo(1);
        assertThat(cold.patches()).isZero();
        assertThat(w0 - cold.water()).isEqualTo(cold.needToday(false) + crew);
        Crossing warm = VoidCrossing.depart(a, KENNEL, true, 3, s);
        warm.sail(-1);
        int t0 = warm.water();
        warm.sail(seam);
        assertThat(warm.idleDays()).isZero();
        assertThat(warm.patches()).isEqualTo(1);
        assertThat(t0 - warm.water()).isEqualTo(cold.needToday(false) - crew + crew * 3 / 4);
    }

    @Test
    void aDryHoldLosesTheThirstiestHeadFirst() {
        Ark a = ark(90, KENNEL, 0);
        long s = seedWhere(a, KENNEL, w -> w.get(5).cold() && w.stream().filter(Day::cold).count() == 1
                && w.stream().allMatch(d -> d.stormSeam() < 0));
        Crossing x = VoidCrossing.depart(a, KENNEL, false, 0, s);
        while (x.outcome() == Outcome.SAILING) {
            x.sail(-1);
        }
        assertThat(x.outcome()).isEqualTo(Outcome.ARRIVED_WITH_LOSSES);
        assertThat(x.lost()).containsExactly(Map.entry(Life.ASHGOAT, 1));
        assertThat(x.lostHead()).isEqualTo(1);
        assertThat(x.line()).isEqualTo("We made Kennel Isle, but the hold ran dry. Load more water next time.");
        Crossing tonic = VoidCrossing.depart(a, KENNEL, true, 0, s);
        while (tonic.outcome() == Outcome.SAILING) {
            tonic.sail(-1);
        }
        assertThat(tonic.outcome()).isEqualTo(Outcome.ARRIVED);
    }

    @Test
    void aSeamUnderThirtyBreachesTheHull() {
        Ark a = ark(62, KENNEL, 0);
        long s = seedWhere(a, KENNEL, w -> w.get(0).damage() > 62 - VoidCrossing.BREACH);
        Crossing x = VoidCrossing.depart(a, KENNEL, true, 12, s);
        assertThat(x.sail(-1)).isEqualTo(Outcome.BREACHED);
        assertThat(x.minSeam()).isLessThan(VoidCrossing.BREACH);
        assertThat(x.day()).isEqualTo(1);
        assertThat(x.line()).isEqualTo("Seam's open to the void. We're limping home. Temper both, smith.");
    }

    @Test
    void theBosunBeatsAnIdleCrewAndTheTonicSavesTheHold() {
        int idleArrived = 0;
        int bosunArrived = 0;
        int tonicLosses = 0;
        int bareLosses = 0;
        for (long s = 0; s < 200; s++) {
            Ark a = ark(70, KENNEL, 0);
            Crossing idle = VoidCrossing.depart(a, KENNEL, true, 6, s);
            while (idle.outcome() == Outcome.SAILING) {
                idle.sail(-1);
            }
            Crossing b = VoidCrossing.bosun(a, KENNEL, true, 6, s);
            Crossing bare = VoidCrossing.bosun(a, KENNEL, false, 6, s);
            idleArrived += idle.outcome() == Outcome.ARRIVED ? 1 : 0;
            bosunArrived += b.outcome() == Outcome.ARRIVED ? 1 : 0;
            tonicLosses += b.lostHead();
            bareLosses += bare.lostHead();
            assertThat(b.outcome()).isNotEqualTo(Outcome.SAILING);
            assertThat(VoidCrossing.bosun(a, KENNEL, true, 6, s).encode()).isEqualTo(b.encode());
        }
        assertThat(bosunArrived).isGreaterThan(idleArrived + 10);
        assertThat(tonicLosses).isZero();
        assertThat(bareLosses).isPositive();
    }

    @Test
    void miraKeepsTheLogAndEncodeIsOneLine() {
        assertThat(VoidCrossing.line(Outcome.SAILING, KENNEL)).isEqualTo("Holding course for Kennel Isle. Keep a hand on the rivet crate.");
        Ark a = ark(90, KENNEL, 0);
        long s = seedWhere(a, KENNEL, w -> w.stream().noneMatch(d -> d.cold() || d.stormSeam() >= 0));
        Crossing x = VoidCrossing.depart(a, KENNEL, false, 2, s);
        assertThat(x.encode()).isEqualTo("VXC 1 SAILING to=Kennel_Isle day=0/6 storms=0 cold=0 minSeam=90 patches=0 spares=2 idle=0 water="
                + a.waterDl() + " lost=0 | Holding course for Kennel Isle. Keep a hand on the rivet crate.");
    }

    @Test
    void theTonicIsTheIslandsVoidCrossing() throws IOException {
        String mech = Files.readString(Path.of("..", "data", "islands", "hephaestus", "mechanics.json"));
        assertThat(mech).contains("\"dual_void_crossing\"").contains("cold_resist+slow_hunger");
        assertThat(ForgeTemperQuest.DUAL_COOKBOOK).contains("dual_void_crossing");
    }
}
