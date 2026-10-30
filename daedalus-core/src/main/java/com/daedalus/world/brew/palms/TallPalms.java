// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.palms;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 65 of the Youtube Master Island story, "The Tall Palms" (quest {@code q_tall_palms}). Palms of given heights
 * stand along the shore; {@link #nextTaller(int)} is the first palm further along that is strictly taller, for every
 * palm at once with a monotonic stack. Naming it for the {@link #asked()} palm (or {@link #NONE}) earns credit; a WRONG
 * palm earns none.
 */
public final class TallPalms {
    public static final String QUEST_ID = "q_tall_palms";
    /** No taller palm further along. */
    public static final int NONE = -1;

    public enum Outcome { RIGHT, WRONG, DUPLICATE, IGNORED }

    private final List<Integer> heights;
    private final int[] next;
    private final int asked;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("walk", "shore", 1),
            new QuestProgress.Step("name", "taller", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = NONE;
    private Outcome last;

    /** Positive palm heights and the palm the climber is on. */
    public TallPalms(List<Integer> heights, int asked) {
        if (heights == null || heights.isEmpty() || asked < 0 || asked >= heights.size()) {
            throw new IllegalArgumentException("palms and a climber on one of them");
        }
        for (Integer h : heights) {
            if (h == null || h <= 0) {
                throw new IllegalArgumentException("a palm has height");
            }
        }
        this.heights = List.copyOf(heights);
        this.asked = asked;
        next = new int[heights.size()];
        Arrays.fill(next, NONE);
        Deque<Integer> stack = new ArrayDeque<>();
        for (int i = 0; i < heights.size(); i++) {
            while (!stack.isEmpty() && heights.get(stack.peek()) < heights.get(i)) {
                next[stack.pop()] = i;
            }
            stack.push(i);
        }
    }

    /** A seeded shore of 1-15 palms of height 1-9 and a climber on any palm. */
    public static TallPalms seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xFA1EL);
        int n = 1 + rng.nextInt(15);
        List<Integer> h = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            h.add(1 + rng.nextInt(9));
        }
        return new TallPalms(h, rng.nextInt(n));
    }

    public List<Integer> heights() {
        return heights;
    }

    public int palms() {
        return heights.size();
    }

    /** The first strictly taller palm after palm i, or {@link #NONE}. */
    public int nextTaller(int i) {
        return next[i];
    }

    public int asked() {
        return asked;
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

    /** Walks the shore: the quest's first step. */
    public void walk(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "walk", "shore");
        }
    }

    /** Names the next taller palm for the asked palm, or {@link #NONE}: RIGHT or WRONG. */
    public Outcome name(String eventId, int palm) {
        if (eventId == null || eventId.isBlank() || palm < NONE || palm >= palms()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        named = palm;
        last = palm == next[asked] ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "name", "taller");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the palm is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperPalmLines.THANKS;
        }
        return KeeperPalmLines.line(this);
    }
}
