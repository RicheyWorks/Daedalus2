// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.orchard;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 37 of the Youtube Master Island story, "The Orchard Rows" (quest {@code q_orchard_rows}). A row of apple
 * trees, each with some apples. Any tree may be stripped, but never two side by side. {@link #most()} is the exact
 * maximum non-adjacent sum by a two-state DP. Carrying in that many apples earns credit; stripping neighbours or a
 * lighter basket does not.
 */
public final class OrchardRows {
    public static final String QUEST_ID = "q_orchard_rows";

    public enum Outcome { STRIPPED, LEFT, NOT_THERE, WELL, LIGHT, NEIGHBOURS, DUPLICATE, IGNORED }

    private final int[] apples;
    private final boolean[] stripped;
    private final int most;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("strip", "tree", 1),
            new QuestProgress.Step("carry", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private Outcome last;
    private int[] neighbours;

    public OrchardRows(int... apples) {
        if (apples == null || apples.length == 0) {
            throw new IllegalArgumentException("at least one tree");
        }
        for (int a : apples) {
            if (a < 0) {
                throw new IllegalArgumentException("apples are counted, not owed");
            }
        }
        this.apples = apples.clone();
        stripped = new boolean[apples.length];
        int take = 0;
        int skip = 0;
        for (int a : apples) {
            int t = skip + a;
            skip = Math.max(skip, take);
            take = t;
        }
        most = Math.max(take, skip);
    }

    /** A seeded row of 3-14 trees with 0-12 apples. */
    public static OrchardRows seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x0C4A6L);
        int[] a = new int[3 + rng.nextInt(12)];
        for (int i = 0; i < a.length; i++) {
            a[i] = rng.nextInt(13);
        }
        return new OrchardRows(a);
    }

    public int trees() {
        return apples.length;
    }

    public int apples(int tree) {
        return apples[tree];
    }

    /** The most apples with no two neighbouring trees stripped. */
    public int most() {
        return most;
    }

    public int basket() {
        int s = 0;
        for (int i = 0; i < apples.length; i++) {
            if (stripped[i]) {
                s += apples[i];
            }
        }
        return s;
    }

    public int[] neighbours() {
        return neighbours == null ? null : neighbours.clone();
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    private Outcome guard(String eventId) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        return events.contains(eventId) ? Outcome.DUPLICATE : null;
    }

    /** Strips a tree, or hangs its apples back if already stripped. */
    public Outcome toggle(String eventId, int tree) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (tree < 0 || tree >= apples.length) {
            return Outcome.NOT_THERE;
        }
        events.add(eventId);
        stripped[tree] = !stripped[tree];
        last = null;
        neighbours = null;
        if (stripped[tree]) {
            quest.apply(eventId, "strip", "tree");
            return Outcome.STRIPPED;
        }
        return Outcome.LEFT;
    }

    /** Carries the basket in: NEIGHBOURS if two side-by-side trees are bare, WELL at the most apples, else LIGHT. */
    public Outcome carry(String eventId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        events.add(eventId);
        neighbours = null;
        for (int i = 0; i + 1 < apples.length; i++) {
            if (stripped[i] && stripped[i + 1]) {
                neighbours = new int[] {i, i + 1};
                break;
            }
        }
        if (neighbours != null) {
            last = Outcome.NEIGHBOURS;
        } else {
            last = basket() == most ? Outcome.WELL : Outcome.LIGHT;
        }
        if (last == Outcome.WELL) {
            quest.apply(eventId, "carry", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the basket came in well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperOrchardLines.THANKS;
        }
        return KeeperOrchardLines.line(this);
    }
}
