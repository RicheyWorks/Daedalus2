// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ArkDrydock.Ark;
import com.daedalus.world.forge.ArkDrydock.ArkClass;
import com.daedalus.world.forge.ArkDrydock.Plate;
import com.daedalus.world.forge.RivetLine.Result;
import com.daedalus.world.forge.RivetLine.Seat;
import com.daedalus.world.forge.RivetLine.Set;
import com.daedalus.world.forge.RivetLine.Tray;
import com.daedalus.world.forge.TemperForge.Quench;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class RivetLineTest {

    @Test
    void theTrayIsSeededWithOneRivetPerHole() {
        for (ArkClass c : ArkClass.values()) {
            Tray t = RivetLine.tray(c, 11L);
            assertThat(t.holes()).isEqualTo(c.plates() * ArkDrydock.RIVETS_PER_SEAM);
            assertThat(t.readyMs()).allSatisfy(ms -> assertThat(ms).isBetween(1500, 2450));
            assertThat(t).isEqualTo(RivetLine.tray(c, 11L));
        }
        assertThat(RivetLine.tray(ArkClass.SKIFF, 12L)).isNotEqualTo(RivetLine.tray(ArkClass.SKIFF, 11L));
    }

    @Test
    void seatsFollowTheWindowAndTheStrikes() {
        assertThat(RivetLine.seat(2000, new Set(1999, 3))).isEqualTo(Seat.SPOILED);
        assertThat(RivetLine.seat(2000, null)).isEqualTo(Seat.SPOILED);
        assertThat(RivetLine.seat(2000, new Set(2000, 3))).isEqualTo(Seat.TIGHT);
        assertThat(RivetLine.seat(2000, new Set(2800, 5))).isEqualTo(Seat.TIGHT);
        assertThat(RivetLine.seat(2000, new Set(2801, 3))).isEqualTo(Seat.LOOSE);
        assertThat(RivetLine.seat(2000, new Set(2400, 2))).isEqualTo(Seat.SNUG);
        assertThat(RivetLine.seat(2000, new Set(2400, 1))).isEqualTo(Seat.LOOSE);
    }

    @Test
    void theMasterFillsEveryHoleTight() {
        Tray t = RivetLine.tray(ArkClass.BARGE, 3L);
        Result r = RivetLine.judge(t, RivetLine.master(t));
        assertThat(r.tight()).isEqualTo(t.holes());
        assertThat(r.rivetsPerSeam()).hasSize(ArkClass.BARGE.plates()).containsOnly(ArkDrydock.RIVETS_PER_SEAM);
        assertThat(r.line()).isEqualTo("Every hole filled hot. She'll hold the void.");
    }

    @Test
    void eagerHammeringSpoilsTheLine() {
        Tray t = RivetLine.tray(ArkClass.SKIFF, 4L);
        List<Set> early = new ArrayList<>();
        for (int i = 0; i < t.holes(); i++) {
            early.add(new Set(1000, 3));
        }
        Result r = RivetLine.judge(t, early);
        assertThat(r.spoiled()).isEqualTo(t.holes());
        assertThat(r.rivetsPerSeam()).containsOnly(0);
        assertThat(r.line()).contains("Wait for the colour");
    }

    @Test
    void missingSetsSpoilTheRest() {
        Tray t = RivetLine.tray(ArkClass.SKIFF, 5L);
        Result r = RivetLine.judge(t, RivetLine.master(t).subList(0, 8));
        assertThat(r.tight()).isEqualTo(8);
        assertThat(r.spoiled()).isEqualTo(t.holes() - 8);
        assertThat(r.rivetsPerSeam()).containsExactly(4, 4, 0, 0, 0, 0);
        assertThat(r.line()).contains("Wait for the colour");
    }

    @Test
    void aFewLooseHeadsGetAWarning() {
        Tray t = RivetLine.tray(ArkClass.SKIFF, 6L);
        List<Set> sets = new ArrayList<>(RivetLine.master(t));
        sets.set(0, new Set(t.readyMs().get(0) + 900, 3));
        sets.set(5, new Set(t.readyMs().get(5) + 100, 2));
        Result r = RivetLine.judge(t, sets);
        assertThat(r.loose()).isEqualTo(1);
        assertThat(r.snug()).isEqualTo(1);
        assertThat(r.rivetsPerSeam()).containsExactly(3, 4, 4, 4, 4, 4);
        assertThat(r.line()).contains("loose heads");
        assertThat(r.seats().get(0)).isEqualTo(Seat.LOOSE);
    }

    @Test
    void lateHandsGetBrannocsComplaint() {
        Tray t = RivetLine.tray(ArkClass.SKIFF, 7L);
        List<Set> sets = new ArrayList<>();
        for (int r : t.readyMs()) {
            sets.add(new Set(r + 1000, 3));
        }
        Result r = RivetLine.judge(t, sets);
        assertThat(r.loose()).isEqualTo(t.holes());
        assertThat(r.line()).isEqualTo("Hull wants tempered rivets, not soft iron.");
    }

    @Test
    void theRivetsGoStraightIntoTheDrydock() {
        Tray t = RivetLine.tray(ArkClass.SKIFF, 8L);
        Plate p = new Plate(90, Quench.DUAL, true);
        List<Plate> plates = Collections.nCopies(ArkClass.SKIFF.plates(), p);
        Result good = RivetLine.judge(t, RivetLine.master(t));
        Ark ark = new Ark(ArkClass.SKIFF, plates, good.rivetsPerSeam(), Map.of(), 0);
        for (int i = 0; i < ArkClass.SKIFF.plates(); i++) {
            assertThat(ArkDrydock.seamStrength(ark, i)).isEqualTo(90);
        }
        List<Set> sets = new ArrayList<>(RivetLine.master(t));
        sets.set(0, new Set(0, 3));
        sets.set(1, new Set(0, 3));
        Result twoShort = RivetLine.judge(t, sets);
        Ark weak = new Ark(ArkClass.SKIFF, plates, twoShort.rivetsPerSeam(), Map.of(), 0);
        assertThat(ArkDrydock.seamStrength(weak, 0)).isEqualTo(90 - 2 * ArkDrydock.MISSING_RIVET_COST);
    }

    @Test
    void judgingIsPure() {
        Tray t = RivetLine.tray(ArkClass.LONGARK, 9L);
        assertThat(RivetLine.judge(t, RivetLine.master(t))).isEqualTo(RivetLine.judge(t, RivetLine.master(t)));
        assertThat(RivetLine.judge(t, List.of()).spoiled()).isEqualTo(t.holes());
    }
}
