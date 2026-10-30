// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.elder;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 77 of the Youtube Master Island story, "The Quiet Elder" (quest {@code q_quiet_elder}). Islanders 0..n-1 and
 * who knows whom; {@link #elder()} is the islander every other islander knows who knows none of them, found by the
 * celebrity elimination (one pass of "does a know b?" questions rules out one islander each, then one check), or
 * {@link #NONE}. Naming the elder earns credit; a WRONG name or a gathering with NO_ELDER earns none.
 */
public final class QuietElder {
    public static final String QUEST_ID = "q_quiet_elder";
    /** No islander is known by all and knows none. */
    public static final int NONE = -1;

    public enum Outcome { FOUND, WRONG, NO_ELDER, MALFORMED, DUPLICATE, IGNORED }

    private final boolean[][] knows;
    private final int elder;
    private int questions;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("gather", "islanders", 1),
            new QuestProgress.Step("name", "elder", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = NONE;
    private Outcome last;

    /** knows.get(a) lists the islanders a knows (never a itself). */
    public QuietElder(List<List<Integer>> knows) {
        if (knows == null || knows.isEmpty()) {
            throw new IllegalArgumentException("at least one islander");
        }
        int n = knows.size();
        this.knows = new boolean[n][n];
        for (int a = 0; a < n; a++) {
            for (Integer b : knows.get(a)) {
                if (b == null || b < 0 || b >= n || b == a) {
                    throw new IllegalArgumentException("an islander knows other real islanders");
                }
                this.knows[a][b] = true;
            }
        }
        int cand = 0;
        for (int i = 1; i < n; i++) {
            if (ask(cand, i)) {
                cand = i;
            }
        }
        boolean ok = true;
        for (int i = 0; i < n && ok; i++) {
            if (i != cand && (ask(cand, i) || !ask(i, cand))) {
                ok = false;
            }
        }
        elder = ok ? cand : NONE;
    }

    private boolean ask(int a, int b) {
        questions++;
        return knows[a][b];
    }

    /** Whether a knows b. */
    public boolean knows(int a, int b) {
        return knows[a][b];
    }

    /** "Does a know b?" questions the elimination asked (at most 3(n-1)). */
    public int questions() {
        return questions;
    }

    /** A seeded gathering of 1-6 islanders; often one is planted as the elder. */
    public static QuietElder seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xE1DE5L);
        int n = 1 + rng.nextInt(6);
        int planted = rng.nextInt(2) == 0 ? rng.nextInt(n) : NONE;
        List<List<Integer>> k = new ArrayList<>();
        for (int a = 0; a < n; a++) {
            List<Integer> row = new ArrayList<>();
            for (int b = 0; b < n; b++) {
                if (a == b || a == planted) {
                    continue;
                }
                if (b == planted ? rng.nextInt(6) != 0 : rng.nextInt(3) == 0) {
                    row.add(b);
                }
            }
            k.add(row);
        }
        return new QuietElder(k);
    }

    public int islanders() {
        return knows.length;
    }

    /** The elder, or {@link #NONE}. */
    public int elder() {
        return elder;
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

    /** Gathers the islanders: the quest's first step. */
    public void gather(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "gather", "islanders");
        }
    }

    /** Names the elder: FOUND, WRONG, NO_ELDER or MALFORMED. */
    public Outcome name(String eventId, int who) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (elder == NONE) {
            last = Outcome.NO_ELDER;
            return last;
        }
        if (who < 0 || who >= knows.length) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = who;
        last = who == elder ? Outcome.FOUND : Outcome.WRONG;
        if (last == Outcome.FOUND) {
            quest.apply(eventId, "name", "elder");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the elder is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperQuietElder.THANKS;
        }
        return KeeperQuietElder.line(this);
    }
}
