// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ArkDrydock.Life;
import com.daedalus.world.forge.ForgeGrades.Material;
import com.daedalus.world.forge.ForgeTemperQuest.Outcome;
import com.daedalus.world.forge.ForgeTemperQuest.Quest;
import com.daedalus.world.forge.ForgeTemperQuest.Step;
import com.daedalus.world.forge.TemperForge.Blank;
import com.daedalus.world.forge.TemperForge.Quench;
import com.daedalus.world.forge.TemperForge.Result;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

class ForgeTemperQuestTest {

    private static final Path MECH = Path.of("..", "data", "islands", "hephaestus", "mechanics.json");

    private static Result forged(Quench q) {
        Blank b = TemperForge.blank(Material.STEEL, 7L);
        return TemperForge.judge(b, TemperForge.idealRun(b, q));
    }

    private static void waterAllPens(Quest q) {
        for (Life p : ForgeTemperQuest.PENS) {
            q.waterPen(p, p.dlPerDay());
        }
    }

    private static void waterAllBeds(Quest q) {
        for (int i = 0; i < ForgeTemperQuest.BEDS; i++) {
            q.waterBed(i, ForgeTemperQuest.BED_DL);
        }
    }

    @Test
    void glowWeightsMatchTheIslandBalance() throws IOException {
        String json = Files.readString(MECH);
        Matcher m = Pattern.compile("\"balance\"\\s*:\\s*\\{\\s*\"water\"\\s*:\\s*(\\d+),\\s*\"animals\"\\s*:\\s*(\\d+),"
                + "\\s*\"herbs3\"\\s*:\\s*(\\d+),\\s*\"tea\"\\s*:\\s*(\\d+)").matcher(json);
        assertThat(m.find()).isTrue();
        assertThat(List.of(m.group(1), m.group(2), m.group(3), m.group(4))).containsExactly(
                "" + ForgeTemperQuest.GLOW_WATER, "" + ForgeTemperQuest.GLOW_ANIMALS,
                "" + ForgeTemperQuest.GLOW_HERBS, "" + ForgeTemperQuest.GLOW_TEA);
        assertThat(ForgeTemperQuest.GLOW_WATER + ForgeTemperQuest.GLOW_ANIMALS + ForgeTemperQuest.GLOW_HERBS
                + ForgeTemperQuest.GLOW_TEA).isEqualTo(100);
    }

    @Test
    void cookbookAndCleanSourcesMatchMechanicsJson() throws IOException {
        String json = Files.readString(MECH);
        List<String> duals = new ArrayList<>();
        Matcher d = Pattern.compile("\"id\"\\s*:\\s*\"(dual_[a-z_]+)\"").matcher(json);
        while (d.find()) {
            duals.add(d.group(1));
        }
        assertThat(duals).containsExactlyInAnyOrderElementsOf(ForgeTemperQuest.DUAL_COOKBOOK);
        assertThat(json).containsPattern("\"dual_recipe_count\"\\s*:\\s*" + ForgeTemperQuest.DUAL_COOKBOOK.size());
        List<String> clean = new ArrayList<>();
        Matcher c = Pattern.compile("\"(\\w+)\"\\s*:\\s*\"clean\"").matcher(json);
        while (c.find()) {
            clean.add(c.group(1));
        }
        assertThat(clean).containsExactlyInAnyOrderElementsOf(ForgeTemperQuest.CLEAN_SOURCES);
    }

    @Test
    void theWholeQuestInOrderEndsTempered() {
        Quest q = new Quest();
        assertThat(q.current()).isEqualTo(Step.ARRIVAL);
        assertThat(q.drink("HotSpring_Clean")).isEqualTo(Outcome.STEP_DONE);
        assertThat(q.glow()).isEqualTo(30);
        waterAllPens(q);
        assertThat(q.current()).isEqualTo(Step.TONIC);
        assertThat(q.glow()).isEqualTo(60);
        assertThat(q.quenchTonic("dual_drydock_shift", Quench.DUAL)).isEqualTo(Outcome.STEP_DONE);
        assertThat(q.tonic()).isEqualTo("dual_drydock_shift");
        assertThat(q.leavePlate(forged(Quench.DUAL))).isEqualTo(Outcome.STEP_DONE);
        assertThat(q.current()).isEqualTo(Step.GLOW);
        assertThat(q.glow()).isEqualTo(70);
        assertThat(q.waterBed(0, 10)).isEqualTo(Outcome.PROGRESS);
        assertThat(q.glow()).isEqualTo(80);
        assertThat(q.waterBed(1, 10)).isEqualTo(Outcome.PROGRESS);
        assertThat(q.waterBed(2, 10)).isEqualTo(Outcome.QUEST_COMPLETE);
        assertThat(q.complete()).isTrue();
        assertThat(q.current()).isEqualTo(Step.COMPLETE);
        assertThat(q.glow()).isEqualTo(100);
        assertThat(q.drink("SteamVentCatch")).isEqualTo(Outcome.ALREADY_DONE);
    }

