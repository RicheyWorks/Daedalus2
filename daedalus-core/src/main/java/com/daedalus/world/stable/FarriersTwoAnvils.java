// SPDX-License-Identifier: MIT

package com.daedalus.world.stable;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * G535 Farrier's Two Anvils (Studio horse lane): shoeing jobs have seeded durations and
 * must-finish-first links (a shoe is shaped before it is fitted), and the forge has two identical
 * anvils. {@link #best} finds the earliest moment the last job is done, exactly, with a memoised
 * event search over (jobs done, job still on the other anvil, its time left); at each free anvil it
 * may start any ready job or deliberately wait for the other anvil. {@link #listSchedule} (Graham's
 * habit: never leave an anvil idle, take the lowest-numbered ready job) can finish later. Plain
 * int[] API with predecessor bitmasks, at most 10 jobs, durations at most {@code MAX_TIME}. The
 * algorithm is small and pure so it can be ported to C++ for Unreal.
 */
public final class FarriersTwoAnvils {

    public static final String QUEST_ID = "q_two_anvils";
    public static final int MAX_JOBS = 10;
    public static final int MAX_TIME = 9;
    public static final int INVALID = -1;

    /** A schedule: finish time, start time and anvil (0 or 1) of each job. */
    public record Plan(int makespan, int[] start, int[] anvil) {
        public Plan {
            start = start.clone();
            anvil = anvil.clone();
        }

        @Override
        public int[] start() {
            return start.clone();
        }

        @Override
        public int[] anvil() {
            return anvil.clone();
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Plan p && p.makespan == makespan && Arrays.equals(p.start, start)
                    && Arrays.equals(p.anvil, anvil);
        }

        @Override
        public int hashCode() {
            return 31 * (31 * makespan + Arrays.hashCode(start)) + Arrays.hashCode(anvil);
        }

        @Override
        public String toString() {
            return "Plan[" + makespan + ", start=" + Arrays.toString(start) + ", anvil=" + Arrays.toString(anvil) + "]";
        }
    }

    private FarriersTwoAnvils() { }

    /** Seeded durations in [1, MAX_TIME]. */
    public static int[] durations(long seed, int n) {
        if (n < 0 || n > MAX_JOBS) {
            throw new IllegalArgumentException("bad job count");
        }
        SplittableRandom rnd = new SplittableRandom(seed);
        int[] p = new int[n];
        for (int i = 0; i < n; i++) {
            p[i] = 1 + rnd.nextInt(MAX_TIME);
        }
        return p;
    }

    /** Seeded predecessor masks: job j waits for each earlier job i with probability percent/100. */
    public static int[] links(long seed, int n, int percent) {
        if (n < 0 || n > MAX_JOBS || percent < 0 || percent > 100) {
            throw new IllegalArgumentException("bad links");
        }
        SplittableRandom rnd = new SplittableRandom(seed ^ 0x9E3779B97F4A7C15L);
        int[] pred = new int[n];
        for (int j = 0; j < n; j++) {
            for (int i = 0; i < j; i++) {
                if (rnd.nextInt(100) < percent) {
                    pred[j] |= 1 << i;
                }
            }
        }
        return pred;
    }

    /** Earliest finish of all jobs on two anvils respecting the links. */
    public static Plan best(int[] time, int[] pred) {
        check(time, pred);
        int n = time.length;
        int[] memo = new int[(1 << n) * (n + 1) * (MAX_TIME + 1)];
        Arrays.fill(memo, -1);
        int[] start = new int[n];
        int[] anvil = new int[n];
        int done = 0;
        int run = -1;
        int rem = 0;
        int busy = 0;
        int t = 0;
        int full = (1 << n) - 1;
        int total = solve(time, pred, memo, 0, -1, 0);
        while (done != full) {
            int want = solve(time, pred, memo, done, run, rem);
            int ready = ready(pred, done, run);
            if (run < 0) {
                for (int k = 0; k < n; k++) {
                    if ((ready & (1 << k)) != 0 && solve(time, pred, memo, done, k, time[k]) == want) {
                        start[k] = t;
                        anvil[k] = 0;
                        busy = 0;
                        run = k;
                        rem = time[k];
                        break;
                    }
                }
                continue;
            }
            int free = 1 - busy;
            int pick = -1;
            for (int k = 0; k < n && pick < 0; k++) {
                if ((ready & (1 << k)) != 0 && step(time, pred, memo, done, run, rem, k) == want) {
                    pick = k;
                }
            }
            if (pick < 0) {
                t += rem;
                done |= 1 << run;
                run = -1;
                rem = 0;
                continue;
            }
            start[pick] = t;
            anvil[pick] = free;
            int p = time[pick];
            if (p < rem) {
                t += p;
                done |= 1 << pick;
                rem -= p;
            } else if (p > rem) {
                t += rem;
                done |= 1 << run;
                run = pick;
                busy = free;
                rem = p - rem;
            } else {
                t += rem;
                done |= (1 << run) | (1 << pick);
                run = -1;
                rem = 0;
            }
        }
        return new Plan(total, start, anvil);
    }

    private static int step(int[] time, int[] pred, int[] memo, int done, int run, int rem, int k) {
        int p = time[k];
        if (p < rem) {
            return p + solve(time, pred, memo, done | (1 << k), run, rem - p);
        }
        if (p > rem) {
            return rem + solve(time, pred, memo, done | (1 << run), k, p - rem);
        }
        return rem + solve(time, pred, memo, done | (1 << run) | (1 << k), -1, 0);
    }

    private static int solve(int[] time, int[] pred, int[] memo, int done, int run, int rem) {
        int n = time.length;
        if (done == (1 << n) - 1) {
            return 0;
        }
        int key = (done * (n + 1) + run + 1) * (MAX_TIME + 1) + rem;
        if (memo[key] >= 0) {
            return memo[key];
        }
        int ready = ready(pred, done, run);
        int bestLeft = Integer.MAX_VALUE;
        if (run < 0) {
            for (int k = 0; k < n; k++) {
                if ((ready & (1 << k)) != 0) {
                    bestLeft = Math.min(bestLeft, solve(time, pred, memo, done, k, time[k]));
                }
            }
        } else {
            bestLeft = rem + solve(time, pred, memo, done | (1 << run), -1, 0);
            for (int k = 0; k < n; k++) {
                if ((ready & (1 << k)) != 0) {
                    bestLeft = Math.min(bestLeft, step(time, pred, memo, done, run, rem, k));
                }
            }
        }
        memo[key] = bestLeft;
        return bestLeft;
    }

    private static int ready(int[] pred, int done, int run) {
        int r = 0;
        for (int k = 0; k < pred.length; k++) {
            if ((done & (1 << k)) == 0 && k != run && (pred[k] & done) == pred[k]) {
                r |= 1 << k;
            }
        }
        return r;
    }

    /** Graham list scheduling in job order: a free anvil never idles while some job is ready. */
    public static Plan listSchedule(int[] time, int[] pred) {
        check(time, pred);
        int n = time.length;
        int[] start = new int[n];
        int[] anvil = new int[n];
        int[] finish = new int[n];
        boolean[] started = new boolean[n];
        int[] free = new int[2];
        int left = n;
        int makespan = 0;
        while (left > 0) {
            int a = free[0] <= free[1] ? 0 : 1;
            int t = free[a];
            int pick = -1;
            for (int k = 0; k < n && pick < 0; k++) {
                if (!started[k] && readyAt(pred, started, finish, k, t)) {
                    pick = k;
                }
            }
            if (pick < 0) {
                int next = Integer.MAX_VALUE;
                for (int k = 0; k < n; k++) {
                    if (started[k] && finish[k] > t) {
                        next = Math.min(next, finish[k]);
                    }
                }
                free[a] = next;
                continue;
            }
            started[pick] = true;
            start[pick] = t;
            anvil[pick] = a;
            finish[pick] = t + time[pick];
            free[a] = finish[pick];
            makespan = Math.max(makespan, finish[pick]);
            left--;
        }
        return new Plan(makespan, start, anvil);
    }

    private static boolean readyAt(int[] pred, boolean[] started, int[] finish, int k, int t) {
        for (int i = 0; i < pred.length; i++) {
            if ((pred[k] & (1 << i)) != 0 && (!started[i] || finish[i] > t)) {
                return false;
            }
        }
        return true;
    }

    /** Makespan of a schedule, or INVALID when a link is broken, an anvil overlaps or a field is bad. */
    public static int finish(int[] time, int[] pred, int[] start, int[] anvil) {
        check(time, pred);
        int n = time.length;
        if (start.length != n || anvil.length != n) {
            return INVALID;
        }
        int makespan = 0;
        for (int j = 0; j < n; j++) {
            if (start[j] < 0 || (anvil[j] != 0 && anvil[j] != 1)) {
                return INVALID;
            }
            for (int i = 0; i < n; i++) {
                if ((pred[j] & (1 << i)) != 0 && start[i] + time[i] > start[j]) {
                    return INVALID;
                }
                if (i != j && anvil[i] == anvil[j] && start[i] < start[j] + time[j] && start[j] < start[i] + time[i]) {
                    return INVALID;
                }
            }
            makespan = Math.max(makespan, start[j] + time[j]);
        }
        return makespan;
    }

    /** Quest q_two_anvils: the farrier's schedule is legal and finishes as early as possible. */
    public static boolean quest(int[] time, int[] pred, int[] start, int[] anvil) {
        int got = finish(time, pred, start, anvil);
        return got != INVALID && got == best(time, pred).makespan();
    }

    private static void check(int[] time, int[] pred) {
        if (time.length != pred.length || time.length > MAX_JOBS) {
            throw new IllegalArgumentException("bad jobs");
        }
        for (int j = 0; j < time.length; j++) {
            if (time[j] < 1 || time[j] > MAX_TIME || (pred[j] >>> j) != 0) {
                throw new IllegalArgumentException("bad job " + j + " (links must point to earlier jobs)");
            }
        }
    }
}
