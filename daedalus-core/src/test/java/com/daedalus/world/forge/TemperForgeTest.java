// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ForgeGrades.Material;
import com.daedalus.world.forge.ForgeGrades.Weapon;
import com.daedalus.world.forge.TemperForge.Blank;
import com.daedalus.world.forge.TemperForge.Quench;
import com.daedalus.world.forge.TemperForge.Result;
import com.daedalus.world.forge.TemperForge.Run;
import com.daedalus.world.forge.TemperForge.Strike;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Anvil and Quench (G19): the master's run tempers to the top, every kind of slip costs temper and never
 * gains it, harder metals judge tighter, a cold strike cracks, a dual quench stamps the ark plate, and the
 * temper feeds Forge Weapon Grades unchanged.
 */
class TemperForgeTest {

    private static final Material[] METALS = {Material.COPPER, Material.BRONZE, Material.IRON, Material.STEEL,
        Material.STARMETAL};

    private static Run shiftStrikes(Run r, int by) {
        List<Integer> s = new ArrayList<>();
        for (int t : r.strikesMs()) {
            s.add(t + by);
        }
        return new Run(r.pullMs(), s, r.quenchMs() + Math.max(0, by), r.quench());
    }

    @Test
    void blanksAreSeededAndInRange() {
        assertThat(TemperForge.blank(Material.IRON, 3)).isEqualTo(TemperForge.blank(Material.IRON, 3));
        boolean differs = false;
        for (long seed = 0; seed < 200; seed++) {
            Blank b = TemperForge.blank(Material.STEEL, seed);
            assertThat(b.strikes()).isBetween(5, 8);
            assertThat(b.beatMs()).isBetween(520, 780);
            differs |= !b.equals(TemperForge.blank(Material.STEEL, 0));
        }
        assertThat(differs).isTrue();
    }

