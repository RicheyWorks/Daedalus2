// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lamplight;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 74 of the Youtube Master Island story, "The Lamplighter's Round" (quest {@code q_lamplighter_round}). Posts
 * 0..n-1 stand in a ring; post i leaves {@code oil[i]} in the can and the walk from post i to post i+1 burns
 * {@code burn[i]}. {@link #start()} is the first post from which the lamplighter can walk the whole ring without the
 * can running dry, by the one-pass circular greedy (reset the start after every deficit), or {@link #NONE} if the ring
 * holds less oil than it burns. Naming that post earns credit; a DRY start or a ring SHORT of oil earns none.
 */
public final class LamplighterRound {
    public static final String QUEST_ID = "q_lamplighter_round";
    /** No post works: the ring burns more oil than it holds. */
    public static final int NONE = -1;

    public enum Outcome { FIRST, LATER, DRY, SHORT, MALFORMED, DUPLICATE, IGNORED }

    private final List<Integer> oil;
    private final List<Integer> burn;
    private final int start;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("walk", "ring", 1),
            new QuestProgress.Step("start", "post", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = NONE;
    private Outcome last;

    /** Oil left at each post and oil burnt walking to the next post (same length, at least one post). */
    public LamplighterRound(List<Integer> oil, List<Integer> burn) {
        if (oil == null || burn == null || oil.isEmpty() || oil.size() != burn.size()) {
            throw new IllegalArgumentException("one oil and one burn per post");
        }
        for (int i = 0; i < oil.size(); i++) {
            if (oil.get(i) == null || burn.get(i) == null || oil.get(i) < 0 || burn.get(i) < 0) {
                throw new IllegalArgumentException("oil and burn are never negative");
            }
        }
        this.oil = List.copyOf(oil);
        this.burn = List.copyOf(burn);
        long total = 0;
        long tank = 0;
        int from = 0;
        for (int i = 0; i < oil.size(); i++) {
            int gain = oil.get(i) - burn.get(i);
            total += gain;
            tank += gain;
            if (tank < 0) {
                from = i + 1;
                tank = 0;
            }
        }
        start = total < 0 ? NONE : from;
    }

    /** Whether walking the whole ring from post s keeps the can at zero or above. */
    public boolean makesIt(int s) {
        long tank = 0;
        for (int k = 0; k < oil.size(); k++) {
            int i = (s + k) % oil.size();
            tank += oil.get(i) - burn.get(i);
            if (tank < 0) {
                return false;
            }
        }
        return true;
    }

    /** A seeded ring of 1-7 posts, oil 0-6 and burn 0-6. */
    public static LamplighterRound seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x1A3B5L);
        int n = 1 + rng.nextInt(7);
        List<Integer> o = new ArrayList<>();
        List<Integer> b = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            o.add(rng.nextInt(7));
            b.add(rng.nextInt(7));
        }
        return new LamplighterRound(o, b);
    }

    public int posts() {
        return oil.size();
    }

    public List<Integer> oil() {
        return oil;
    }

    public List<Integer> burn() {
        return burn;
    }

    /** The first post that completes the ring, or {@link #NONE}. */
    public int start() {
        return start;
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

    /** Walks the ring once to read the posts: the quest's first step. */
    public void walk(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "walk", "ring");
        }
    }

    /** Names a starting post: FIRST, LATER (works, but an earlier post works too), DRY, SHORT or MALFORMED. */
    public Outcome name(String eventId, int post) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (start == NONE) {
            last = Outcome.SHORT;
            return last;
        }
        if (post < 0 || post >= oil.size()) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = post;
        last = !makesIt(post) ? Outcome.DRY : post == start ? Outcome.FIRST : Outcome.LATER;
        if (last == Outcome.FIRST) {
            quest.apply(eventId, "start", "post");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the first good post is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return String.format(KeeperLamplighter.THANKS, start);
        }
        return KeeperLamplighter.line(this);
    }
}
