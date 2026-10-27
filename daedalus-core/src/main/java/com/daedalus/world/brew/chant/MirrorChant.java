// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.chant;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 69 of the Youtube Master Island story, "The Mirror Chant" (quest {@code q_mirror_chant}). A chant of
 * syllables; {@link #longest()} is the length of its longest palindromic stretch, by Manacher's algorithm (radii over
 * the chant with gaps between syllables, linear time). Marking a stretch that long and mirrored earns credit; a SHORT
 * or BROKEN mark earns none.
 */
public final class MirrorChant {
    public static final String QUEST_ID = "q_mirror_chant";

    public enum Outcome { MIRROR, SHORT, BROKEN, NOT_THERE, DUPLICATE, IGNORED }

    private final String chant;
    private final int longest;
    private final int longestStart;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("hear", "chant", 1),
            new QuestProgress.Step("mark", "mirror", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private String marked = "";
    private Outcome last;

    /** A non-empty chant of lowercase syllable letters. */
    public MirrorChant(String chant) {
        if (chant == null || !chant.matches("[a-z]+")) {
            throw new IllegalArgumentException("a chant of syllables");
        }
        this.chant = chant;
        int m = 2 * chant.length() + 1;
        int[] rad = new int[m];
        int centre = 0;
        int right = 0;
        int best = 0;
        int bestAt = 0;
        for (int i = 0; i < m; i++) {
            int r = i < right ? Math.min(right - i, rad[2 * centre - i]) : 0;
            while (i - r - 1 >= 0 && i + r + 1 < m && at(i - r - 1) == at(i + r + 1)) {
                r++;
            }
            rad[i] = r;
            if (i + r > right) {
                centre = i;
                right = i + r;
            }
            if (r > best) {
                best = r;
                bestAt = (i - r) / 2;
            }
        }
        longest = best;
        longestStart = bestAt;
    }

    /** The chant with gaps: even positions are gaps, odd positions syllables. */
    private char at(int k) {
        return k % 2 == 0 ? '|' : chant.charAt(k / 2);
    }

    /** A seeded chant of 1-20 syllables over 2-3 sounds. */
    public static MirrorChant seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xC4A7L);
        int n = 1 + rng.nextInt(20);
        int k = 2 + rng.nextInt(2);
        StringBuilder s = new StringBuilder();
        for (int i = 0; i < n; i++) {
            s.append((char) ('a' + rng.nextInt(k)));
        }
        return new MirrorChant(s.toString());
    }

    public String chant() {
        return chant;
    }

    /** The length of the longest palindromic stretch. */
    public int longest() {
        return longest;
    }

    /** One longest mirror verse. */
    public String verse() {
        return chant.substring(longestStart, longestStart + longest);
    }

    public String marked() {
        return marked;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Hears the chant: the quest's first step. */
    public void hear(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "hear", "chant");
        }
    }

    /** Marks syllables start..end-1: MIRROR, SHORT, BROKEN or NOT_THERE. */
    public Outcome mark(String eventId, int start, int end) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (start < 0 || start >= end || end > chant.length()) {
            return Outcome.NOT_THERE;
        }
        events.add(eventId);
        marked = chant.substring(start, end);
        boolean mirrored = new StringBuilder(marked).reverse().toString().equals(marked);
        last = !mirrored ? Outcome.BROKEN : marked.length() == longest ? Outcome.MIRROR : Outcome.SHORT;
        if (last == Outcome.MIRROR) {
            quest.apply(eventId, "mark", "mirror");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the mirror verse is marked. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperChantLines.THANKS;
        }
        return KeeperChantLines.line(this);
    }
}
