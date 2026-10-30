// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.refrain;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 84 of the Youtube Master Island story, "The Refrain Count" (quest {@code q_refrain_count}). A long work song
 * and a short refrain, both strings of drum beats (letters a-c); {@link #times()} counts every place the refrain
 * starts in the song, overlapping ones included, by the Z-function of {@code refrain + '|' + song} (each Z value at
 * least the refrain's length marks a match). Naming the count earns credit; a WRONG count, or a refrain NEVER_SUNG,
 * earns none.
 */
public final class RefrainCount {
    public static final String QUEST_ID = "q_refrain_count";

    public enum Outcome { RIGHT, WRONG, NEVER_SUNG, MALFORMED, DUPLICATE, IGNORED }

    private final String song;
    private final String refrain;
    private final int times;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("hear", "song", 1),
            new QuestProgress.Step("count", "refrains", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** A song and a non-empty refrain of beats a, b, c. */
    public RefrainCount(String song, String refrain) {
        if (song == null || refrain == null || refrain.isEmpty() || !song.matches("[abc]*")
                || !refrain.matches("[abc]+")) {
            throw new IllegalArgumentException("a song and a refrain of a, b, c beats");
        }
        this.song = song;
        this.refrain = refrain;
        int[] z = zFunction(refrain + "|" + song);
        int c = 0;
        for (int i = refrain.length() + 1; i < z.length; i++) {
            if (z[i] >= refrain.length()) {
                c++;
            }
        }
        times = c;
    }

    /** z[i] = length of the longest common prefix of s and s.substring(i) (z[0] = 0). */
    static int[] zFunction(String s) {
        int n = s.length();
        int[] z = new int[n];
        int l = 0;
        int r = 0;
        for (int i = 1; i < n; i++) {
            if (i < r) {
                z[i] = Math.min(r - i, z[i - l]);
            }
            while (i + z[i] < n && s.charAt(z[i]) == s.charAt(i + z[i])) {
                z[i]++;
            }
            if (i + z[i] > r) {
                l = i;
                r = i + z[i];
            }
        }
        return z;
    }

    /** A seeded song of 0-24 beats and a refrain of 1-3 beats from a, b (and sometimes c). */
    public static RefrainCount seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x2EF2L);
        int beats = 2 + rng.nextInt(2);
        return new RefrainCount(beats(rng, rng.nextInt(25), beats), beats(rng, 1 + rng.nextInt(3), beats));
    }

    private static String beats(SplittableRandom rng, int n, int kinds) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) {
            sb.append((char) ('a' + rng.nextInt(kinds)));
        }
        return sb.toString();
    }

    public String song() {
        return song;
    }

    public String refrain() {
        return refrain;
    }

    /** Places the refrain starts in the song, overlaps included. */
    public int times() {
        return times;
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

    /** Hears the whole song: the quest's first step. */
    public void hear(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "hear", "song");
        }
    }

    /** Names how many times the refrain is sung: RIGHT, WRONG, NEVER_SUNG or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (times == 0) {
            last = Outcome.NEVER_SUNG;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == times ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "refrains");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the refrains are counted. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperRefrain.THANKS;
        }
        return KeeperRefrain.line(this);
    }
}
