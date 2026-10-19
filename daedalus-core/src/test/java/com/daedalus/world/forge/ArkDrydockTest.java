// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ArkDrydock.Ark;
import com.daedalus.world.forge.ArkDrydock.ArkClass;
import com.daedalus.world.forge.ArkDrydock.Inspection;
import com.daedalus.world.forge.ArkDrydock.Life;
import com.daedalus.world.forge.ArkDrydock.Plate;
import com.daedalus.world.forge.ArkDrydock.Reason;
import com.daedalus.world.forge.ArkDrydock.Voyage;
import com.daedalus.world.forge.ForgeGrades.Material;
import com.daedalus.world.forge.TemperForge.Blank;
import com.daedalus.world.forge.TemperForge.Quench;
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
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Ark Drydock (G24): a well-forged, fully riveted, temper-both hull with a paired, watered manifest
 * launches; every blocker is caught and named, the Drydock Master has a line for each, and the hold's
 * water numbers match the island's livestock data.
 */
class ArkDrydockTest {

    private static final Path LIVESTOCK = Path.of("..", "data", "islands", "hephaestus", "livestock.json");
    private static final Voyage FIVE_DAYS = new Voyage("Kennel Isle", 5);

    private static List<Plate> plates(int n, Quench q, int temper) {
        return new ArrayList<>(Collections.nCopies(n, new Plate(temper, q, true)));
    }

    private static List<Integer> rivets(int n) {
        return new ArrayList<>(Collections.nCopies(n, ArkDrydock.RIVETS_PER_SEAM));
    }

    private static Map<Life, Integer> manifest() {
        Map<Life, Integer> m = new EnumMap<>(Life.class);
        m.put(Life.EMBERHEN, 2);
        m.put(Life.ASHGOAT, 2);
        m.put(Life.VENT_BEES, 1);
        m.put(Life.PET, 1);
        m.put(Life.SEED_CRATE, 2);
        return m;
    }

    private static Ark ark(List<Plate> plates, List<Integer> rivets, Map<Life, Integer> manifest, int water) {
        return new Ark(ArkClass.SKIFF, plates, rivets, manifest, water);
    }

    private static Ark good() {
        List<Plate> p = plates(6, Quench.MAGMA, 90);
        p.set(3, new Plate(90, Quench.SPRING, true));
        Ark draft = ark(p, rivets(6), manifest(), 0);
        return ark(p, rivets(6), manifest(), ArkDrydock.waterNeedDl(draft, FIVE_DAYS));
    }

    @Test
    void waterFiguresMatchTheIslandLivestockData() throws IOException {
        String json = Files.readString(LIVESTOCK);
        Matcher m = Pattern.compile("\"id\":\\s*\"([a-z_]+)\"[^{}]*?\"drinks\":\\s*\"([0-9.]+) L/day").matcher(json);
        Set<String> seen = new HashSet<>();
        while (m.find()) {
            String id = m.group(1);
            int dl = (int) Math.round(Double.parseDouble(m.group(2)) * 10);
            Life life = null;
            for (Life l : Life.values()) {
                if (l.id().equals(id)) {
                    life = l;
                }
            }
            assertThat(life).as("livestock.json id %s has a Life", id).isNotNull();
            assertThat(life.dlPerDay()).as(id).isEqualTo(dl);
            seen.add(id);
        }
        assertThat(seen).containsExactlyInAnyOrder("emberhen", "ashgoat", "forgeox", "lavaboar", "cinderwool",
                "vent_bees");
    }

    @Test
    void aGoodArkLaunchesWithTheSendOff() {
        Inspection i = ArkDrydock.inspect(good(), FIVE_DAYS);
        assertThat(i.ready()).isTrue();
        assertThat(i.reasons()).isEmpty();
        assertThat(i.integrity()).isEqualTo(90);
        assertThat(i.berthsUsed()).isEqualTo(8);
        // crew 2 x 20 + hens 2 x 5 + goats 2 x 80 + bees 10 + pet 10 = 230 dL a day, 5 days
        assertThat(i.waterNeedDl()).isEqualTo(1150);
        assertThat(i.line()).contains("5 days to Kennel Isle");
        assertThat(ArkDrydock.questStep(i)).isEqualTo("launch");
    }

