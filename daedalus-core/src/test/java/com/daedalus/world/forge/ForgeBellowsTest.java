// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ForgeBellows.Plan;
import com.daedalus.world.forge.ForgeBellows.Result;
import com.daedalus.world.forge.ForgeBellows.Tier;
import com.daedalus.world.forge.ForgeGrades.Material;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ForgeBellowsTest {

    private static Result steady(Material m, int oxen, long seed) {
        Plan p = ForgeBellows.plan(m, oxen, seed);
        return ForgeBellows.run(p, ForgeBellows.steadyHand(p));
    }

    @Test
    void theDraughtIsSeededAndTheOxenAreCapped() {
        Plan a = ForgeBellows.plan(Material.IRON, 1, 42L);
        Plan b = ForgeBellows.plan(Material.IRON, 1, 42L);
        assertThat(a).isEqualTo(b);
        assertThat(a.gusts()).hasSize(ForgeBellows.TICKS);
        long gusts = a.gusts().stream().filter(g -> g).count();
        assertThat(gusts).isBetween(3L, 20L);
        assertThat(ForgeBellows.plan(Material.IRON, 1, 43L).gusts()).isNotEqualTo(a.gusts());
        assertThatThrownBy(() -> ForgeBellows.plan(Material.IRON, 3, 1L)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ForgeBellows.plan(Material.IRON, -1, 1L)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ForgeBellows.plan(Material.WOOD, 0, 1L)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void eachForgeoxAddsFifteenPercentToAPump() {
        assertThat(ForgeBellows.plan(Material.STEEL, 0, 1L).pumpC()).isEqualTo(30);
        assertThat(ForgeBellows.plan(Material.STEEL, 1, 1L).pumpC()).isEqualTo(34);
        assertThat(ForgeBellows.plan(Material.STEEL, 2, 1L).pumpC()).isEqualTo(39);
        assertThat(steady(Material.STEEL, 0, 1L).forgeSpeedPm()).isEqualTo(1000);
        assertThat(steady(Material.STEEL, 2, 1L).forgeSpeedPm()).isEqualTo(1300);
    }

    @Test
    void oxBonusMatchesTheIslandLivestockData() throws IOException {
        String json = Files.readString(Path.of("..", "data", "islands", "hephaestus", "livestock.json"));
        Matcher m = Pattern.compile("\"forgeox_bellows\"\\s*:\\s*\\{\\s*\"heads\"\\s*:\\s*(\\d+),\\s*\"forge_speed_bonus_each\"\\s*:\\s*([0-9.]+)")
                .matcher(json);
        assertThat(m.find()).isTrue();
        assertThat(Integer.parseInt(m.group(1))).isEqualTo(ForgeBellows.MAX_OXEN);
        assertThat(Math.round(Double.parseDouble(m.group(2)) * 100)).isEqualTo(ForgeBellows.OX_BONUS_PCT);
    }

    @Test
    void aSteadyHandHoldsTheSoftMetalsSteady() {
        for (Material m : List.of(Material.COPPER, Material.BRONZE)) {
            for (long seed = 0; seed < 10; seed++) {
                Result r = steady(m, 0, seed);
                assertThat(r.tier()).as(m + " seed " + seed).isEqualTo(Tier.STEADY);
                assertThat(r.readyToPull()).isTrue();
                assertThat(r.cinders()).isZero();
                assertThat(r.line()).contains("ready");
            }
        }
    }

    @Test
    void forgeoxOnTheBellowsBuysYouTime() {
        for (Material m : List.of(Material.IRON, Material.STEEL, Material.STARMETAL)) {
            int none = 0;
            int two = 0;
            for (long seed = 0; seed < 10; seed++) {
                none += steady(m, 0, seed).inBandTicks();
                two += steady(m, 2, seed).inBandTicks();
            }
            assertThat(two).as(m.name()).isGreaterThan(none);
        }
    }

    @Test
    void starmetalNeedsTheOxen() {
        int total = 0;
        for (long seed = 0; seed < 20; seed++) {
            Result r = steady(Material.STARMETAL, 0, seed);
            assertThat(r.tier()).isIn(Tier.FITFUL, Tier.COLD);
            total += r.inBandPm();
        }
        assertThat(total / 20).isLessThan(300);
        assertThat(steady(Material.STARMETAL, 0, 0L).line()).isEqualTo("Forgeox on the bellows buys you time. Don't waste it.");
    }

    @Test
    void spammingTheBellowsChokesTheBedOnCinders() {
        Plan p = ForgeBellows.plan(Material.COPPER, 2, 1L);
        Result r = ForgeBellows.run(p, Collections.nCopies(ForgeBellows.TICKS, true));
        assertThat(r.cinders()).isEqualTo(ForgeBellows.COAL);
        assertThat(r.doused()).isTrue();
        assertThat(r.readyToPull()).isFalse();
        assertThat(r.peakC()).isGreaterThan(p.metal().targetC() + ForgeBellows.CINDER_BANDS * p.metal().bandC() - ForgeBellows.CINDER_DROP_C);
        assertThat(r.tier()).isEqualTo(Tier.COLD);
        assertThat(r.line()).contains("cinders");
        assertThat(r.finalC()).isEqualTo(20);
    }

    @Test
    void noPumpingLetsTheBedFallToAmbient() {
        Plan p = ForgeBellows.plan(Material.IRON, 1, 5L);
        Result r = ForgeBellows.run(p, List.of());
        assertThat(r.inBandTicks()).isZero();
        assertThat(r.finalC()).isEqualTo(20);
        assertThat(r.peakC()).isEqualTo(ForgeBellows.START_C);
        assertThat(r.tier()).isEqualTo(Tier.COLD);
        assertThat(r.line()).isEqualTo("Cold bed, cold iron. Again.");
    }

    @Test
    void aShortInputMeansNoPumpForTheRest() {
        Plan p = ForgeBellows.plan(Material.BRONZE, 0, 3L);
        List<Boolean> full = new ArrayList<>(ForgeBellows.steadyHand(p));
        List<Boolean> padded = new ArrayList<>(full.subList(0, 60));
        padded.addAll(Collections.nCopies(60, false));
        assertThat(ForgeBellows.run(p, full.subList(0, 60))).isEqualTo(ForgeBellows.run(p, padded));
        assertThat(ForgeBellows.run(p, full)).isEqualTo(ForgeBellows.run(p, full));
    }

    @Test
    void theBandIsTheMetalsOwnWorkingBand() {
        Plan p = ForgeBellows.plan(Material.IRON, 2, 9L);
        Result r = ForgeBellows.run(p, ForgeBellows.steadyHand(p));
        int heat = ForgeBellows.START_C;
        int in = 0;
        List<Boolean> pumps = ForgeBellows.steadyHand(p);
        for (int t = 0; t < ForgeBellows.TICKS; t++) {
            heat = ForgeBellows.step(p, t, heat, pumps.get(t));
            if (Math.abs(heat - 850) <= 40) {
                in++;
            }
        }
        assertThat(r.inBandTicks()).isEqualTo(in);
        assertThat(r.inBandPm()).isEqualTo(in * 1000 / ForgeBellows.TICKS);
    }

    @Test
    void tiersAndLinesCoverEveryShiftBell() {
        assertThat(ForgeBellows.line(Tier.WARM, false, 1)).contains("rhythm");
        assertThat(ForgeBellows.line(Tier.FITFUL, false, 1)).contains("colour");
        assertThat(ForgeBellows.line(Tier.FITFUL, false, 0)).contains("Forgeox");
        assertThat(ForgeBellows.line(Tier.COLD, false, 0)).contains("Forgeox");
        assertThat(ForgeBellows.line(Tier.STEADY, true, 2)).contains("cinders");
        assertThat(steady(Material.STEEL, 0, 0L).tier()).isEqualTo(Tier.WARM);
    }
}
