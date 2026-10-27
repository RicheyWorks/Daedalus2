// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.wells;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 45 of the Youtube Master Island story, "The Well Pipes" (quest {@code q_well_pipes}). Clay pipes are laid
 * one by one between the island's wells; wells joined by any chain of pipes share water. {@link #groupsAfter(int)} is
 * the number of separate well groups after the first k pipes, by union-find with path halving and union by size.
 * Naming the final count earns credit; a wrong count does not. A pipe between two wells already joined is wasted.
 */
public final class WellPipes {
    public static final String QUEST_ID = "q_well_pipes";

    public enum Outcome { RIGHT, WRONG, DUPLICATE, IGNORED }

    private final int wells;
    private final List<int[]> pipes;
    private final int[] groupsAfter;
    private final int wasted;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("walk", "pipes", 1),
            new QuestProgress.Step("count", "right", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    public WellPipes(int wells, List<int[]> pipes) {
        if (wells <= 0 || pipes == null) {
            throw new IllegalArgumentException("at least one well");
        }
        this.wells = wells;
        this.pipes = new ArrayList<>();
        int[] parent = new int[wells];
        int[] size = new int[wells];
        for (int i = 0; i < wells; i++) {
            parent[i] = i;
            size[i] = 1;
        }
        groupsAfter = new int[pipes.size() + 1];
        int groups = wells;
        int waste = 0;
        groupsAfter[0] = groups;
        for (int k = 0; k < pipes.size(); k++) {
            int[] p = pipes.get(k);
            if (p.length != 2 || p[0] < 0 || p[1] < 0 || p[0] >= wells || p[1] >= wells) {
                throw new IllegalArgumentException("no such well");
            }
            this.pipes.add(p.clone());
            int a = find(parent, p[0]);
            int b = find(parent, p[1]);
            if (a == b) {
                waste++;
            } else {
                if (size[a] < size[b]) {
                    int t = a;
                    a = b;
                    b = t;
                }
                parent[b] = a;
                size[a] += size[b];
                groups--;
            }
            groupsAfter[k + 1] = groups;
        }
        wasted = waste;
    }

    private static int find(int[] parent, int x) {
        while (parent[x] != x) {
            parent[x] = parent[parent[x]];
            x = parent[x];
        }
        return x;
    }

    /** A seeded island of 2-12 wells and 0-14 pipes. */
    public static WellPipes seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x3E11L);
        int n = 2 + rng.nextInt(11);
        int m = rng.nextInt(15);
        List<int[]> p = new ArrayList<>();
        for (int i = 0; i < m; i++) {
            p.add(new int[] {rng.nextInt(n), rng.nextInt(n)});
        }
        return new WellPipes(n, p);
    }

    public int wells() {
        return wells;
    }

    public int pipeCount() {
        return pipes.size();
    }

    /** The pipes in the order laid (copies). */
    public List<int[]> pipes() {
        List<int[]> out = new ArrayList<>();
        for (int[] p : pipes) {
            out.add(p.clone());
        }
        return out;
    }

    /** Separate well groups after the first {@code k} pipes. */
    public int groupsAfter(int k) {
        return groupsAfter[k];
    }

    /** Separate well groups once every pipe is laid. */
    public int groups() {
        return groupsAfter[pipes.size()];
    }

    /** Pipes laid between wells already joined. */
    public int wasted() {
        return wasted;
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

    /** Walks the pipe lines: the quest's first step. */
    public void walk(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "walk", "pipes");
        }
    }

    /** Names how many separate well groups remain: RIGHT earns credit, WRONG does not. */
    public Outcome count(String eventId, int groups) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (!events.add(eventId)) {
            return Outcome.DUPLICATE;
        }
        named = groups;
        last = groups == groups() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "right");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the count is right. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperWellLines.THANKS;
        }
        return KeeperWellLines.line(this);
    }
}
