// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.weave;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 55 of the Youtube Master Island story, "The Loom Pattern" (quest {@code q_loom_pattern}). A woven strip of
 * coloured threads and a family pattern; {@link #starts()} lists every start of the pattern in the strip with
 * Knuth-Morris-Pratt (a failure table, linear time). Marking the first start earns credit; anything else is FRAYED.
 */
public final class LoomPattern {
    public static final String QUEST_ID = "q_loom_pattern";

    public enum Outcome { CLEAN, FRAYED, NOT_THERE, DUPLICATE, IGNORED }

    private final String strip;
    private final String pattern;
    private final List<Integer> starts;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("weave", "strip", 1),
            new QuestProgress.Step("mark", "first", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int marked = -1;
    private Outcome last;

    /** A strip and a non-empty pattern, both of thread letters. */
    public LoomPattern(String strip, String pattern) {
        if (strip == null || pattern == null || strip.isEmpty() || pattern.isEmpty()) {
            throw new IllegalArgumentException("a strip and a pattern");
        }
        this.strip = strip;
        this.pattern = pattern;
        this.starts = List.copyOf(kmp(strip, pattern));
    }

    /** The KMP failure table: longest proper prefix of p[0..i] that is also its suffix. */
    static int[] failure(String p) {
        int[] f = new int[p.length()];
        int k = 0;
        for (int i = 1; i < p.length(); i++) {
            while (k > 0 && p.charAt(i) != p.charAt(k)) {
                k = f[k - 1];
            }
            if (p.charAt(i) == p.charAt(k)) {
                k++;
            }
            f[i] = k;
        }
        return f;
    }

    static List<Integer> kmp(String s, String p) {
        int[] f = failure(p);
        List<Integer> out = new ArrayList<>();
        int k = 0;
        for (int i = 0; i < s.length(); i++) {
            while (k > 0 && s.charAt(i) != p.charAt(k)) {
                k = f[k - 1];
            }
            if (s.charAt(i) == p.charAt(k)) {
                k++;
            }
            if (k == p.length()) {
                out.add(i - k + 1);
                k = f[k - 1];
            }
        }
        return out;
    }

    /** A seeded strip of 1-30 threads over 2-3 colours and a pattern of 1-4. */
    public static LoomPattern seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x100FL);
        int colours = 2 + rng.nextInt(2);
        StringBuilder s = new StringBuilder();
        int n = 1 + rng.nextInt(30);
        for (int i = 0; i < n; i++) {
            s.append((char) ('a' + rng.nextInt(colours)));
        }
        StringBuilder p = new StringBuilder();
        int m = 1 + rng.nextInt(4);
        for (int i = 0; i < m; i++) {
            p.append((char) ('a' + rng.nextInt(colours)));
        }
        return new LoomPattern(s.toString(), p.toString());
    }

    public String strip() {
        return strip;
    }

    public String pattern() {
        return pattern;
    }

    /** Every start of the pattern, overlaps included, in order. */
    public List<Integer> starts() {
        return starts;
    }

    /** The first start, or -1 if the pattern is not woven in. */
    public int first() {
        return starts.isEmpty() ? -1 : starts.get(0);
    }

    public int marked() {
        return marked;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Watches the strip come off the loom: the quest's first step. */
    public void weave(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "weave", "strip");
        }
    }

    /** Marks a thread: CLEAN if the pattern first starts there, else FRAYED (always, if the pattern is absent). */
    public Outcome mark(String eventId, int thread) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (thread < 0 || thread >= strip.length()) {
            return Outcome.NOT_THERE;
        }
        events.add(eventId);
        marked = thread;
        last = thread == first() ? Outcome.CLEAN : Outcome.FRAYED;
        if (last == Outcome.CLEAN) {
            quest.apply(eventId, "mark", "first");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the first start is marked. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperLoomLines.THANKS;
        }
        return KeeperLoomLines.line(this);
    }
}
