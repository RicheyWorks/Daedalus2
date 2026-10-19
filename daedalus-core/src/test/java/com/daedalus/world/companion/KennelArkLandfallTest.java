// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.companion.KennelArkLandfall.Chapter;
import com.daedalus.world.companion.KennelArkLandfall.Day;
import com.daedalus.world.companion.KennelArkLandfall.Landfall;
import com.daedalus.world.companion.KennelGrowth.Pup;

import java.util.HashSet;
import java.util.List;

import org.junit.jupiter.api.Test;

class KennelArkLandfallTest {
    static final List<Pup> CREW = KennelArkVoyageTest.CREW;
    static final KennelArkMuster.Roster FULL = KennelArkVoyageTest.FULL;
    static final KennelArkMuster.Roster NONE = KennelArkMuster.assign(List.of());

    @Test
    void strandedAnimalsAreSeededAndDistinct() {
        List<String> s = KennelArkLandfall.stranded(9L);
        assertThat(s).hasSize(KennelArkLandfall.STRANDED_COUNT).doesNotHaveDuplicates().isEqualTo(KennelArkLandfall.stranded(9L));
        assertThat(KennelArkLandfall.STRANDED).containsAll(s);
        boolean differs = false;
        for (long k = 0; k < 20; k++) {
            differs |= !KennelArkLandfall.stranded(k).equals(KennelArkLandfall.stranded(k + 1));
        }
        assertThat(differs).isTrue();
    }

    @Test
    void planksMendTheHullAndWaterDrainsDaily() {
        for (long seed = 0; seed < 50; seed++) {
            Landfall l = KennelArkLandfall.repair(FULL, 2, 6, KennelArkLandfall.stranded(seed), seed);
            int hull = 2;
            int water = 6;
            int saved = 0;
            for (Day d : l.days()) {
                int planks = (d.fetched() ? KennelArkLandfall.FETCH_PLANKS : 0) + (d.hauled() ? KennelArkLandfall.HAUL_PLANKS : 0);
                assertThat(d.planks()).isEqualTo(planks);
                hull = Math.min(KennelArkLandfall.HULL_FULL, hull + planks);
                water--;
                assertThat(d.hull()).isEqualTo(hull);
                assertThat(d.water()).isEqualTo(water);
                if (d.rescued() != null) {
                    assertThat(d.rescued()).isEqualTo(l.rescued().get(saved++));
                }
            }
            assertThat(saved).isEqualTo(l.rescued().size());
            assertThat(l.days().size()).isLessThanOrEqualTo(KennelArkLandfall.DAYS);
            assertThat(l.seaworthy()).isEqualTo(hull == KennelArkLandfall.HULL_FULL && water > 0);
            assertThat(l).isEqualTo(KennelArkLandfall.repair(FULL, 2, 6, KennelArkLandfall.stranded(seed), seed));
        }
    }

    @Test
    void noCrewMeansNoPlanksAndTheCasksRunDry() {
        Landfall l = KennelArkLandfall.repair(NONE, 4, 3, KennelArkLandfall.stranded(1L), 1L);
        assertThat(l.days()).hasSize(3).allMatch(d -> !d.fetched() && !d.hauled() && d.rescued() == null && d.planks() == 0);
        assertThat(l.seaworthy()).isFalse();
        assertThat(l.hull()).isEqualTo(4);
        assertThat(l.water()).isZero();
        assertThat(l.rescued()).isEmpty();
        assertThat(l.failReason()).isEqualTo("the casks ran dry on the shelf");
    }

    @Test
    void hullNotMendedInTimeWithWaterLeft() {
        Landfall l = KennelArkLandfall.repair(NONE, 1, 10, List.of(), 2L);
        assertThat(l.days()).hasSize(KennelArkLandfall.DAYS);
        assertThat(l.water()).isEqualTo(10 - KennelArkLandfall.DAYS);
        assertThat(l.failReason()).isEqualTo("the hull was not mended in time");
    }

    @Test
    void aFullHullIsSeaworthyAtOnce() {
        Landfall l = KennelArkLandfall.repair(NONE, KennelArkLandfall.HULL_FULL, 1, List.of("ark cat"), 3L);
        assertThat(l.seaworthy()).isTrue();
        assertThat(l.days()).isEmpty();
        assertThat(l.failReason()).isNull();
    }

    @Test
    void chapterReplaysTheStormBeltThenLands() {
        Chapter grounded = KennelArkLandfall.landfallOnTheCinderShelf(List.of(new Pup("pip", 12, 12, 60, 0)), 3L);
        assertThat(grounded.complete()).isFalse();
        assertThat(grounded.landfall()).isNull();
        assertThat(grounded.failReason()).startsWith("the ark never lifted: crew short");
        int complete = 0;
        int lost = 0;
        HashSet<String> animals = new HashSet<>();
        for (long s = 0; s < 200; s++) {
            Chapter c = KennelArkLandfall.landfallOnTheCinderShelf(CREW, s);
            assertThat(c).isEqualTo(KennelArkLandfall.landfallOnTheCinderShelf(CREW, s));
            assertThat(c.voyage()).isEqualTo(KennelArkVoyage.crossingTheStormBelt(CREW, s));
            if (!c.voyage().arrived()) {
                assertThat(c.landfall()).isNull();
                assertThat(c.failReason()).startsWith(c.voyage().legs().isEmpty() ? "the ark never lifted: " : "the ark never made landfall: ");
                lost++;
                continue;
            }
            assertThat(c.landfall()).isNotNull();
            if (c.complete()) {
                complete++;
                assertThat(c.failReason()).isNull();
                animals.addAll(c.landfall().rescued());
            }
        }
        assertThat(complete).isPositive();
        assertThat(lost).isPositive();
        assertThat(animals).isNotEmpty();
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> KennelArkLandfall.repair(null, 5, 5, List.of(), 1L)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KennelArkLandfall.repair(FULL, 0, 5, List.of(), 1L)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KennelArkLandfall.repair(FULL, 5, 0, List.of(), 1L)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KennelArkLandfall.repair(FULL, 11, 5, List.of(), 1L)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KennelArkLandfall.repair(FULL, 5, 5, null, 1L)).isInstanceOf(IllegalArgumentException.class);
    }
}