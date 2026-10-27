// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.beacons;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 93 of the Youtube Master Island story, "The Beacon Fence" (quest {@code q_beacon_fence}). A tight rope must
 * enclose every beacon post. {@link #corners()} counts the posts it bends at, by Andrew's monotone chain convex hull
 * (posts on a straight stretch dropped); {@link #all()} is the trap, every post. Naming the corners earns credit; a
 * WRONG count, or posts too FLAT to fence, earns none.
 */
public final class BeaconFence {
    public static final String QUEST_ID = "q_beacon_fence";

    public enum Outcome { RIGHT, WRONG, FLAT, MALFORMED, DUPLICATE, IGNORED }

    private final List<List<Integer>> posts;
    private final int corners;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "posts", 1),
            new QuestProgress.Step("count", "corners", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Distinct posts [x, y], 1 or more. */
    public BeaconFence(List<List<Integer>> posts) {
        if (posts == null || posts.isEmpty() || posts.stream().anyMatch(p -> p == null || p.size() != 2
                || p.get(0) == null || p.get(1) == null) || new HashSet<>(posts).size() != posts.size()) {
            throw new IllegalArgumentException("real distinct posts");
        }
        this.posts = List.copyOf(posts.stream().map(List::copyOf).toList());
        List<List<Integer>> sorted = new ArrayList<>(this.posts);
        sorted.sort(Comparator.<List<Integer>>comparingInt(p -> p.get(0)).thenComparingInt(p -> p.get(1)));
        List<List<Integer>> hull = new ArrayList<>();
        for (int pass = 0; pass < 2; pass++) {
            int base = hull.size();
            for (List<Integer> p : sorted) {
                while (hull.size() >= base + 2 && cross(hull.get(hull.size() - 2), hull.get(hull.size() - 1), p) <= 0) {
                    hull.remove(hull.size() - 1);
                }
                hull.add(p);
            }
            hull.remove(hull.size() - 1);
            Collections.reverse(sorted);
        }
        corners = hull.size() < 3 ? 0 : hull.size();
    }

    static long cross(List<Integer> o, List<Integer> a, List<Integer> b) {
        return (long) (a.get(0) - o.get(0)) * (b.get(1) - o.get(1)) - (long) (a.get(1) - o.get(1)) * (b.get(0) - o.get(0));
    }

    /** A seeded headland of 3-7 distinct posts on a 5x5 grid. */
    public static BeaconFence seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xBEACL);
        int n = 3 + rng.nextInt(5);
        List<List<Integer>> p = new ArrayList<>();
        while (p.size() < n) {
            List<Integer> q = List.of(rng.nextInt(5), rng.nextInt(5));
            if (!p.contains(q)) {
                p.add(q);
            }
        }
        return new BeaconFence(p);
    }

    public List<List<Integer>> posts() {
        return posts;
    }

    /** Posts the rope bends at (convex hull corners), or 0 if flat. */
    public int corners() {
        return corners;
    }

    /** Every post: the trap. */
    public int all() {
        return posts.size();
    }

    /** Whether the posts stand in one line (or there are fewer than three). */
    public boolean flat() {
        return corners == 0;
    }

    public int named() {
        return named;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Reads the beacon posts: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "posts");
        }
    }

    /** Names the answer: RIGHT, WRONG, FLAT or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (flat()) {
            last = Outcome.FLAT;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == corners() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "corners");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperBeaconFence.THANKS;
        }
        return KeeperBeaconFence.line(this);
    }
}
