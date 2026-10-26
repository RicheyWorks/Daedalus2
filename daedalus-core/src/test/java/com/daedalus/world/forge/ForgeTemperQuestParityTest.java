// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ArkDrydock.Life;
import com.daedalus.world.forge.ForgeGrades.Material;
import com.daedalus.world.forge.ForgeTemperQuest.Outcome;
import com.daedalus.world.forge.ForgeTemperQuest.Quest;
import com.daedalus.world.forge.TemperForge.Blank;
import com.daedalus.world.forge.TemperForge.Quench;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * C++ = Java, line for line (G51): engines/unreal/core-test/forge_temper_quest_parity.txt is written by
 * forge_temper_quest_core_test.cpp --write from DaedalusForgeTemperQuestCore.h.
 */
class ForgeTemperQuestParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "forge_temper_quest_parity.txt");
    private static final String[] SOURCES = {"HotSpring_Clean", "SteamVentCatch", "RainCatch_Ash", "SaltStill_Basalt",
        "AshWell_Dirty", "QuenchTrough_Forge"};
    private static final Material[] METALS = {Material.COPPER, Material.BRONZE, Material.IRON, Material.STEEL,
        Material.STARMETAL};

    /** The same seeded event script the C++ test plays. */
    static List<String> play(int seed) {
        SplittableRandom rng = new SplittableRandom(seed * 131L + 9);
        Quest q = new Quest();
        List<String> out = new ArrayList<>();
        Life[] life = Life.values();
        for (int e = 0; e < 60; e++) {
            int kind = rng.nextInt(9);
            Outcome o = Outcome.PROGRESS;
            String ev;
            switch (kind) {
                case 0 -> {
                    String s = SOURCES[rng.nextInt(6)];
                    o = q.drink(s);
                    ev = "drink " + s;
                }
                case 1 -> {
                    Life p = life[rng.nextInt(life.length)];
                    int dl = rng.nextInt(130);
                    o = q.waterPen(p, dl);
                    ev = "pen " + p.id() + " " + dl;
                }
                case 2 -> {
                    int bed = rng.nextInt(4);
                    int dl = rng.nextInt(15);
                    o = q.waterBed(bed, dl);
                    ev = "bed " + bed + " " + dl;
                }
                case 3 -> {
                    int r = rng.nextInt(9);
                    Quench path = Quench.values()[rng.nextInt(3)];
                    String recipe = r < 8 ? ForgeTemperQuest.DUAL_COOKBOOK.get(r) : "tea_ashmint_draught";
                    o = q.quenchTonic(recipe, path);
                    ev = "tonic " + recipe + " " + path.ordinal();
                }
                case 4 -> {
                    int m = rng.nextInt(5);
                    int bs = rng.nextInt(1000);
                    Quench path = Quench.values()[rng.nextInt(3)];
                    Blank b = TemperForge.blank(METALS[m], bs);
                    o = q.leavePlate(TemperForge.judge(b, TemperForge.idealRun(b, path)));
                    ev = "plate " + m + " " + bs + " " + path.ordinal();
                }
                case 5 -> {
                    q.endShift();
                    ev = "bell";
                }
                case 7 -> {
                    int bed = rng.nextInt(ForgeTemperQuest.BEDS);
                    o = q.waterBed(bed, ForgeTemperQuest.BED_DL);
                    ev = "bed " + bed + " " + ForgeTemperQuest.BED_DL;
                }
                default -> {
                    Life p = ForgeTemperQuest.PENS.get(rng.nextInt(ForgeTemperQuest.PENS.size()));
                    o = q.waterPen(p, p.dlPerDay());
                    ev = "pen " + p.id() + " " + p.dlPerDay();
                }
            }
            out.add("s=" + seed + " e=" + e + " " + ev + " -> " + (kind == 5 ? "-" : o.name()) + " " + q.current()
                    + " " + q.glow());
        }
        out.add("s=" + seed + " | " + q.encode());
        return out;
    }

    @Test
    void javaMatchesTheCppParityFileLineForLine() throws IOException {
        List<String> lines = Files.readAllLines(PARITY);
        assertThat(lines.get(0)).startsWith("# forge_temper_quest_core_test.cpp --write");
        List<String> expected = new ArrayList<>();
        for (int seed = 0; seed < 100; seed++) {
            expected.addAll(play(seed));
        }
        assertThat(lines.subList(1, lines.size())).containsExactlyElementsOf(expected);
        assertThat(expected.stream().filter(l -> l.contains("QUEST_COMPLETE")).count()).isPositive();
    }
}
