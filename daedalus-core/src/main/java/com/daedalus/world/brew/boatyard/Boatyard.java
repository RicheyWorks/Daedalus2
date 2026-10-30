// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.boatyard;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 42 of the Youtube Master Island story, "The Boatyard" (quest {@code q_boatyard}). Building a boat is a set
 * of jobs, each taking some days and waiting on other jobs. Jobs with nothing to wait on run side by side.
 * {@link #launchDay()} is the critical path: the longest chain of days through a Kahn topological order. Naming that
 * day earns credit; a day too early or too late does not. A yard whose jobs wait on each other in a loop is refused.
 */
public final class Boatyard {
    public static final String QUEST_ID = "q_boatyard";

    public enum Outcome { RIGHT, EARLY, LATE, DUPLICATE, IGNORED }

    private final int[] days;
    private final List<int[]> waits;
    private final int[] finish;
    private final int launchDay;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("plan", "yard", 1),
            new QuestProgress.Step("launch", "right", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** {@code waits} holds pairs {before, after}: job {@code after} starts once {@code before} is finished. */
    public Boatyard(int[] days, List<int[]> waits) {
        if (days == null || days.length == 0) {
            throw new IllegalArgumentException("at least one job");
        }
        int n = days.length;
        for (int d : days) {
            if (d <= 0) {
                throw new IllegalArgumentException("every job takes a day or more");
            }
        }
        this.days = days.clone();
        this.waits = new ArrayList<>();
        List<List<Integer>> next = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            next.add(new ArrayList<>());
        }
        int[] in = new int[n];
        for (int[] w : waits) {
            if (w.length != 2 || w[0] < 0 || w[1] < 0 || w[0] >= n || w[1] >= n || w[0] == w[1]) {
                throw new IllegalArgumentException("no such job");
            }
            this.waits.add(w.clone());
            next.get(w[0]).add(w[1]);
            in[w[1]]++;
        }
        int[] start = new int[n];
        finish = new int[n];
        Deque<Integer> ready = new ArrayDeque<>();
        for (int i = 0; i < n; i++) {
            if (in[i] == 0) {
                ready.add(i);
            }
        }
        int done = 0;
        int end = 0;
        while (!ready.isEmpty()) {
            int j = ready.poll();
            done++;
            finish[j] = start[j] + days[j];
            end = Math.max(end, finish[j]);
            for (int k : next.get(j)) {
                start[k] = Math.max(start[k], finish[j]);
                if (--in[k] == 0) {
                    ready.add(k);
                }
            }
        }
        if (done < n) {
            throw new IllegalArgumentException("the jobs wait on each other in a loop");
        }
        launchDay = end;
    }

    /** A seeded yard of 3-9 jobs, 1-5 days, each pair waiting with chance 1/3 (earlier job first). */
    public static Boatyard seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xB0A7L);
        int n = 3 + rng.nextInt(7);
        int[] d = new int[n];
        for (int i = 0; i < n; i++) {
            d[i] = 1 + rng.nextInt(5);
        }
        List<int[]> w = new ArrayList<>();
        for (int a = 0; a < n; a++) {
            for (int b = a + 1; b < n; b++) {
                if (rng.nextInt(3) == 0) {
                    w.add(new int[] {a, b});
                }
            }
        }
        return new Boatyard(d, w);
    }

    public int jobs() {
        return days.length;
    }

    public int days(int job) {
        return days[job];
    }

    /** The waits as {before, after} pairs (copies). */
    public List<int[]> waits() {
        List<int[]> out = new ArrayList<>();
        for (int[] w : waits) {
            out.add(w.clone());
        }
        return out;
    }

    /** The day job {@code job} is finished at the soonest. */
    public int finish(int job) {
        return finish[job];
    }

    /** The soonest day the boat can launch. */
    public int launchDay() {
        return launchDay;
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

    /** Reads the yard's job board: the quest's first step. */
    public void plan(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "plan", "yard");
        }
    }

    /** Names the launch day: RIGHT earns credit, EARLY and LATE do not. */
    public Outcome launch(String eventId, int day) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (!events.add(eventId)) {
            return Outcome.DUPLICATE;
        }
        named = day;
        last = day == launchDay ? Outcome.RIGHT : day < launchDay ? Outcome.EARLY : Outcome.LATE;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "launch", "right");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the launch day is right. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperYardLines.THANKS;
        }
        return KeeperYardLines.line(this);
    }
}
