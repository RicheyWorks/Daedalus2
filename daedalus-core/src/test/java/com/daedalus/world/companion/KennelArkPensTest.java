// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.companion.KennelArkPens.Pen;
import com.daedalus.world.companion.KennelArkPens.Plan;
import com.daedalus.world.companion.KennelArkPens.WarmCrates;

import java.util.List;

import org.junit.jupiter.api.Test;

class KennelArkPensTest {
    static final List<KennelGrowth.Pup> CREW = KennelArkVoyageTest.CREW;

    @Test
    void everyStrandedAnimalHasAPen() {
        assertThat(KennelArkPens.NEEDS.keySet()).containsExactlyInAnyOrderElementsOf(KennelArkLandfall.STRANDED);
        assertThat(KennelArkPens.need("reef otter")).isEqualTo(Pen.POOL);
        assertThat(Pen.WARM_CRATE.room()).isEqualTo(2);
        assertThatThrownBy(() -> KennelArkPens.need("dragon")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void cheapestFirstAndCratesAreShared() {
        Plan p = KennelArkPens.plan(List.of("reef otter", "ember fox", "ark cat", "cinder hare"), 3);
        assertThat(p.penned()).containsExactly("ember fox", "ark cat", "cinder hare");
        assertThat(p.built()).containsExactly(Pen.WARM_CRATE, Pen.BURROW);
        assertThat(p.unpenned()).containsExactly("reef otter");
        assertThat(p.planksUsed()).isEqualTo(2);
        assertThat(p.planksLeft()).isEqualTo(1);
        assertThat(p.allPenned()).isFalse();
        Plan all = KennelArkPens.plan(List.of("sky-crane", "salt goat", "reef otter"), 9);
        assertThat(all.allPenned()).isTrue();
        assertThat(all.penned()).containsExactly("sky-crane", "salt goat", "reef otter");
        assertThat(all.planksLeft()).isZero();
        assertThat(KennelArkPens.plan(List.of(), 0).allPenned()).isTrue();
    }

    @Test
    void spareIsPlanksBeyondTheMend() {
        KennelArkLandfall.Landfall l = KennelArkLandfall.repairRolls(KennelArkVoyageTest.FULL, 7, 6, List.of(), new int[15]);
        assertThat(l.hull()).isEqualTo(KennelArkLandfall.HULL_FULL);
        int planks = l.days().stream().mapToInt(KennelArkLandfall.Day::planks).sum();
        assertThat(KennelArkPens.spare(7, l)).isEqualTo(planks - 3).isNotNegative();
        assertThatThrownBy(() -> KennelArkPens.spare(11, l)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void chapterPensWhatTheArkBroughtHome() {
        int complete = 0;
        int neverHome = 0;
        for (long s = 0; s < 200; s++) {
            WarmCrates w = KennelArkPens.theWarmCrates(CREW, s);
            assertThat(w).isEqualTo(KennelArkPens.theWarmCrates(CREW, s));
            assertThat(w.landing()).isEqualTo(KennelArkLandfall.landfallOnTheCinderShelf(CREW, s));
            if (!w.landing().complete()) {
                neverHome++;
                assertThat(w.plan()).isNull();
                assertThat(w.failReason()).startsWith("the ark never came home: ");
                continue;
            }
            KennelArkLandfall.Landfall l = w.landing().landfall();
            int budget = KennelArkPens.STORES + KennelArkPens.spare(w.landing().voyage().hull(), l);
            assertThat(w.plan().planksUsed() + w.plan().planksLeft()).isEqualTo(budget);
            assertThat(w.plan().penned().size() + w.plan().unpenned().size()).isEqualTo(l.rescued().size());
            assertThat(w.complete()).isEqualTo(!l.rescued().isEmpty() && w.plan().allPenned());
            if (w.complete()) {
                complete++;
                assertThat(w.failReason()).isNull();
            } else {
                assertThat(w.failReason()).isIn("no animals came aboard", "not every animal has a pen");
            }
        }
        assertThat(complete).isPositive();
        assertThat(neverHome).isPositive();
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> KennelArkPens.plan(null, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KennelArkPens.plan(List.of(), -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KennelArkPens.plan(List.of("ghost"), 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KennelArkPens.spare(3, null)).isInstanceOf(IllegalArgumentException.class);
    }
}
