// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.companion.KennelArkMuster.Muster;
import com.daedalus.world.companion.KennelArkMuster.Post;
import com.daedalus.world.companion.KennelArkMuster.QuestResult;
import com.daedalus.world.companion.KennelArkMuster.Roster;
import com.daedalus.world.companion.KennelGrowth.Pup;

import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.Test;

class KennelArkMusterTest {
    static final Pup ELDER = new Pup("greymuzzle", 90, 70, 95, 0);
    static final Pup ADULT = new Pup("tank", 30, 25, 85, 0);
    static final Pup JUV_A = new Pup("pip", 12, 12, 60, 0);
    static final Pup JUV_B = new Pup("wick", 14, 13, 55, 0);
    static final Pup PUP = new Pup("button", 5, 5, 30, 0);
    static final Pup NEWBORN = new Pup("bean", 1, 1, 100, 0);

    @Test
    void fitsNeedsStageAndTier() {
        assertThat(KennelArkMuster.fits(ADULT, "rescue")).isTrue();
        assertThat(KennelArkMuster.fits(ELDER, "rescue")).isFalse();
        assertThat(KennelArkMuster.fits(ELDER, "guard")).isTrue();
        assertThat(KennelArkMuster.fits(JUV_A, "guard")).isFalse();
        assertThat(KennelArkMuster.fits(JUV_A, "fetch")).isTrue();
        assertThat(KennelArkMuster.fits(PUP, "come")).isTrue();
        assertThat(KennelArkMuster.fits(PUP, "fetch")).isFalse();
        assertThat(KennelArkMuster.fits(NEWBORN, "come")).isFalse();
        assertThat(KennelArkMuster.fits(new Pup("shy", 30, 30, 20, 0), "come")).isFalse();
        assertThat(KennelArkMuster.fits(ADULT, "sit")).isFalse();
    }

    @Test
    void elderGuardsAndAdultRescues() {
        Roster r = KennelArkMuster.assign(List.of(ELDER, ADULT, JUV_A, JUV_B));
        assertThat(r.full()).isTrue();
        assertThat(r.posts()).extracting(Post::role).containsExactly("guard", "rescue", "fetch", "come");
        assertThat(r.posts()).extracting(Post::hound).containsExactly("greymuzzle", "tank", "pip", "wick");
        assertThat(r.totalPct()).isEqualTo(r.posts().stream().mapToInt(Post::pct).sum());
        for (Post p : r.posts()) {
            assertThat(p.pct()).isEqualTo(KennelTraining.successPct(bondOf(p.hound()), p.role()));
        }
    }

    @Test
    void assignmentIsOptimalAgainstBruteForce() {
        List<Pup> hounds = List.of(PUP, JUV_B, ADULT, new Pup("rook", 40, 40, 80, 0), JUV_A, ELDER);
        Roster r = KennelArkMuster.assign(hounds);
        int[] best = {-1, -1};
        brute(hounds, 0, new boolean[hounds.size()], 0, 0, best);
        assertThat(r.posts().size()).isEqualTo(best[0]);
        assertThat(r.totalPct()).isEqualTo(best[1]);
        assertThat(r.posts().stream().map(Post::hound).distinct().count()).isEqualTo(r.posts().size());
    }

    @Test
    void shortCrewListsUnfilledPostsAndFailsTheChapter() {
        Roster r = KennelArkMuster.assign(List.of(PUP, NEWBORN, JUV_A));
        assertThat(r.unfilled()).containsExactly("guard", "rescue");
        assertThat(r.posts()).extracting(Post::hound).containsExactly("pip", "button");
        QuestResult q = KennelArkMuster.musterAtHullBay(List.of(PUP, NEWBORN, JUV_A), 9L);
        assertThat(q.complete()).isFalse();
        assertThat(q.triesUsed()).isZero();
        assertThat(q.failReason()).isEqualTo("crew short: guard,rescue");
        assertThat(KennelArkMuster.assign(List.of()).unfilled()).hasSize(4);
    }

    @Test
    void musterIsSeededAndLaunchNeedsThreeHolds() {
        Roster r = KennelArkMuster.assign(List.of(ELDER, ADULT, JUV_A, JUV_B));
        int launched = 0;
        for (long s = 0; s < 400; s++) {
            Muster m = KennelArkMuster.muster(r, s);
            assertThat(m).isEqualTo(KennelArkMuster.muster(r, s));
            assertThat(m.results()).hasSize(4);
            assertThat(m.holds()).isEqualTo((int) m.results().stream().filter(b -> b).count());
            assertThat(m.launched()).isEqualTo(m.holds() >= KennelArkMuster.LAUNCH_NEED);
            launched += m.launched() ? 1 : 0;
        }
        assertThat(launched).isBetween(60, 340);
    }

    @Test
    void chapterStopsOnFirstLaunchWithinThreeDawns() {
        List<Pup> crew = List.of(ELDER, ADULT, JUV_A, JUV_B);
        int complete = 0;
        for (long s = 0; s < 200; s++) {
            QuestResult q = KennelArkMuster.musterAtHullBay(crew, s);
            assertThat(q).isEqualTo(KennelArkMuster.musterAtHullBay(crew, s));
            assertThat(q.holdsPerTry()).hasSize(q.triesUsed());
            assertThat(q.triesUsed()).isBetween(1, KennelArkMuster.QUEST_TRIES);
            for (int t = 0; t < q.triesUsed() - 1; t++) {
                assertThat(q.holdsPerTry().get(t)).isLessThan(KennelArkMuster.LAUNCH_NEED);
            }
            if (q.complete()) {
                complete++;
                assertThat(q.holdsPerTry().get(q.triesUsed() - 1)).isGreaterThanOrEqualTo(KennelArkMuster.LAUNCH_NEED);
                assertThat(q.failReason()).isNull();
            } else {
                assertThat(q.triesUsed()).isEqualTo(KennelArkMuster.QUEST_TRIES);
                assertThat(q.failReason()).isEqualTo("the ark missed its window");
            }
        }
        assertThat(complete).isBetween(100, 200);
    }

    @Test
    void rejectsDuplicatesAndOversizedCrews() {
        assertThatThrownBy(() -> KennelArkMuster.assign(List.of(ADULT, ADULT))).isInstanceOf(IllegalArgumentException.class);
        List<Pup> many = new ArrayList<>();
        for (int i = 0; i < 9; i++) {
            many.add(new Pup("h" + i, 30, 30, 90, 0));
        }
        assertThatThrownBy(() -> KennelArkMuster.assign(many)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KennelArkMuster.assign(null)).isInstanceOf(IllegalArgumentException.class);
    }

    private static int bondOf(String name) {
        return List.of(ELDER, ADULT, JUV_A, JUV_B, PUP, NEWBORN).stream().filter(p -> p.name().equals(name))
            .findFirst().orElseThrow().bond();
    }

    private static void brute(List<Pup> h, int role, boolean[] used, int filled, int pct, int[] best) {
        if (role == KennelArkMuster.ROLES.size()) {
            if (filled > best[0] || (filled == best[0] && pct > best[1])) {
                best[0] = filled;
                best[1] = pct;
            }
            return;
        }
        String r = KennelArkMuster.ROLES.get(role);
        brute(h, role + 1, used, filled, pct, best);
        for (int i = 0; i < h.size(); i++) {
            if (!used[i] && KennelArkMuster.fits(h.get(i), r)) {
                used[i] = true;
                brute(h, role + 1, used, filled + 1, pct + KennelTraining.successPct(h.get(i).bond(), r), best);
                used[i] = false;
            }
        }
    }
}
