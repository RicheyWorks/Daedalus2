// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Kennel Isle ark kennel logs (contest gap G92, chapter "The Last Kennel Log"). When the planet shattered, the last
 * kennel ark tore its logbook into {@link #FRAGMENTS} pages that now ride drifting plates. A hound can scent a page only
 * when it is grown (G65 {@link KennelGrowth.Stage}, range by stage) and bonded (G37 {@link KennelBond.Tier#LOYAL}+).
 * Each scent takes a day and every plate drifts {@link #DRIFT_PER_DAY} further away, so the keeper must pick the order.
 * Found pages are read in ark-day order. Pure and deterministic.
 */
public final class KennelArkLogs {
    public static final int FRAGMENTS = 6;
    public static final int DRIFT_PER_DAY = 1;
    public static final int QUEST_DAYS = 8;
    public static final List<String> LOG = List.of(
        "Day 1: the plates split at dawn. Forty hounds aboard, all calm but the Corso pups.",
        "Day 2: water rationed. The hounds drink first; they are the ones who find the springs.",
        "Day 3: Pip's mother scented a fresh spring on a plate we could not see.",
        "Day 4: we carve a notch on the kennel post for every day someone shows up.",
        "Day 5: the arks scatter. We tie the logbook pages to the hounds' collars.",
        "Day 6: if you read this, the hounds brought it home. Keep them close.");

    public record Fragment(int arkDay, int distance) {
        public Fragment {
            if (arkDay < 1 || arkDay > FRAGMENTS || distance < 0) {
                throw new IllegalArgumentException("bad fragment");
            }
        }
    }

    public record Hunt(boolean complete, int daysUsed, List<Integer> foundDays, List<String> pages, String failReason) {
        public Hunt {
            foundDays = List.copyOf(foundDays);
            pages = List.copyOf(pages);
        }
    }

    private KennelArkLogs() {
    }

    /** Seeded scatter: one page per ark day, shuffled, at distances 1..9. */
    public static List<Fragment> scatter(long seed) {
        SplittableRandom r = new SplittableRandom(seed);
        List<Integer> days = new ArrayList<>();
        for (int d = 1; d <= FRAGMENTS; d++) {
            days.add(d);
        }
        for (int i = days.size() - 1; i > 0; i--) {
            int j = r.nextInt(i + 1);
            days.set(i, days.set(j, days.get(i)));
        }
        List<Fragment> out = new ArrayList<>();
        for (int d : days) {
            out.add(new Fragment(d, 1 + r.nextInt(9)));
        }
        return out;
    }

    public static int range(KennelGrowth.Stage s) {
        return switch (s) {
            case NEWBORN, PUP -> 0;
            case JUVENILE -> 6;
            case ADULT -> 14;
            case ELDER -> 10;
        };
    }

    public static boolean canScent(KennelGrowth.Pup hound, int distance) {
        return KennelBond.Tier.of(hound.bond()).compareTo(KennelBond.Tier.LOYAL) >= 0
            && distance <= range(hound.stage());
    }

    /** Greedy plan: each day chase the reachable page that is farthest (it escapes first). */
    public static List<Integer> plan(KennelGrowth.Pup hound, List<Fragment> frags) {
        List<Integer> order = new ArrayList<>();
        boolean[] taken = new boolean[frags.size()];
        for (int day = 0; day < frags.size(); day++) {
            int best = -1;
            for (int i = 0; i < frags.size(); i++) {
                int d = frags.get(i).distance() + day * DRIFT_PER_DAY;
                if (!taken[i] && canScent(hound, d) && (best < 0 || d > frags.get(best).distance() + day)) {
                    best = i;
                }
            }
            if (best < 0) {
                break;
            }
            taken[best] = true;
            order.add(best);
        }
        return order;
    }

    /** Runs a hunt in the given order of fragment indices; one scent per day, plates drift after each day. */
    public static Hunt hunt(KennelGrowth.Pup hound, List<Fragment> frags, List<Integer> order) {
        if (KennelBond.Tier.of(hound.bond()).compareTo(KennelBond.Tier.LOYAL) < 0) {
            return new Hunt(false, 0, List.of(), List.of(), "bond too low");
        }
        if (range(hound.stage()) == 0) {
            return new Hunt(false, 0, List.of(), List.of(), "too young");
        }
        List<Integer> found = new ArrayList<>();
        int day = 0;
        for (int idx : order) {
            if (day >= QUEST_DAYS) {
                break;
            }
            Fragment f = frags.get(idx);
            if (!found.contains(f.arkDay()) && canScent(hound, f.distance() + day * DRIFT_PER_DAY)) {
                found.add(f.arkDay());
            }
            day++;
        }
        List<Integer> sorted = new ArrayList<>(found);
        sorted.sort(Comparator.naturalOrder());
        List<String> pages = new ArrayList<>();
        for (int d : sorted) {
            pages.add(LOG.get(d - 1));
        }
        boolean done = sorted.size() == FRAGMENTS;
        return new Hunt(done, day, sorted, pages, done ? null : "pages lost to the drift: " + (FRAGMENTS - sorted.size()));
    }
}