    @Test
    void onlyMetalsAreTempered() {
        assertThat(TemperForge.forgeable(Material.IRON)).isTrue();
        assertThat(TemperForge.forgeable(Material.WOOD)).isFalse();
        assertThat(TemperForge.forgeable(Material.OBSIDIAN)).isFalse();
        assertThatThrownBy(() -> TemperForge.blank(Material.STONE, 1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void theMastersRunTempersToTheTopForEveryMetalAndSeed() {
        for (Material m : METALS) {
            for (long seed = 0; seed < 100; seed++) {
                Blank b = TemperForge.blank(m, seed);
                for (Quench q : Quench.values()) {
                    Result r = TemperForge.judge(b, TemperForge.idealRun(b, q));
                    assertThat(r.temper()).as("%s seed %d %s", m, seed, q).isGreaterThanOrEqualTo(98);
                    assertThat(r.cracked()).isFalse();
                    assertThat(r.strikes()).hasSize(b.strikes()).containsOnly(Strike.PERFECT);
                    assertThat(r.arkPlate()).isEqualTo(q == Quench.DUAL);
                }
            }
        }
    }

    @Test
    void mistimingNeverHelpsAndCostsMore() {
        for (Material m : METALS) {
            Blank b = TemperForge.blank(m, 7);
            Run ideal = TemperForge.idealRun(b, Quench.SPRING);
            int prev = TemperForge.judge(b, ideal).temper();
            for (int off = 20; off <= 400; off += 20) {
                int t = TemperForge.judge(b, shiftStrikes(ideal, off)).temper();
                assertThat(t).as("%s off %d", m, off).isLessThanOrEqualTo(prev);
                prev = t;
            }
            assertThat(prev).isLessThan(80);
        }
    }

    @Test
    void harderMetalsJudgeTighter() {
        int[] at = new int[METALS.length];
        for (int i = 0; i < METALS.length; i++) {
            Blank b = TemperForge.blank(METALS[i], 11);
            Result r = TemperForge.judge(b, shiftStrikes(TemperForge.idealRun(b, Quench.MAGMA), 75));
            at[i] = r.hammerPm();
        }
        assertThat(at[0]).isEqualTo(1000);                                     // copper: 75 ms is still perfect
        assertThat(at[METALS.length - 1]).isEqualTo(600);                       // starmetal: only good
        for (int i = 1; i < at.length; i++) {
            assertThat(at[i]).isLessThanOrEqualTo(at[i - 1]);
        }
    }

    @Test
    void pullingTooEarlyOrTooLateLosesHeatMarks() {
        Blank b = TemperForge.blank(Material.IRON, 2);
        Run ideal = TemperForge.idealRun(b, Quench.SPRING);
        assertThat(TemperForge.heatScore(b, b.heatAt(ideal.pullMs()))).isEqualTo(1000);
        assertThat(TemperForge.heatScore(b, b.metal().targetC() + b.metal().bandC())).isEqualTo(1000);
        assertThat(TemperForge.heatScore(b, b.metal().targetC() + b.metal().bandC() + 10)).isEqualTo(900);
        assertThat(TemperForge.heatScore(b, b.metal().targetC() - b.metal().bandC() - 100)).isZero();
        assertThat(b.heatAt(10_000_000)).isEqualTo(b.metal().targetC() + 300);     // it burns, not melts away
        Run early = new Run(ideal.pullMs() - 2000, ideal.strikesMs(), ideal.quenchMs(), Quench.SPRING);
        assertThat(TemperForge.judge(b, early).heatPm()).isLessThan(1000);
    }

    @Test
    void aColdStrikeCracksTheBlankAndCapsTemper() {
        Blank b = TemperForge.blank(Material.STEEL, 4);
        Run ideal = TemperForge.idealRun(b, Quench.DUAL);
        List<Integer> s = new ArrayList<>(ideal.strikesMs());
        int cold = ideal.pullMs() + (b.metal().targetC() - b.workableC() + 40) * 1000 / TemperForge.COOL_C_PER_S;
        s.set(s.size() - 1, cold);
        Result r = TemperForge.judge(b, new Run(ideal.pullMs(), s, cold + 10, Quench.DUAL));
        assertThat(r.strikes().get(s.size() - 1)).isEqualTo(Strike.CRACK);
        assertThat(r.cracked()).isTrue();
        assertThat(r.temper()).isLessThanOrEqualTo(TemperForge.CRACKED_CAP);
        assertThat(r.arkPlate()).isFalse();
    }

    @Test
    void strikesAfterTheQuenchAreWastedAndOverworkCosts() {
        Blank b = TemperForge.blank(Material.BRONZE, 9);
        Run ideal = TemperForge.idealRun(b, Quench.MAGMA);
        List<Integer> s = new ArrayList<>(ideal.strikesMs());
        s.add(ideal.quenchMs() + 50);
        Result wasted = TemperForge.judge(b, new Run(ideal.pullMs(), s, ideal.quenchMs(), Quench.MAGMA));
        assertThat(wasted.strikes().get(s.size() - 1)).isEqualTo(Strike.WASTED);
        assertThat(wasted.hammerPm()).isEqualTo(1000);
        List<Integer> extra = new ArrayList<>(ideal.strikesMs());
        extra.add(ideal.strikesMs().get(extra.size() - 1) + 10);
        Result over = TemperForge.judge(b, new Run(ideal.pullMs(), extra, ideal.quenchMs() + 20, Quench.MAGMA));
        assertThat(over.strikes().get(extra.size() - 1)).isEqualTo(Strike.MISS);
        assertThat(over.hammerPm()).isEqualTo((1000 * b.strikes() - TemperForge.OVERWORK_PM) / b.strikes());
        assertThatThrownBy(() -> TemperForge.judge(b, new Run(10, List.of(), 5, Quench.MAGMA)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TemperForge.judge(b, new Run(10, List.of(500, 400), 900, Quench.MAGMA)))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void dualQuenchHasHalfTheWindow() {
        Blank b = TemperForge.blank(Material.IRON, 5);
        Run ideal = TemperForge.idealRun(b, Quench.SPRING);
        int late = ideal.quenchMs() + 900;                           // about 22 C cooler than the target
        Result spring = TemperForge.judge(b, new Run(ideal.pullMs(), ideal.strikesMs(), late, Quench.SPRING));
        Result dual = TemperForge.judge(b, new Run(ideal.pullMs(), ideal.strikesMs(), late, Quench.DUAL));
        assertThat(spring.quenchPm()).isEqualTo(1000);
        assertThat(dual.quenchPm()).isLessThan(1000);
    }

    @Test
    void temperFeedsForgeWeaponGrades() {
        Blank b = TemperForge.blank(Material.STARMETAL, 1);
        Result r = TemperForge.judge(b, TemperForge.idealRun(b, Quench.DUAL));
        assertThat(r.tier()).isEqualTo(ForgeGrades.tier(r.temper()));
        assertThat(r.grade(Weapon.SWORD, Material.STARMETAL))
                .isEqualTo(ForgeGrades.grade(Weapon.SWORD, Material.STARMETAL, r.temper()));
        Result sloppy = TemperForge.judge(b, shiftStrikes(TemperForge.idealRun(b, Quench.DUAL), 300));
        assertThat(sloppy.grade(Weapon.BLASTER, Material.STARMETAL).damagePm())
                .isLessThanOrEqualTo(r.grade(Weapon.BLASTER, Material.STARMETAL).damagePm());
    }

    @Test
    void judgingIsPureAndReplayable() {
        Blank b = TemperForge.blank(Material.COPPER, 13);
        Run run = shiftStrikes(TemperForge.idealRun(b, Quench.SPRING), 95);
        assertThat(TemperForge.judge(b, run)).isEqualTo(TemperForge.judge(b, run));
    }
}