    @Test
    void temperBothOrTheHullFails() {
        Ark g = good();
        Inspection allMagma = ArkDrydock.inspect(ark(plates(6, Quench.MAGMA, 90), rivets(6), manifest(), g.waterDl()),
                FIVE_DAYS);
        assertThat(allMagma.reasons()).containsExactly(Reason.BRITTLE);
        assertThat(allMagma.line()).contains("Heat alone breaks");
        Inspection allSpring = ArkDrydock.inspect(ark(plates(6, Quench.SPRING, 90), rivets(6), manifest(), g.waterDl()),
                FIVE_DAYS);
        assertThat(allSpring.reasons()).containsExactly(Reason.SOFT);
        assertThat(allSpring.line()).contains("Water alone softens");
        Inspection allDual = ArkDrydock.inspect(ark(plates(6, Quench.DUAL, 90), rivets(6), manifest(), g.waterDl()),
                FIVE_DAYS);
        assertThat(allDual.ready()).isTrue();
    }

    @Test
    void seamsAreTheMeanTemperLessMissingRivets() {
        Ark g = good();
        List<Plate> p = new ArrayList<>(g.plates());
        p.set(1, new Plate(40, Quench.MAGMA, true));
        List<Integer> r = rivets(6);
        r.set(4, 1);
        Ark a = ark(p, r, manifest(), g.waterDl());
        assertThat(ArkDrydock.seamStrength(a, 0)).isEqualTo(65);            // (90 + 40) / 2
        assertThat(ArkDrydock.seamStrength(a, 1)).isEqualTo(65);
        assertThat(ArkDrydock.seamStrength(a, 4)).isEqualTo(90 - 3 * ArkDrydock.MISSING_RIVET_COST);
        assertThat(ArkDrydock.seamStrength(a, 5)).isEqualTo(90);            // the ring closes 5 -> 0
        assertThat(ArkDrydock.inspect(a, FIVE_DAYS).integrity()).isEqualTo(60);
        assertThat(ArkDrydock.inspect(a, FIVE_DAYS).ready()).isTrue();
        r.set(4, 0);
        Inspection weak = ArkDrydock.inspect(ark(p, r, manifest(), g.waterDl()), FIVE_DAYS);
        assertThat(weak.reasons()).containsExactly(Reason.WEAK_SEAM);
        assertThat(ArkDrydock.questStep(weak)).isEqualTo("rivet_seams");
    }

    @Test
    void theHullMustBeWholeAndStamped() {
        Ark g = good();
        Inspection gap = ArkDrydock.inspect(ark(g.plates().subList(0, 5), rivets(5), manifest(), g.waterDl()),
                FIVE_DAYS);
        assertThat(gap.reasons()).contains(Reason.HULL_INCOMPLETE);
        assertThat(ArkDrydock.questStep(gap)).isEqualTo("forge_plates");
        List<Plate> p = new ArrayList<>(g.plates());
        p.set(2, new Plate(95, Quench.MAGMA, false));
        assertThat(ArkDrydock.inspect(ark(p, rivets(6), manifest(), g.waterDl()), FIVE_DAYS).reasons())
                .containsExactly(Reason.UNSTAMPED_PLATE);
        assertThat(ArkDrydock.inspect(ark(List.of(), List.of(), manifest(), g.waterDl()), FIVE_DAYS).reasons())
                .contains(Reason.HULL_INCOMPLETE, Reason.WEAK_SEAM);
    }

    @Test
    void lifeTravelsInPairsWithinTheBerths() {
        Ark g = good();
        Map<Life, Integer> odd = manifest();
        odd.put(Life.FORGEOX, 1);
        Ark a = ark(g.plates(), g.rivets(), odd, ArkClass.SKIFF.holdDl());
        Inspection i = ArkDrydock.inspect(a, FIVE_DAYS);
        assertThat(i.reasons()).containsExactly(Reason.UNPAIRED);
        assertThat(ArkDrydock.questStep(i)).isEqualTo("load_life");
        Map<Life, Integer> crowded = manifest();
        crowded.put(Life.SEED_CRATE, 10);
        assertThat(ArkDrydock.inspect(ark(g.plates(), g.rivets(), crowded, g.waterDl()), FIVE_DAYS).reasons())
                .containsExactly(Reason.OVER_CAPACITY);
    }

