// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Deque;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Forge Critical Path (contest gap G193): refitting an ark ({@link ArkDrydock}) is a web of forge jobs with durations
 * and "must finish before" links. With unlimited hands the refit lasts as long as its longest chain of jobs.
 *
 * <p>The scheduler is plain: {@code durations[j]} days per job, {@code edges[i] = {a, b}} means a finishes before b
 * starts. {@link #schedule} gives a topological order, earliest and latest starts, slack and one critical path, or
 * reports a cycle. Any project can use it for quest chains or build pipelines.
 */
public final class ForgeCriticalPath {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_forge_critical_path";

    /** How the player's launch-day call went. */
    public enum Grade { ON_TIME, LATE, CYCLE }

    /** A solved schedule. {@code cyclic} is true (and the rest empty) when the links loop. */
    public record Schedule(boolean cyclic, List<Integer> order, List<Integer> earliest, List<Integer> latest,
            List<Integer> critical, int makespan) {

        public Schedule {
            order = List.copyOf(order);
            earliest = List.copyOf(earliest);
            latest = List.copyOf(latest);
            critical = List.copyOf(critical);
        }

        /** Days job {@code j} can slip without delaying the launch. */
        public int slack(int j) {
            return latest.get(j) - earliest.get(j);
        }
    }

    private ForgeCriticalPath() {
    }

    /** A seeded refit: {@code n} jobs of 1..9 days; each pair (a &lt; b) linked with chance {@code linkPct}%. */
    public static int[][] refitEdges(long seed, int n, int linkPct) {
        SplittableRandom r = new SplittableRandom(seed);
        List<int[]> e = new ArrayList<>();
        for (int a = 0; a < n; a++) {
            for (int b = a + 1; b < n; b++) {
                if (r.nextInt(100) < linkPct) {
                    e.add(new int[] {a, b});
                }
            }
        }
        return e.toArray(new int[0][]);
    }

    /** Seeded durations of 1..9 days for {@code n} jobs. */
    public static int[] refitDurations(long seed, int n) {
        SplittableRandom r = new SplittableRandom(seed ^ 0x5DEECE66DL);
        int[] d = new int[n];
        for (int i = 0; i < n; i++) {
            d[i] = 1 + r.nextInt(9);
        }
        return d;
    }

    /** Solves the schedule (Kahn's order, forward and backward passes). */
    public static Schedule schedule(int[] durations, int[][] edges) {
        int n = durations.length;
        List<List<Integer>> out = new ArrayList<>();
        List<List<Integer>> in = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            if (durations[i] < 0) {
                throw new IllegalArgumentException("negative duration at job " + i);
            }
            out.add(new ArrayList<>());
            in.add(new ArrayList<>());
        }
        int[] indeg = new int[n];
        for (int[] e : edges) {
            if (e.length != 2 || e[0] < 0 || e[0] >= n || e[1] < 0 || e[1] >= n) {
                throw new IllegalArgumentException("bad link " + Arrays.toString(e));
            }
            out.get(e[0]).add(e[1]);
            in.get(e[1]).add(e[0]);
            indeg[e[1]]++;
        }
        Deque<Integer> ready = new ArrayDeque<>();
        for (int i = 0; i < n; i++) {
            if (indeg[i] == 0) {
                ready.add(i);
            }
        }
        List<Integer> order = new ArrayList<>();
        while (!ready.isEmpty()) {
            int j = ready.poll();
            order.add(j);
            for (int k : out.get(j)) {
                if (--indeg[k] == 0) {
                    ready.add(k);
                }
            }
        }
        if (order.size() < n) {
            return new Schedule(true, List.of(), List.of(), List.of(), List.of(), -1);
        }
        int[] es = new int[n];
        int makespan = 0;
        for (int j : order) {
            for (int p : in.get(j)) {
                es[j] = Math.max(es[j], es[p] + durations[p]);
            }
            makespan = Math.max(makespan, es[j] + durations[j]);
        }
        int[] ls = new int[n];
        for (int x = n - 1; x >= 0; x--) {
            int j = order.get(x);
            int lf = makespan;
            for (int k : out.get(j)) {
                lf = Math.min(lf, ls[k]);
            }
            ls[j] = lf - durations[j];
        }
        List<Integer> critical = new ArrayList<>();
        int cur = -1;
        for (int j : order) {
            if (in.get(j).isEmpty() && ls[j] == es[j] && (cur < 0)) {
                cur = j;
            }
        }
        while (cur >= 0) {
            critical.add(cur);
            int next = -1;
            for (int k : out.get(cur)) {
                if (ls[k] == es[k] && es[k] == es[cur] + durations[cur] && (next < 0 || k < next)) {
                    next = k;
                }
            }
            cur = next;
        }
        return new Schedule(false, order, box(es), box(ls), critical, makespan);
    }

    private static List<Integer> box(int[] a) {
        List<Integer> l = new ArrayList<>(a.length);
        for (int x : a) {
            l.add(x);
        }
        return l;
    }

    /** ON_TIME if the player's launch day equals the makespan, LATE otherwise, CYCLE if the links loop. */
    public static Grade grade(Schedule s, int guessDay) {
        if (s.cyclic()) {
            return Grade.CYCLE;
        }
        return guessDay == s.makespan() ? Grade.ON_TIME : Grade.LATE;
    }

    /** The Forgemaster's line for a call. */
    public static String forgemasterLine(Schedule s, int guessDay) {
        return switch (grade(s, guessDay)) {
            case ON_TIME -> "Forgemaster: day " + s.makespan() + ". The ark launches on your word.";
            case LATE -> "Forgemaster: you said day " + guessDay + ". The chain says day " + s.makespan() + ".";
            case CYCLE -> "Forgemaster: these jobs wait on each other in a ring. Nothing ever starts.";
        };
    }
}
