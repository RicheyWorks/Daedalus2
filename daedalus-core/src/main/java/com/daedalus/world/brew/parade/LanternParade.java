// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.parade;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 23 of the Youtube Master Island story, "The Lantern Parade" (quest {@code q_lantern_parade}). The children
 * stand in a seeded line; the walkers kept must carry strictly rising lanterns in line order. The parade is bright when
 * it is also the longest such parade; {@link #longest()} is exact longest-increasing-subsequence DP and
 * {@link #bestParade()} walks it back.
 */
public final class LanternParade {
    public static final String QUEST_ID = "q_lantern_parade";
    public static final int CHILDREN_TO_KEEP = 3;
    static final String[] NAMES = {"ada", "bram", "coll", "dilly", "eno", "fay", "gus", "hettie", "ivo", "jess", "kit",
        "lune"};

    public enum Outcome { KEPT, SEATED, ALREADY_KEPT, NOT_KEPT, UNKNOWN, BRIGHT, DIM, NOT_RISING, EMPTY, DUPLICATE,
        IGNORED }

    private final List<Walker> line;
    private final Map<String, Integer> index = new LinkedHashMap<>();
    private final Set<String> kept = new HashSet<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("keep", "child", CHILDREN_TO_KEEP),
            new QuestProgress.Step("march", "bright", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private final List<Walker> best;
    private Outcome last;

    public LanternParade(List<Walker> walkers) {
        if (walkers.isEmpty()) {
            throw new IllegalArgumentException("nobody in line");
        }
        for (int i = 0; i < walkers.size(); i++) {
            if (index.put(walkers.get(i).name(), i) != null) {
                throw new IllegalArgumentException("duplicate walker " + walkers.get(i).name());
            }
        }
        line = List.copyOf(walkers);
        best = List.copyOf(lis(line));
    }

    /** A seeded line: 6-12 children with poles of height 1-15 (repeats allowed). */
    public static LanternParade seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x1A27EL);
        int n = 6 + rng.nextInt(7);
        List<Walker> out = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            out.add(new Walker(NAMES[i], 1 + rng.nextInt(15)));
        }
        return new LanternParade(out);
    }

    /** O(n^2) LIS: len[i] = longest strictly rising parade ending at i, prev[i] its walker before. */
    static List<Walker> lis(List<Walker> line) {
        int n = line.size();
        int[] len = new int[n];
        int[] prev = new int[n];
        int end = 0;
        for (int i = 0; i < n; i++) {
            len[i] = 1;
            prev[i] = -1;
            for (int j = 0; j < i; j++) {
                if (line.get(j).height() < line.get(i).height() && len[j] + 1 > len[i]) {
                    len[i] = len[j] + 1;
                    prev[i] = j;
                }
            }
            if (len[i] > len[end]) {
                end = i;
            }
        }
        List<Walker> out = new ArrayList<>();
        for (int i = end; i >= 0; i = prev[i]) {
            out.add(0, line.get(i));
        }
        return out;
    }

    public List<Walker> line() {
        return line;
    }

    /** The most children that can walk with strictly rising lanterns. */
    public int longest() {
        return best.size();
    }

    /** One longest parade in line order. */
    public List<Walker> bestParade() {
        return best;
    }

    /** The kept walkers in line order. */
    public List<Walker> parade() {
        return line.stream().filter(w -> kept.contains(w.name())).toList();
    }

    /** Whether the kept walkers carry strictly rising lanterns. */
    public boolean rising() {
        List<Walker> p = parade();
        for (int i = 1; i < p.size(); i++) {
            if (p.get(i).height() <= p.get(i - 1).height()) {
                return false;
            }
        }
        return true;
    }

    public QuestProgress quest() {
        return quest;
    }

    public Outcome last() {
        return last;
    }

    private Outcome guard(String eventId, String name) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        return name == null || index.containsKey(name) ? null : Outcome.UNKNOWN;
    }

    /** Keeps a child in the parade. */
    public Outcome keep(String eventId, String name) {
        Outcome g = guard(eventId, name);
        if (g != null) {
            return g;
        }
        if (name == null) {
            return Outcome.UNKNOWN;
        }
        if (!kept.add(name)) {
            return Outcome.ALREADY_KEPT;
        }
        events.add(eventId);
        last = null;
        quest.apply(eventId, "keep", "child");
        return Outcome.KEPT;
    }

    /** Sits a child out on the sand to watch. */
    public Outcome seat(String eventId, String name) {
        Outcome g = guard(eventId, name);
        if (g != null) {
            return g;
        }
        if (name == null || !kept.remove(name)) {
            return Outcome.NOT_KEPT;
        }
        events.add(eventId);
        last = null;
        return Outcome.SEATED;
    }

    /** Starts the parade: EMPTY or NOT_RISING (no credit), BRIGHT at the longest, else DIM. */
    public Outcome march(String eventId) {
        Outcome g = guard(eventId, null);
        if (g != null) {
            return g;
        }
        if (kept.isEmpty()) {
            return Outcome.EMPTY;
        }
        if (!rising()) {
            return Outcome.NOT_RISING;
        }
        events.add(eventId);
        last = kept.size() == longest() ? Outcome.BRIGHT : Outcome.DIM;
        if (last == Outcome.BRIGHT) {
            quest.apply(eventId, "march", "bright");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once a parade was bright. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperParadeLines.THANKS;
        }
        return KeeperParadeLines.line(this);
    }
}
