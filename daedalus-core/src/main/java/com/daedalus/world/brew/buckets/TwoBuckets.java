// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.buckets;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 48 of the Youtube Master Island story, "The Two Buckets" (quest {@code q_two_buckets}). Two unmarked buckets
 * hold {@code a} and {@code b}. A move fills a bucket from the sea (FA, FB), empties it (EA, EB) or pours one into the
 * other until it is empty or the other is full (AB, BA). {@link #fewest()} is the fewest moves until either bucket
 * holds exactly the target, by breadth-first search over bucket states, or -1 if it cannot be done. A move list that
 * reaches the target in that many moves earns credit; a longer one does not, and one that MISSES earns none.
 */
public final class TwoBuckets {
    public static final String QUEST_ID = "q_two_buckets";

    public enum Outcome { WELL, LONG, MISSED, NOT_THERE, DUPLICATE, IGNORED }

    public static final List<String> MOVES = List.of("FA", "FB", "EA", "EB", "AB", "BA");

    private final int a;
    private final int b;
    private final int target;
    private final int fewest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("fetch", "buckets", 1),
            new QuestProgress.Step("measure", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int used = -1;
    private Outcome last;

    public TwoBuckets(int a, int b, int target) {
        if (a <= 0 || b <= 0 || target <= 0 || target > Math.max(a, b)) {
            throw new IllegalArgumentException("the target must fit in a bucket");
        }
        this.a = a;
        this.b = b;
        this.target = target;
        int[][] dist = new int[a + 1][b + 1];
        for (int[] row : dist) {
            Arrays.fill(row, -1);
        }
        dist[0][0] = 0;
        Deque<int[]> q = new ArrayDeque<>();
        q.add(new int[] {0, 0});
        int found = -1;
        while (!q.isEmpty() && found < 0) {
            int[] s = q.poll();
            if (s[0] == target || s[1] == target) {
                found = dist[s[0]][s[1]];
                break;
            }
            for (String m : MOVES) {
                int[] t = step(s, m);
                if (dist[t[0]][t[1]] < 0) {
                    dist[t[0]][t[1]] = dist[s[0]][s[1]] + 1;
                    q.add(t);
                }
            }
        }
        fewest = found;
    }

    /** One move from state {@code s}. */
    public int[] step(int[] s, String move) {
        int x = s[0];
        int y = s[1];
        switch (move) {
            case "FA" -> x = a;
            case "FB" -> y = b;
            case "EA" -> x = 0;
            case "EB" -> y = 0;
            case "AB" -> {
                int p = Math.min(x, b - y);
                x -= p;
                y += p;
            }
            case "BA" -> {
                int p = Math.min(y, a - x);
                y -= p;
                x += p;
            }
            default -> throw new IllegalArgumentException("no such move");
        }
        return new int[] {x, y};
    }

    /** A seeded pair of buckets of 1-7 and a target that fits. */
    public static TwoBuckets seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xB0C7L);
        int a = 1 + rng.nextInt(7);
        int b = 1 + rng.nextInt(7);
        return new TwoBuckets(a, b, 1 + rng.nextInt(Math.max(a, b)));
    }

    public int bucketA() {
        return a;
    }

    public int bucketB() {
        return b;
    }

    public int target() {
        return target;
    }

    /** The fewest moves to the target, or -1 if it cannot be measured. */
    public int fewest() {
        return fewest;
    }

    public int used() {
        return used;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Fetches the buckets: the quest's first step. */
    public void fetch(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "fetch", "buckets");
        }
    }

    /** Plays a list of moves from empty buckets: MISSED unless it ends on the target, WELL in the fewest, else LONG. */
    public Outcome measure(String eventId, String... moves) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (moves == null) {
            return Outcome.NOT_THERE;
        }
        for (String m : moves) {
            if (!MOVES.contains(m)) {
                return Outcome.NOT_THERE;
            }
        }
        events.add(eventId);
        int[] s = {0, 0};
        for (String m : moves) {
            s = step(s, m);
        }
        used = moves.length;
        if (s[0] != target && s[1] != target) {
            last = Outcome.MISSED;
        } else {
            last = used == fewest ? Outcome.WELL : Outcome.LONG;
        }
        if (last == Outcome.WELL) {
            quest.apply(eventId, "measure", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the brine is measured well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperBucketLines.THANKS;
        }
        return KeeperBucketLines.line(this);
    }
}