    @Test
    void stepsCanBeDoneOutOfOrderAndTheLastOneClosesTheQuest() {
        Quest q = new Quest();
        waterAllBeds(q);
        assertThat(q.leavePlate(forged(Quench.DUAL))).isEqualTo(Outcome.STEP_DONE);
        assertThat(q.quenchTonic("dual_lava_runner", Quench.DUAL)).isEqualTo(Outcome.STEP_DONE);
        waterAllPens(q);
        assertThat(q.current()).isEqualTo(Step.ARRIVAL);
        assertThat(q.drink("SaltStill_Basalt")).isEqualTo(Outcome.QUEST_COMPLETE);
    }

    @Test
    void dirtyWaterAndForeignPensAreRefused() {
        Quest q = new Quest();
        assertThat(q.drink("AshWell_Dirty")).isEqualTo(Outcome.DIRTY_WATER);
        assertThat(q.drink("QuenchTrough_Forge")).isEqualTo(Outcome.DIRTY_WATER);
        assertThat(q.current()).isEqualTo(Step.ARRIVAL);
        assertThat(q.waterPen(Life.PET, 50)).isEqualTo(Outcome.NOT_A_PEN);
        assertThat(q.waterPen(Life.ASHGOAT, 0)).isEqualTo(Outcome.BAD_AMOUNT);
        assertThat(q.waterBed(3, 10)).isEqualTo(Outcome.NO_SUCH_BED);
        assertThat(q.waterBed(0, 9)).isEqualTo(Outcome.BAD_AMOUNT);
        assertThat(q.glow()).isZero();
    }

    @Test
    void tonicMustBeFromTheBookAndQuenchedDual() {
        Quest q = new Quest();
        assertThat(q.quenchTonic("tea_ashmint_draught", Quench.DUAL)).isEqualTo(Outcome.UNKNOWN_RECIPE);
        assertThat(q.quenchTonic("dual_void_crossing", Quench.MAGMA)).isEqualTo(Outcome.NOT_DUAL);
        assertThat(q.quenchTonic("dual_void_crossing", Quench.SPRING)).isEqualTo(Outcome.NOT_DUAL);
        assertThat(q.tonic()).isEmpty();
        assertThat(q.quenchTonic("dual_void_crossing", Quench.DUAL)).isEqualTo(Outcome.STEP_DONE);
        assertThat(q.quenchTonic("dual_lava_runner", Quench.DUAL)).isEqualTo(Outcome.ALREADY_DONE);
        assertThat(q.tonic()).isEqualTo("dual_void_crossing");
    }

    @Test
    void onlyAStampedPlateCounts() {
        Quest q = new Quest();
        assertThat(q.leavePlate(forged(Quench.MAGMA))).isEqualTo(Outcome.NOT_STAMPED);
        assertThat(q.leavePlate(forged(Quench.SPRING))).isEqualTo(Outcome.NOT_STAMPED);
        assertThat(q.leavePlate(forged(Quench.DUAL))).isEqualTo(Outcome.STEP_DONE);
        assertThat(q.leavePlate(forged(Quench.DUAL))).isEqualTo(Outcome.ALREADY_DONE);
    }

    @Test
    void unfinishedTroughsAndBedsDryOutAtTheShiftBell() {
        Quest q = new Quest();
        for (Life p : ForgeTemperQuest.PENS.subList(0, 5)) {
            q.waterPen(p, p.dlPerDay());
        }
        q.waterBed(0, 10);
        assertThat(q.glow()).isEqualTo(25 + 10);
        q.endShift();
        assertThat(q.shifts()).isEqualTo(1);
        assertThat(q.glow()).isZero();
        assertThat(q.waterPen(Life.VENT_BEES, 10)).isEqualTo(Outcome.PROGRESS);
        assertThat(q.current()).isEqualTo(Step.ARRIVAL);
    }

    @Test
    void finishedPensAndBedsSurviveTheShiftBell() {
        Quest q = new Quest();
        waterAllPens(q);
        waterAllBeds(q);
        q.endShift();
        assertThat(q.glow()).isEqualTo(60);
        assertThat(q.waterPen(Life.FORGEOX, 120)).isEqualTo(Outcome.ALREADY_DONE);
        assertThat(q.waterBed(1, 10)).isEqualTo(Outcome.ALREADY_DONE);
    }

    @Test
    void pensAccumulateWithinAShiftUntilEveryTroughIsFull() {
        Quest q = new Quest();
        assertThat(q.waterPen(Life.FORGEOX, 60)).isEqualTo(Outcome.PROGRESS);
        assertThat(q.glow()).isZero();
        assertThat(q.waterPen(Life.FORGEOX, 60)).isEqualTo(Outcome.PROGRESS);
        assertThat(q.glow()).isEqualTo(5);
        for (Life p : ForgeTemperQuest.PENS) {
            if (p != Life.FORGEOX) {
                q.waterPen(p, p.dlPerDay());
            }
        }
        assertThat(q.glow()).isEqualTo(30);
    }

    @Test
    void keeperHasALineForEveryStep() {
        for (Step s : Step.values()) {
            assertThat(ForgeTemperQuest.keeperLine(s)).isNotBlank();
        }
        assertThat(ForgeTemperQuest.keeperLine(Step.COMPLETE)).contains("tempered");
    }
}
