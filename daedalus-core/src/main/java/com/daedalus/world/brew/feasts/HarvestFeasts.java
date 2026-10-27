// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.feasts;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;
import java.util.TreeSet;

/**
 * Chapter 32 of the Youtube Master Island story, "The Harvest Feasts" (quest {@code q_harvest_feasts}). Families ask
 * for the village hall over an hour span {@code [start, end)} and each feast brings some cheer. The hall holds one
 * feast at a time (a feast may start the hour another ends). {@link #most()} is exact weighted interval scheduling:
 * sort by end, binary-search the last compatible feast, DP. Booking that much cheer earns credit; overlapping feasts
 * or less cheer do not.
 */
public final class HarvestFeasts {
    public static final String QUEST_ID = "q_harvest_feasts";

    public enum Outcome { BOOKED, STRUCK, NOT_THERE, WELL, DIM, OVERLAP, DUPLICATE, IGNORED }

    private final int[] start;
    private final int[] end;
    private final int[] cheer;
    private final int most;
    private final Set<Integer> booked = new TreeSet<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("book", "feast", 1),
            new QuestProgress.Step("open", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private Outcome last;
    private int[] overlap;

    public HarvestFeasts(int[] start, int[] end, int[] cheer) {
        if (start == null || end == null || cheer == null || start.length == 0 || start.length != end.length
                || start.length != cheer.length) {
            throw new IllegalArgumentException("one start, end and cheer per feast");
        }
        for (int i = 0; i < start.length; i++) {
            if (start[i] < 0 || end[i] <= start[i] || cheer[i] < 0) {
                throw new IllegalArgumentException("feasts run forward and bring non-negative cheer");
            }
        }
        this.start = start.clone();
        this.end = end.clone();
        this.cheer = cheer.clone();
        most = schedule();
    }

    /** A seeded book of 3-12 feasts within a 24-hour day, 1-6 hours long, 1-9 cheer. */
    public static HarvestFeasts seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xFEA57L);
        int n = 3 + rng.nextInt(10);
        int[] s = new int[n];
        int[] e = new int[n];
        int[] c = new int[n];
        for (int i = 0; i < n; i++) {
            s[i] = rng.nextInt(20);
            e[i] = s[i] + 1 + rng.nextInt(6);
            c[i] = 1 + rng.nextInt(9);
        }
        return new HarvestFeasts(s, e, c);
    }

    private int schedule() {
        int n = start.length;
        Integer[] order = new Integer[n];
        for (int i = 0; i < n; i++) {
            order[i] = i;
        }
        Arrays.sort(order, (a, b) -> Integer.compare(end[a], end[b]));
        int[] ends = new int[n];
        for (int i = 0; i < n; i++) {
            ends[i] = end[order[i]];
        }
        int[] dp = new int[n + 1];
        for (int i = 1; i <= n; i++) {
            int f = order[i - 1];
            int lo = 0;
            int hi = i - 1;
            while (lo < hi) {
                int mid = (lo + hi + 1) >>> 1;
                if (ends[mid - 1] <= start[f]) {
                    lo = mid;
                } else {
                    hi = mid - 1;
                }
            }
            dp[i] = Math.max(dp[i - 1], dp[lo] + cheer[f]);
        }
        return dp[n];
    }

    static boolean clash(int as, int ae, int bs, int be) {
        return as < be && bs < ae;
    }

    public int feasts() {
        return start.length;
    }

    public int start(int f) {
        return start[f];
    }

    public int end(int f) {
        return end[f];
    }

    public int cheer(int f) {
        return cheer[f];
    }

    /** The most cheer any clash-free booking brings. */
    public int most() {
        return most;
    }

    public int bookedCheer() {
        return booked.stream().mapToInt(f -> cheer[f]).sum();
    }

    public int[] overlap() {
        return overlap == null ? null : overlap.clone();
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    private Outcome guard(String eventId) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        return events.contains(eventId) ? Outcome.DUPLICATE : null;
    }

    /** Books a feast into the hall, or strikes it if already booked. */
    public Outcome toggle(String eventId, int f) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (f < 0 || f >= start.length) {
            return Outcome.NOT_THERE;
        }
        events.add(eventId);
        last = null;
        overlap = null;
        if (booked.remove(f)) {
            return Outcome.STRUCK;
        }
        booked.add(f);
        quest.apply(eventId, "book", "feast");
        return Outcome.BOOKED;
    }

    /** Opens the hall for the season: OVERLAP on any clash, WELL at the most cheer, else DIM. */
    public Outcome open(String eventId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        events.add(eventId);
        overlap = null;
        Integer[] b = booked.toArray(new Integer[0]);
        for (int i = 0; i < b.length && overlap == null; i++) {
            for (int j = i + 1; j < b.length; j++) {
                if (clash(start[b[i]], end[b[i]], start[b[j]], end[b[j]])) {
                    overlap = new int[] {b[i], b[j]};
                    break;
                }
            }
        }
        if (overlap != null) {
            last = Outcome.OVERLAP;
        } else {
            last = bookedCheer() == most ? Outcome.WELL : Outcome.DIM;
        }
        if (last == Outcome.WELL) {
            quest.apply(eventId, "open", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the hall opened well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperFeastLines.THANKS;
        }
        return KeeperFeastLines.line(this);
    }
}
