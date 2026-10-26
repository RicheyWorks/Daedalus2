// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Kennel Isle ark muster (contest gap, chapter "The Muster at Hull Bay"). Before a rebuilt ark lifts off the shattered
 * planet it needs a hound crew: one hound on each post of {@link #ROLES}. A hound fits a post only when its G65 stage
 * allows the command ({@link KennelGrowth#canTrain}) and its G37 bond tier obeys it ({@link KennelBond#obeys}).
 * {@link #assign} finds the roster that fills the most posts, then has the highest summed G61 drill odds
 * ({@link KennelTraining#successPct}); ties keep the earlier hound. At the muster each posted hound drills once with a
 * seeded roll, and the ark launches when at least {@link #LAUNCH_NEED} posts hold. Pure and deterministic.
 */
public final class KennelArkMuster {
    public static final List<String> ROLES = List.of("guard", "rescue", "fetch", "come");
    public static final int LAUNCH_NEED = 3;
    public static final int QUEST_TRIES = 3;
    public static final int MAX_HOUNDS = 8;

    public record Post(String role, String hound, int pct) { }

    public record Roster(List<Post> posts, List<String> unfilled, int totalPct) {
        public Roster {
            posts = List.copyOf(posts);
            unfilled = List.copyOf(unfilled);
        }

        public boolean full() {
            return unfilled.isEmpty();
        }
    }

    public record Muster(boolean launched, int holds, List<Boolean> results) {
        public Muster {
            results = List.copyOf(results);
        }
    }

    public record QuestResult(boolean complete, int triesUsed, Roster roster, List<Integer> holdsPerTry, String failReason) {
        public QuestResult {
            holdsPerTry = List.copyOf(holdsPerTry);
        }
    }

    private KennelArkMuster() { }

    /** True when the hound may take the post: stage allows the command and the bond tier obeys it. */
    public static boolean fits(KennelGrowth.Pup hound, String role) {
        return ROLES.contains(role) && KennelGrowth.canTrain(hound, role) && KennelBond.obeys(hound.bond(), role);
    }

    /** The best roster: most posts filled, then highest summed drill odds; ties keep the earlier hound per post. */
    public static Roster assign(List<KennelGrowth.Pup> hounds) {
        check(hounds);
        int[] best = new int[ROLES.size()];
        int[] cur = new int[ROLES.size()];
        int[] score = {-1, -1};
        search(hounds, 0, cur, new boolean[hounds.size()], 0, 0, best, score);
        List<Post> posts = new ArrayList<>();
        List<String> unfilled = new ArrayList<>();
        int total = 0;
        for (int i = 0; i < ROLES.size(); i++) {
            String role = ROLES.get(i);
            if (best[i] < 0) {
                unfilled.add(role);
                continue;
            }
            KennelGrowth.Pup h = hounds.get(best[i]);
            int pct = KennelTraining.successPct(h.bond(), role);
            posts.add(new Post(role, h.name(), pct));
            total += pct;
        }
        return new Roster(posts, unfilled, total);
    }

    private static void search(List<KennelGrowth.Pup> hounds, int role, int[] cur, boolean[] used, int filled, int pct,
                               int[] best, int[] score) {
        if (role == ROLES.size()) {
            if (filled > score[0] || (filled == score[0] && pct > score[1])) {
                score[0] = filled;
                score[1] = pct;
                System.arraycopy(cur, 0, best, 0, cur.length);
            }
            return;
        }
        String r = ROLES.get(role);
        for (int i = 0; i < hounds.size(); i++) {
            if (used[i] || !fits(hounds.get(i), r)) {
                continue;
            }
            used[i] = true;
            cur[role] = i;
            search(hounds, role + 1, cur, used, filled + 1, pct + KennelTraining.successPct(hounds.get(i).bond(), r), best, score);
            used[i] = false;
        }
        cur[role] = -1;
        search(hounds, role + 1, cur, used, filled, pct, best, score);
    }

    /** One muster: every posted hound drills its post once (roll below its odds holds the post). */
    public static Muster muster(Roster roster, long seed) {
        SplittableRandom rnd = new SplittableRandom(seed);
        List<Boolean> results = new ArrayList<>();
        int holds = 0;
        for (Post p : roster.posts()) {
            boolean ok = rnd.nextInt(100) < p.pct();
            results.add(ok);
            holds += ok ? 1 : 0;
        }
        return new Muster(holds >= LAUNCH_NEED, holds, results);
    }

    /** The chapter: muster the best roster up to {@link #QUEST_TRIES} times (one per dawn); complete on the first launch. */
    public static QuestResult musterAtHullBay(List<KennelGrowth.Pup> hounds, long seed) {
        Roster roster = assign(hounds);
        if (roster.posts().size() < LAUNCH_NEED) {
            return new QuestResult(false, 0, roster, List.of(), "crew short: " + String.join(",", roster.unfilled()));
        }
        SplittableRandom days = new SplittableRandom(seed);
        List<Integer> holds = new ArrayList<>();
        for (int t = 1; t <= QUEST_TRIES; t++) {
            Muster m = muster(roster, days.nextLong());
            holds.add(m.holds());
            if (m.launched()) {
                return new QuestResult(true, t, roster, holds, null);
            }
        }
        return new QuestResult(false, QUEST_TRIES, roster, holds, "the ark missed its window");
    }

    private static void check(List<KennelGrowth.Pup> hounds) {
        if (hounds == null || hounds.size() > MAX_HOUNDS) {
            throw new IllegalArgumentException("muster takes 0.." + MAX_HOUNDS + " hounds");
        }
        Set<String> names = new HashSet<>();
        for (KennelGrowth.Pup h : hounds) {
            if (h == null || !names.add(h.name())) {
                throw new IllegalArgumentException("hounds must be distinct and named");
            }
        }
    }
}
