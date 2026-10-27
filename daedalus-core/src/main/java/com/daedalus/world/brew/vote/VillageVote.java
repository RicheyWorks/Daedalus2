// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.vote;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 67 of the Youtube Master Island story, "The Village Vote" (quest {@code q_village_vote}). Shells marked with
 * choices; {@link #majority()} is the choice on more than half the shells, or {@link #NONE}, by the Boyer-Moore
 * majority vote (one pass with a candidate and a counter) and a confirming count. Naming it earns credit; a WRONG
 * answer earns none.
 */
public final class VillageVote {
    public static final String QUEST_ID = "q_village_vote";
    /** No majority. */
    public static final int NONE = -1;

    public enum Outcome { RIGHT, WRONG, DUPLICATE, IGNORED }

    private final List<Integer> shells;
    private final int majority;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("open", "jar", 1),
            new QuestProgress.Step("name", "winner", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = NONE;
    private Outcome last;

    /** Choices on the shells, each 0 or more. */
    public VillageVote(List<Integer> shells) {
        if (shells == null || shells.isEmpty()) {
            throw new IllegalArgumentException("at least one shell");
        }
        int candidate = NONE;
        int count = 0;
        for (Integer s : shells) {
            if (s == null || s < 0) {
                throw new IllegalArgumentException("a shell names a choice");
            }
            if (count == 0) {
                candidate = s;
                count = 1;
            } else {
                count += s == candidate ? 1 : -1;
            }
        }
        this.shells = List.copyOf(shells);
        int votes = 0;
        for (int s : this.shells) {
            votes += s == candidate ? 1 : 0;
        }
        majority = 2 * votes > shells.size() ? candidate : NONE;
    }

    /** A seeded vote of 1-15 shells over 1-3 choices, leaning toward choice 0 so majorities happen. */
    public static VillageVote seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x7073L);
        int n = 1 + rng.nextInt(15);
        int k = 1 + rng.nextInt(3);
        List<Integer> s = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            s.add(rng.nextBoolean() ? 0 : rng.nextInt(k));
        }
        return new VillageVote(s);
    }

    public List<Integer> shells() {
        return shells;
    }

    /** The choice on more than half the shells, or {@link #NONE}. */
    public int majority() {
        return majority;
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

    /** Opens the voting jar: the quest's first step. */
    public void open(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "open", "jar");
        }
    }

    /** Names the winning choice, or {@link #NONE}: RIGHT or WRONG. */
    public Outcome name(String eventId, int choice) {
        if (eventId == null || eventId.isBlank() || choice < NONE) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        named = choice;
        last = choice == majority ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "name", "winner");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the vote is read right. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperVoteLines.THANKS;
        }
        return KeeperVoteLines.line(this);
    }
}