    @Test
    void theHoldMustCarryEnoughWaterButNoMoreThanItHolds() {
        Ark g = good();
        Inspection thirsty = ArkDrydock.inspect(ark(g.plates(), g.rivets(), manifest(), g.waterDl() - 1), FIVE_DAYS);
        assertThat(thirsty.reasons()).containsExactly(Reason.THIRSTY_HOLD);
        assertThat(ArkDrydock.questStep(thirsty)).isEqualTo("water_hold");
        assertThat(ArkDrydock.inspect(ark(g.plates(), g.rivets(), manifest(), ArkClass.SKIFF.holdDl() + 1), FIVE_DAYS)
                .reasons()).containsExactly(Reason.OVER_HOLD);
        Map<Life, Integer> oxen = manifest();
        oxen.put(Life.FORGEOX, 2);
        Ark heavy = ark(g.plates(), g.rivets(), oxen, ArkClass.SKIFF.holdDl());
        assertThat(ArkDrydock.inspect(heavy, new Voyage("Glass Reef", 9)).reasons()).containsExactly(Reason.THIRSTY_HOLD);
    }

    @Test
    void everyReasonHasItsOwnLineAndQuestStep() {
        Set<String> lines = new HashSet<>();
        for (Reason r : Reason.values()) {
            assertThat(ArkDrydock.line(r)).isNotBlank();
            assertThat(lines.add(ArkDrydock.line(r))).isTrue();
            Inspection i = new Inspection(false, List.of(r), 0, 0, 0, ArkDrydock.line(r));
            assertThat(ArkDrydock.questStep(i)).isIn("forge_plates", "rivet_seams", "load_life", "water_hold");
        }
    }

    @Test
    void voyagesAreSeededToOtherShards() {
        assertThat(ArkDrydock.voyage(8)).isEqualTo(ArkDrydock.voyage(8));
        Set<String> shards = new HashSet<>();
        for (long seed = 0; seed < 200; seed++) {
            Voyage v = ArkDrydock.voyage(seed);
            assertThat(v.days()).isBetween(3, 9);
            assertThat(v.shard()).isNotEqualTo("Hephaestus Island");
            shards.add(v.shard());
        }
        assertThat(shards).hasSize(ArkDrydock.SHARDS.size());
    }

    @Test
    void platesForgedAtTheAnvilBuildALaunchableLongark() {
        List<Plate> p = new ArrayList<>();
        for (int i = 0; i < ArkClass.LONGARK.plates(); i++) {
            Blank b = TemperForge.blank(Material.STARMETAL, i);
            Quench q = i % 2 == 0 ? Quench.MAGMA : Quench.SPRING;
            p.add(Plate.of(TemperForge.judge(b, TemperForge.idealRun(b, q))));
        }
        Map<Life, Integer> life = manifest();
        life.put(Life.FORGEOX, 2);
        life.put(Life.CINDERWOOL, 2);
        Voyage v = ArkDrydock.voyage(3);
        Ark draft = new Ark(ArkClass.LONGARK, p, rivets(p.size()), life, 0);
        Ark a = new Ark(ArkClass.LONGARK, p, rivets(p.size()), life, ArkDrydock.waterNeedDl(draft, v));
        Inspection i = ArkDrydock.inspect(a, v);
        assertThat(i.ready()).as("%s", i.reasons()).isTrue();
        assertThat(i.integrity()).isGreaterThanOrEqualTo(98);
        Blank b = TemperForge.blank(Material.IRON, 1);
        List<Integer> cold = new ArrayList<>(TemperForge.idealRun(b, Quench.DUAL).strikesMs());
        cold.set(0, cold.get(0) + 60_000);
        for (int k = 1; k < cold.size(); k++) {
            cold.set(k, cold.get(0) + k);
        }
        Plate cracked = Plate.of(TemperForge.judge(b, new TemperForge.Run(b.idealPullMs(), cold, cold.get(0) + 100_000,
                Quench.DUAL)));
        assertThat(cracked.stamped()).isFalse();
    }
}
