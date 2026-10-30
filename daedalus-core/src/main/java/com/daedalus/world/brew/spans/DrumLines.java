// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.spans;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 72 of the Youtube Master Island story, "The Drum Lines" (quest {@code q_drum_lines}). Possible drum lines
 * {a, b, rope} between huts; {@link #cheapest()} is the least rope linking every hut, by Kruskal's algorithm (lines
 * sorted by rope, joined with union-find), or {@link #NONE} if no set links them all. Picking a set that links every
 * hut with that much rope earns credit; a DEAR or BROKEN pick earns none.
 */
public final class DrumLines {
    public static final String QUEST_ID = "q_drum_lines";
    /** The huts cannot all be linked. */
    public static final long NONE = -1;

    public enum Outcome { CHEAPEST, DEAR, BROKEN, CUT_OFF, MALFORMED, DUPLICATE, IGNORED }

    private final int huts;
    private final List<int[]> lines;
    private final long cheapest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("survey", "village", 1),
            new QuestProgress.Step("string", "lines", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private long picked = NONE;
    private Outcome last;

    /** Huts 0..n-1 and possible lines {a, b, rope}. */
    public DrumLines(int huts, List<int[]> lines) {
        if (huts <= 0 || lines == null) {
            throw new IllegalArgumentException("at least one hut");
        }
        this.huts = huts;
        this.lines = new ArrayList<>();
        for (int[] l : lines) {
            if (l.length != 3 || l[0] < 0 || l[1] < 0 || l[0] >= huts || l[1] >= huts || l[0] == l[1] || l[2] <= 0) {
                throw new IllegalArgumentException("a line joins two real huts and takes rope");
            }
            this.lines.add(l.clone());
        }
        List<int[]> sorted = new ArrayList<>(this.lines);
        sorted.sort(Comparator.comparingInt(l -> l[2]));
        int[] parent = new int[huts];
        for (int i = 0; i < huts; i++) {
            parent[i] = i;
        }
        long rope = 0;
        int joined = 0;
        for (int[] l : sorted) {
            int a = find(parent, l[0]);
            int b = find(parent, l[1]);
            if (a != b) {
                parent[a] = b;
                rope += l[2];
                joined++;
            }
        }
        cheapest = joined == huts - 1 ? rope : NONE;
    }

    static int find(int[] parent, int x) {
        while (parent[x] != x) {
            parent[x] = parent[parent[x]];
            x = parent[x];
        }
        return x;
    }

    /** A seeded village of 1-5 huts and 0-8 possible lines of rope 1-9. */
    public static DrumLines seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xD2A1L);
        int n = 1 + rng.nextInt(5);
        int m = n < 2 ? 0 : rng.nextInt(9);
        List<int[]> l = new ArrayList<>();
        for (int i = 0; i < m; i++) {
            int a = rng.nextInt(n);
            int b = (a + 1 + rng.nextInt(n - 1)) % n;
            l.add(new int[] {a, b, 1 + rng.nextInt(9)});
        }
        return new DrumLines(n, l);
    }

    public int huts() {
        return huts;
    }

    /** The possible lines (copies). */
    public List<int[]> lines() {
        List<int[]> out = new ArrayList<>();
        for (int[] l : lines) {
            out.add(l.clone());
        }
        return out;
    }

    /** The least rope linking every hut, or {@link #NONE}. */
    public long cheapest() {
        return cheapest;
    }

    /** Whether the chosen lines (by index) link every hut. */
    public boolean links(Set<Integer> chosen) {
        int[] parent = new int[huts];
        for (int i = 0; i < huts; i++) {
            parent[i] = i;
        }
        int groups = huts;
        for (int i : chosen) {
            int a = find(parent, lines.get(i)[0]);
            int b = find(parent, lines.get(i)[1]);
            if (a != b) {
                parent[a] = b;
                groups--;
            }
        }
        return groups == 1;
    }

    public long picked() {
        return picked;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Surveys the village: the quest's first step. */
    public void survey(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "survey", "village");
        }
    }

    /** Strings lines by index (each once): CHEAPEST, DEAR, BROKEN, CUT_OFF or MALFORMED. */
    public Outcome string(String eventId, List<Integer> picks) {
        if (eventId == null || eventId.isBlank() || picks == null) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (cheapest == NONE) {
            last = Outcome.CUT_OFF;
            return last;
        }
        Set<Integer> chosen = new HashSet<>();
        long rope = 0;
        for (Integer p : picks) {
            if (p == null || p < 0 || p >= lines.size() || !chosen.add(p)) {
                last = Outcome.MALFORMED;
                return last;
            }
            rope += lines.get(p)[2];
        }
        picked = rope;
        last = !links(chosen) ? Outcome.BROKEN : rope == cheapest ? Outcome.CHEAPEST : Outcome.DEAR;
        if (last == Outcome.CHEAPEST) {
            quest.apply(eventId, "string", "lines");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the cheapest lines are strung. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperDrumLines.THANKS;
        }
        return KeeperDrumLines.line(this);
    }
}
