// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.companion.KennelArkVoyage.Leg;
import com.daedalus.world.companion.KennelArkVoyage.Trouble;
import com.daedalus.world.companion.KennelArkVoyage.Voyage;
import com.daedalus.world.companion.KennelGrowth.Pup;

import java.util.Collections;
import java.util.List;

import org.junit.jupiter.api.Test;

class KennelArkVoyageTest {
    static final List<Pup> CREW = List.of(new Pup("greymuzzle", 90, 70, 95, 0), new Pup("tank", 30, 25, 85, 0),
        new Pup("pip", 12, 12, 60, 0), new Pup("wick", 14, 13, 55, 0));
    static final KennelArkMuster.Roster FULL = KennelArkMuster.assign(CREW);

    @Test
    void stormsAreSeededAndSixLegs() {
        assertThat(KennelArkVoyage.storms(4L)).hasSize(KennelArkVoyage.LEGS).isEqualTo(KennelArkVoyage.storms(4L));
        boolean differs = false;
        for (long s = 0; s < 20; s++) {
            differs |= !KennelArkVoyage.storms(s).equals(KennelArkVoyage.storms(s + 1));
        }
        assertThat(differs).isTrue();
        assertThat(Trouble.OVERBOARD.role()).isEqualTo("rescue");
        assertThat(Trouble.values()).extracting(Trouble::role).containsExactlyElementsOf(KennelArkMuster.ROLES);
    }

    @Test
    void tollsApplyOnlyWhenATroubleIsNotAnswered() {
        Voyage v = KennelArkVoyage.cross(FULL, KennelArkVoyage.storms(11L), 5L);
        int hull = KennelArkVoyage.START_HULL;
        int water = KennelArkVoyage.START_WATER;
        for (Leg l : v.legs()) {
            KennelArkMuster.Post p = FULL.posts().stream().filter(x -> x.role().equals(l.trouble().role())).findFirst().orElseThrow();
            assertThat(l.hound()).isEqualTo(p.hound());
            assertThat(l.pct()).isEqualTo(p.pct());
            if (!l.answered()) {
                hull = Math.max(0, hull - l.trouble().hullToll());
                water = Math.max(0, water - l.trouble().waterToll());
            }
            assertThat(l.hull()).isEqualTo(hull);
            assertThat(l.water()).isEqualTo(water);
        }
        assertThat(v.hull()).isEqualTo(hull);
        assertThat(v.water()).isEqualTo(water);
        assertThat(v.arrived()).isEqualTo(hull > 0 && water > 0 && v.legs().size() == KennelArkVoyage.LEGS);
        assertThat(v).isEqualTo(KennelArkVoyage.cross(FULL, KennelArkVoyage.storms(11L), 5L));
    }

    @Test
    void emptyPostAlwaysFailsAndDryCasksSinkAShortCrew() {
        KennelArkMuster.Roster noFetch = KennelArkMuster.assign(List.of(new Pup("tank", 30, 25, 85, 0)));
        assertThat(noFetch.posts()).extracting(KennelArkMuster.Post::role).doesNotContain("fetch");
        Voyage v = KennelArkVoyage.cross(noFetch, Collections.nCopies(3, Trouble.DRY_CASKS), 1L);
        assertThat(v.legs()).allMatch(l -> !l.answered() && l.hound() == null && l.pct() == 0);
        assertThat(v.arrived()).isFalse();
        assertThat(v.legs()).hasSize(3);
        assertThat(v.water()).isZero();
        assertThat(v.failReason()).isEqualTo("the casks ran dry");
    }

    @Test
    void hullGivesWayUnderGustsWithNoGuard() {
        KennelArkMuster.Roster none = KennelArkMuster.assign(List.of());
        Voyage v = KennelArkVoyage.cross(none, Collections.nCopies(4, Trouble.BOARDING_GUST), 2L);
        assertThat(v.legs()).hasSize(4);
        assertThat(v.hull()).isZero();
        assertThat(v.failReason()).isEqualTo("the hull gave way");
    }

    @Test
    void chapterNeedsALiftThenACrossing() {
        Voyage grounded = KennelArkVoyage.crossingTheStormBelt(List.of(new Pup("pip", 12, 12, 60, 0)), 3L);
        assertThat(grounded.arrived()).isFalse();
        assertThat(grounded.legs()).isEmpty();
        assertThat(grounded.failReason()).startsWith("the ark never lifted: crew short");
        int arrived = 0;
        for (long s = 0; s < 200; s++) {
            Voyage v = KennelArkVoyage.crossingTheStormBelt(CREW, s);
            assertThat(v).isEqualTo(KennelArkVoyage.crossingTheStormBelt(CREW, s));
            if (v.arrived()) {
                arrived++;
                assertThat(v.legs()).hasSize(KennelArkVoyage.LEGS);
                assertThat(v.failReason()).isNull();
            }
        }
        assertThat(arrived).isBetween(20, 190);
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> KennelArkVoyage.cross(null, List.of(), 1L)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KennelArkVoyage.cross(FULL, Collections.nCopies(7, Trouble.OVERBOARD), 1L))
            .isInstanceOf(IllegalArgumentException.class);
    }
}
