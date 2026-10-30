// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ScarDig.Action;
import com.daedalus.world.forge.ScarDig.Cell;
import com.daedalus.world.forge.ScarDig.Kit;
import com.daedalus.world.forge.ScarDig.Plan;
import com.daedalus.world.forge.ScarDig.Result;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ScarDigTest {

    private static final Kit BARE = new Kit(false, false, 0);

    /** All rock except the given cells (x, y, cell triples). */
    private static Plan scar(Object... xyc) {
        List<Cell> cells = new ArrayList<>(Collections.nCopies(ScarDig.SIZE * ScarDig.SIZE, Cell.ROCK));
        for (int i = 0; i < xyc.length; i += 3) {
            cells.set((Integer) xyc[i + 1] * ScarDig.SIZE + (Integer) xyc[i], (Cell) xyc[i + 2]);
        }
        return new Plan(cells);
    }

    private static List<Action> swings(int x, int y, int n) {
        return new ArrayList<>(Collections.nCopies(n, Action.swing(x, y)));
    }

    @Test
    void theScarIsSeededAndRoughlyAsRichAsTheIslandSays() {
        assertThat(ScarDig.plan(4L)).isEqualTo(ScarDig.plan(4L));
        assertThat(ScarDig.plan(5L)).isNotEqualTo(ScarDig.plan(4L));
        Map<Cell, Integer> n = new EnumMap<>(Cell.class);
        Set<Plan> distinct = new HashSet<>();
        for (long s = 0; s < 200; s++) {
            Plan p = ScarDig.plan(s);
            distinct.add(p);
            assertThat(p.cells()).hasSize(64);
            p.cells().forEach(c -> n.merge(c, 1, Integer::sum));
        }
        assertThat(distinct).hasSize(200);
        int total = 200 * 64;
        assertThat(n.get(Cell.STARMETAL) * 1000 / total).isBetween(45, 75);
        assertThat(n.get(Cell.EMBERITE) * 1000 / total).isBetween(65, 95);
        assertThat(n.get(Cell.SLAG) * 1000 / total).isBetween(140, 180);
        assertThat(n.get(Cell.VENT) * 1000 / total).isBetween(45, 75);
    }

    @Test
    void badScarsAndPacksAreRefused() {
        assertThatThrownBy(() -> new Plan(List.of(Cell.ROCK))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Kit(false, false, 4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Kit(false, false, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThat(new Kit(false, true, 0).strike()).isEqualTo(2);
        assertThat(BARE.strike()).isEqualTo(1);
    }

    @Test
    void eachCellBreaksAfterItsHardnessAndEverySwingCostsWater() {
        Plan p = scar(0, 0, Cell.STARMETAL, 1, 0, Cell.EMBERITE, 2, 0, Cell.SLAG);
        assertThat(ScarDig.run(p, BARE, swings(0, 0, 3)).starmetal()).isZero();
        Result r = ScarDig.run(p, BARE, swings(0, 0, 4));
        assertThat(r.starmetal()).isEqualTo(1);
        assertThat(r.broken()).isEqualTo(1);
        assertThat(r.water()).isEqualTo(ScarDig.START_WATER - 4 * ScarDig.THIRST_PER_SWING);
        List<Action> all = swings(1, 0, 3);
        all.addAll(swings(2, 0, 1));
        all.addAll(swings(3, 0, 2));
        Result r2 = ScarDig.run(p, BARE, all);
        assertThat(r2.emberite()).isEqualTo(1);
        assertThat(r2.slag()).isEqualTo(1);
        assertThat(r2.broken()).isEqualTo(3);
        assertThat(Cell.ROCK.hardness()).isEqualTo(2);
        assertThat(Cell.VENT.hardness()).isEqualTo(1);
    }

    @Test
    void drydockShiftStrikesTwice() {
        Plan p = scar(0, 0, Cell.STARMETAL, 1, 0, Cell.EMBERITE);
        Kit shift = new Kit(false, true, 0);
        assertThat(ScarDig.run(p, shift, swings(0, 0, 2)).starmetal()).isEqualTo(1);
        Result r = ScarDig.run(p, shift, swings(1, 0, 2));
        assertThat(r.emberite()).isEqualTo(1);
        assertThat(r.swings()).isEqualTo(2);
    }

    @Test
    void ventsScaldAndCanteensRefill() {
        Plan p = scar(0, 0, Cell.VENT);
        Result r = ScarDig.run(p, BARE, swings(0, 0, 1));
        assertThat(r.water()).isEqualTo(ScarDig.START_WATER - ScarDig.THIRST_PER_SWING - ScarDig.VENT_SCALD);
        List<Action> a = swings(1, 0, 20);
        a.add(Action.drink());
        a.add(Action.drink());
        Result d = ScarDig.run(p, new Kit(false, false, 1), a);
        assertThat(d.water()).isEqualTo(ScarDig.START_WATER - 40 + ScarDig.CANTEEN);
        assertThat(d.wasted()).isEqualTo(18 + 1); // 18 swings on broken rock, one dry canteen
        Result capped = ScarDig.run(p, new Kit(false, false, 1), List.of(Action.swing(3, 3), Action.drink()));
        assertThat(capped.water()).isEqualTo(ScarDig.START_WATER);
    }

    @Test
    void wastedSwingsStillCostWater() {
        Plan p = scar();
        Result r = ScarDig.run(p, BARE, List.of(Action.swing(-1, 0), Action.swing(0, 8), Action.swing(8, 0),
                Action.swing(0, 0), Action.swing(0, 0), Action.swing(0, 0)));
        assertThat(r.wasted()).isEqualTo(4);
        assertThat(r.broken()).isEqualTo(1);
        assertThat(r.water()).isEqualTo(ScarDig.START_WATER - 6 * ScarDig.THIRST_PER_SWING);
    }

    @Test
    void faintingStopsTheDigAndDropsHalfTheHaul() {
        Plan p = scar(0, 0, Cell.STARMETAL, 1, 0, Cell.STARMETAL, 2, 0, Cell.STARMETAL, 3, 0, Cell.EMBERITE);
        List<Action> a = new ArrayList<>();
        for (int x = 0; x < 3; x++) {
            a.addAll(swings(x, 0, 4));
        }
        a.addAll(swings(3, 0, 3));
        a.addAll(swings(4, 4, 40));
        Result r = ScarDig.run(p, BARE, a);
        assertThat(r.fainted()).isTrue();
        assertThat(r.water()).isZero();
        assertThat(r.swings()).isEqualTo(ScarDig.START_WATER / ScarDig.THIRST_PER_SWING);
        assertThat(r.starmetal()).isEqualTo(1);
        assertThat(r.emberite()).isZero();
        assertThat(r.line()).isEqualTo("The scar took your water before your ore. Canteen first, pick second.");
    }

    @Test
    void scarProspectorLuckRoundsUp() {
        assertThat(ScarDig.luck(0)).isZero();
        assertThat(ScarDig.luck(1)).isEqualTo(2);
        assertThat(ScarDig.luck(10)).isEqualTo(11);
        assertThat(ScarDig.luck(11)).isEqualTo(13);
        Plan p = scar(0, 0, Cell.STARMETAL);
        Result r = ScarDig.run(p, new Kit(true, false, 0), swings(0, 0, 4));
        assertThat(r.starmetal()).isEqualTo(2);
        assertThat(r.ingots()).isEqualTo(1);
    }

    @Test
    void theProspectorNeverFaintsNorTouchesAVentAndTonicsPay() {
        int bare = 0;
        int tonics = 0;
        for (long s = 0; s < 100; s++) {
            Plan p = ScarDig.plan(s);
            for (Kit k : List.of(BARE, new Kit(false, false, 3), new Kit(true, true, 3))) {
                List<Action> a = ScarDig.prospector(p, k);
                for (Action x : a) {
                    if (!x.isDrink()) {
                        assertThat(p.at(x.x(), x.y())).isIn(Cell.STARMETAL, Cell.EMBERITE);
                    }
                }
                Result r = ScarDig.run(p, k, a);
                assertThat(r.fainted()).isFalse();
                assertThat(r.wasted()).isZero();
                assertThat(ScarDig.run(p, k, a)).isEqualTo(r);
                if (k.equals(BARE)) {
                    bare += r.ingots();
                } else if (k.prospector()) {
                    tonics += r.ingots();
                }
            }
        }
        assertThat(tonics).isGreaterThan(bare + bare / 4);
    }

    @Test
    void hesperHasALineForEverySack() {
        assertThat(ScarDig.line(true, 9, 9)).startsWith("The scar took your water");
        assertThat(ScarDig.line(false, 3, 6)).isEqualTo("Starmetal enough for a plate. Weighed, logged, off to the drydock.");
        assertThat(ScarDig.line(false, 1, 3)).isEqualTo("Some shine in the sack. Swing where the veins glow.");
        assertThat(ScarDig.line(false, 0, 0)).isEqualTo("Rock and slag. The veins glow; the rock doesn't.");
        Result r = ScarDig.run(scar(0, 0, Cell.SLAG), BARE, swings(0, 0, 1));
        assertThat(r.encode()).isEqualTo("SCR 1 star=0 ember=0 slag=1 broken=1 swings=1 wasted=0 water=58 fainted=0 ingots=0 | "
                + "Rock and slag. The veins glow; the rock doesn't.");
    }

    @Test
    void theIslandDataKnowsTheIngotAndBothTonics() throws IOException {
        Path island = Path.of("..", "data", "islands", "hephaestus");
        assertThat(Files.readString(island.resolve("items.json"))).contains("\"starmetal_ingot\"");
        String mech = Files.readString(island.resolve("mechanics.json"));
        assertThat(mech).contains("\"dual_scar_prospector\"").contains("ore_luck_+10pct").contains("\"dual_drydock_shift\"");
        assertThat(ForgeTemperQuest.DUAL_COOKBOOK).contains("dual_scar_prospector", "dual_drydock_shift");
    }
}
