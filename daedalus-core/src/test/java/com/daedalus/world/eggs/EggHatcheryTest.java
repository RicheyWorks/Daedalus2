// SPDX-License-Identifier: MIT

package com.daedalus.world.eggs;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.companion.TonicBook;
import com.daedalus.world.companion.TonicBrewer;
import com.daedalus.world.eggs.EggHatchery.CareAction;
import com.daedalus.world.eggs.EggHatchery.EggState;
import com.daedalus.world.eggs.EggHatchery.Stage;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class EggHatcheryTest {
    private static final CareAction WARM = new CareAction(37.5, false);
    private static final CareAction WARM_TURN = new CareAction(37.5, true);
    private static final CareAction COLD = new CareAction(20.0, false);
    private static EggHatchery h;

    private static Path repo(String... parts) {
        Path p = Path.of("..", parts);
        return Files.exists(p) ? p : Path.of("", parts);
    }

    @BeforeAll
    static void load() throws Exception {
        h = EggHatchery.load(repo("data", "eggs", "egg-hatch-v1.json"));
    }

    @Test
    void manifestHasAllClaudeEggs() {
        assertThat(h.eggs()).hasSize(49).containsKeys("Diamond", "Dragon", "Robin", "Galaxy", "Easter_Painted");
        assertThat(h.eggs().get("Dragon").hatchPool()).containsOnlyKeys("dino");
    }

    @Test
    void stagesAdvanceIntactCrackedHatchingHatched() {
        EggState s = h.start("Robin", 1);
        assertThat(s.stage()).isEqualTo(Stage.INTACT);
        java.util.List<Stage> seen = new java.util.ArrayList<>();
        while (!s.hatched()) {
            s = h.tick(s, WARM);
            if (seen.isEmpty() || seen.get(seen.size() - 1) != s.stage()) {
                seen.add(s.stage());
            }
        }
        assertThat(seen).containsExactly(Stage.INTACT, Stage.CRACKED, Stage.HATCHING, Stage.HATCHED);
        assertThat(s.ticks()).isEqualTo(h.care().hatchAt());
        assertThat(s.hatchling().family()).isEqualTo("bird");
    }

    @Test
    void turningHalvesTheWait() {
        EggState s = h.run(h.start("Wool", 3), Collections.nCopies(100, WARM_TURN));
        assertThat(s.hatched()).isTrue();
        assertThat(s.ticks()).isEqualTo((h.care().hatchAt() + 1) / 2);
        assertThat(s.turns()).isEqualTo(s.ticks());
    }

    @Test
    void coldNeverHatchesAndNeverDropsBelowStageFloor() {
        EggState s = h.run(h.start("Wool", 3), Collections.nCopies(h.care().crackAt(), WARM));
        assertThat(s.stage()).isEqualTo(Stage.CRACKED);
        s = h.run(s, Collections.nCopies(500, COLD));
        assertThat(s.stage()).isEqualTo(Stage.CRACKED);
        assertThat(s.growth()).isEqualTo(h.care().crackAt());
        assertThat(s.hatched()).isFalse();
    }

    @Test
    void chillPenaltyCostsGrowth() {
        EggState s = h.run(h.start("Wool", 3), Collections.nCopies(h.care().crackAt() + 3, WARM));
        int g = s.growth();
        s = h.run(s, Collections.nCopies(h.care().chillPenaltyEvery(), COLD));
        assertThat(s.growth()).isEqualTo(g - 1);
        assertThat(s.chills()).isEqualTo(h.care().chillPenaltyEvery());
    }

    @Test
    void warmBandEdgesAndOverheat() {
        EggHatchery.Care c = h.care();
        assertThat(h.tick(h.start("Wool", 0), new CareAction(c.warmMin(), false)).growth()).isEqualTo(1);
        assertThat(h.tick(h.start("Wool", 0), new CareAction(c.warmMax(), false)).growth()).isEqualTo(1);
        assertThat(h.tick(h.start("Wool", 0), new CareAction(c.warmMax() + 0.1, false)).chills()).isEqualTo(1);
    }

    @Test
    void deterministicPerSeed() {
        for (long seed = 0; seed < 50; seed++) {
            EggState a = h.run(h.start("Rainbow", seed), Collections.nCopies(40, WARM));
            EggState b = h.run(h.start("Rainbow", seed), Collections.nCopies(40, WARM));
            assertThat(a).isEqualTo(b);
        }
    }

    @Test
    void familyRollFollowsWeights() {
        EggHatchery.EggType sea = h.eggs().get("Sea"); // sea 4, fish 3
        Map<String, Integer> n = new HashMap<>();
        for (long s = 0; s < 70_000; s++) {
            n.merge(EggHatchery.rollFamily(sea, s), 1, Integer::sum);
        }
        assertThat(n.keySet()).isEqualTo(Set.of("sea", "fish"));
        assertThat(n.get("sea") / 70_000.0).isBetween(0.55, 0.59);
    }

    @Test
    void everyEggHatchesOnlyFromItsPool() {
        for (EggHatchery.EggType t : h.eggs().values()) {
            for (long s = 0; s < 20; s++) {
                EggState e = h.run(h.start(t.name(), s), Collections.nCopies(40, WARM));
                assertThat(t.hatchPool()).containsKey(e.hatchling().family());
                assertThat(e.hatchling().rarity()).isEqualTo(t.rarity());
            }
        }
    }

    @Test
    void perfectCareRaisesShinyRate() {
        int perfect = 0;
        int rough = 0;
        List<CareAction> roughPlan = new java.util.ArrayList<>(List.of(COLD));
        roughPlan.addAll(Collections.nCopies(40, WARM));
        for (long s = 0; s < 20_000; s++) {
            if (h.run(h.start("Gold", s), Collections.nCopies(40, WARM)).hatchling().shiny()) {
                perfect++;
            }
            EggState r = h.run(h.start("Gold", s), roughPlan);
            assertThat(r.hatchling().perfectCare()).isFalse();
            if (r.hatchling().shiny()) {
                rough++;
            }
        }
        assertThat(rough / 20_000.0).isBetween(0.01, 0.03);
        assertThat(perfect).isGreaterThan(rough);
    }

    @Test
    void hatchlingCoatFeedsKennelTonicBrewer() throws Exception {
        TonicBrewer brewer = new TonicBrewer(TonicBook.load(repo("tools", "islands", "kennel-isle", "tonics.json")));
        assertThat(EggHatchery.coatFor("speckle")).isEqualTo("Spots");
        assertThat(EggHatchery.coatFor("zigzag")).isEqualTo("Stripes");
        assertThat(EggHatchery.coatFor("marble")).isEqualTo("Labyrinth");
        assertThat(EggHatchery.coatFor("facet")).isEqualTo("None");
        EggState s = h.run(h.start("Opal", 9), Collections.nCopies(40, WARM));
        assertThat(s.hatchling().coat()).isEqualTo("Labyrinth");
        assertThat(brewer.brew(List.of("Furfern", "Pawmint", "Barkbalm"), s.hatchling().coat(), "other", 1, false))
            .isPresent();
    }

    @Test
    void hatchedEggIgnoresFurtherCare() {
        EggState s = h.run(h.start("Robin", 2), Collections.nCopies(40, WARM));
        assertThat(h.tick(s, COLD)).isSameAs(s);
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> h.start("NoSuchEgg", 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> EggHatchery.parse("{\"version\":2}")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new EggHatchery.Care(39, 36, 6, 12, 16, 3, 0.02, 2))
            .isInstanceOf(IllegalArgumentException.class);
    }
}
