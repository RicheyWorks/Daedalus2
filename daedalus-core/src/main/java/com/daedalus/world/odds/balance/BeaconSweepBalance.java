// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import com.daedalus.world.odds.OddsRng;
import java.util.ArrayList;
import java.util.List;

/**
 * Beacon Sweep (DaedalusDesktopBeaconSweepCore.h on main), a minesweeper, re-played cell by cell. Source constants:
 * option 0 is 9x9 with 10 mines, option 1 is 16x16 with 40, option 2 is 30x16 with 99; mapped to easy, normal, hard.
 * Mines are planted on the first reveal, never in that cell's 3x3 neighbourhood (a partial Fisher-Yates over the other
 * cells, as in the source); revealing a zero floods its neighbours; opening a mine loses; opening every safe cell
 * wins. Score is 1000 on a win, else the safe cells opened. A size whose mines do not fit outside the 3x3 cannot be
 * planted and counts as a loss with score 0 (tuner grid only).
 *
 * <p>Player model (careful logician, no flag mistakes): opens the centre first, then repeatedly applies the two local
 * rules (a number with all its mines flagged opens the rest; a number whose covered cells equal its missing mines
 * flags them all) and the subset rule over pairs of numbers. When nothing is certain it guesses the covered cell with
 * the lowest local risk (the highest missing/covered ratio among its numbered neighbours, or the global density for a
 * cell with none), ties broken uniformly at random.
 */
public final class BeaconSweepBalance implements BalanceGame, TunableGame {
    static final List<String> NAMES = List.of("easy", "normal", "hard");
    /** {width, height, mines} for options 0, 1, 2. */
    private static final int[][] CONFIG = {{9, 9, 10}, {16, 16, 40}, {30, 16, 99}};
    static final int WIN_POINTS = 1000;

    @Override
    public String id() {
        return "beacon_sweep";
    }

    @Override
    public List<String> difficulties() {
        return NAMES;
    }

    @Override
    public boolean supports(String difficulty) {
        return NAMES.contains(difficulty);
    }

    @Override
    public SessionOutcome play(String difficulty, OddsRng rng) {
        if (!supports(difficulty)) {
            throw new IllegalArgumentException("Beacon Sweep ships no '" + difficulty + "' board");
        }
        return playConfig(CONFIG[NAMES.indexOf(difficulty)], rng);
    }

    @Override
    public List<Knob> knobs() {
        return List.of(new Knob("width", 9, 30, 7), new Knob("height", 9, 16, 7), new Knob("mines", 5, 100, 5));
    }

    @Override
    public int[] shipped(String difficulty) {
        int i = NAMES.indexOf(difficulty);
        return i < 0 ? null : CONFIG[i].clone();
    }

    @Override
    public SessionOutcome play(int[] knobs, OddsRng rng) {
        return playConfig(knobs, rng);
    }

    /** Plays one board with explicit {width, height, mines}. */
    SessionOutcome playConfig(int[] cfg, OddsRng rng) {
        Board b = new Board(cfg[0], cfg[1], cfg[2]);
        int first = (b.h / 2) * b.w + b.w / 2;
        if (!b.plant(first, rng)) {
            return new SessionOutcome(false, 0);
        }
        b.reveal(first);
        while (!b.lost && !b.won()) {
            if (!b.deduce()) {
                b.reveal(b.guess(rng));
            }
        }
        return new SessionOutcome(b.won(), b.won() ? WIN_POINTS : b.openSafe);
    }

    /** The board and the solver; package-private for rule tests. */
    static final class Board {
        final int w;
        final int h;
        final int mines;
        final boolean[] mine;
        final boolean[] open;
        final boolean[] flag;
        final int[] near;
        int openSafe;
        boolean lost;

        Board(int w, int h, int mines) {
            this.w = w;
            this.h = h;
            this.mines = mines;
            mine = new boolean[w * h];
            open = new boolean[w * h];
            flag = new boolean[w * h];
            near = new int[w * h];
        }

        List<Integer> neighbours(int i) {
            List<Integer> out = new ArrayList<>(8);
            int c = i % w;
            int r = i / w;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    int cc = c + dx;
                    int rr = r + dy;
                    if ((dx != 0 || dy != 0) && cc >= 0 && cc < w && rr >= 0 && rr < h) {
                        out.add(rr * w + cc);
                    }
                }
            }
            return out;
        }

        /** Source Plant: candidates outside the safe 3x3, partial Fisher-Yates. False if the mines do not fit. */
        boolean plant(int safe, OddsRng rng) {
            List<Integer> cand = new ArrayList<>();
            for (int i = 0; i < w * h; i++) {
                if (Math.abs(i % w - safe % w) > 1 || Math.abs(i / w - safe / w) > 1) {
                    cand.add(i);
                }
            }
            if (mines > cand.size()) {
                return false;
            }
            for (int i = 0; i < mines; i++) {
                int j = i + (int) (rng.nextDouble() * (cand.size() - i));
                Integer t = cand.get(i);
                cand.set(i, cand.get(j));
                cand.set(j, t);
                mine[cand.get(i)] = true;
            }
            for (int i = 0; i < w * h; i++) {
                for (int j : neighbours(i)) {
                    if (mine[j]) {
                        near[i]++;
                    }
                }
            }
            return true;
        }

        void reveal(int start) {
            if (lost || open[start] || flag[start]) {
                return;
            }
            List<Integer> pending = new ArrayList<>(List.of(start));
            while (!pending.isEmpty()) {
                int j = pending.remove(pending.size() - 1);
                if (open[j] || flag[j]) {
                    continue;
                }
                open[j] = true;
                if (mine[j]) {
                    lost = true;
                    return;
                }
                openSafe++;
                if (near[j] == 0) {
                    for (int k : neighbours(j)) {
                        if (!open[k] && !flag[k]) {
                            pending.add(k);
                        }
                    }
                }
            }
        }

        boolean won() {
            return !lost && openSafe == w * h - mines;
        }

        private List<Integer> covered(int i) {
            List<Integer> u = new ArrayList<>();
            for (int k : neighbours(i)) {
                if (!open[k] && !flag[k]) {
                    u.add(k);
                }
            }
            return u;
        }

        private int missing(int i) {
            int f = 0;
            for (int k : neighbours(i)) {
                if (flag[k]) {
                    f++;
                }
            }
            return near[i] - f;
        }

        /** One pass of the certain rules; true if anything was opened or flagged. */
        boolean deduce() {
            List<Integer> frontier = new ArrayList<>();
            for (int i = 0; i < w * h; i++) {
                if (open[i] && !mine[i] && near[i] > 0 && !covered(i).isEmpty()) {
                    frontier.add(i);
                }
            }
            for (int i : frontier) {
                List<Integer> u = covered(i);
                int m = missing(i);
                if (m == 0) {
                    for (int k : u) {
                        reveal(k);
                    }
                    return true;
                }
                if (m == u.size()) {
                    for (int k : u) {
                        flag[k] = true;
                    }
                    return true;
                }
            }
            for (int a : frontier) {
                List<Integer> ua = covered(a);
                for (int bIdx : frontier) {
                    if (a == bIdx) {
                        continue;
                    }
                    List<Integer> ub = covered(bIdx);
                    if (ub.size() <= ua.size() || !ub.containsAll(ua)) {
                        continue;
                    }
                    List<Integer> rest = new ArrayList<>(ub);
                    rest.removeAll(ua);
                    int diff = missing(bIdx) - missing(a);
                    if (diff == 0) {
                        for (int k : rest) {
                            reveal(k);
                        }
                        return true;
                    }
                    if (diff == rest.size()) {
                        for (int k : rest) {
                            flag[k] = true;
                        }
                        return true;
                    }
                }
            }
            return false;
        }

        /** Lowest-risk covered cell, ties uniform. */
        int guess(OddsRng rng) {
            int coveredCount = 0;
            int flags = 0;
            for (int i = 0; i < w * h; i++) {
                if (flag[i]) {
                    flags++;
                } else if (!open[i]) {
                    coveredCount++;
                }
            }
            double density = coveredCount == 0 ? 1 : (mines - flags) / (double) coveredCount;
            double best = Double.MAX_VALUE;
            List<Integer> ties = new ArrayList<>();
            for (int i = 0; i < w * h; i++) {
                if (open[i] || flag[i]) {
                    continue;
                }
                double risk = -1;
                for (int k : neighbours(i)) {
                    if (open[k] && near[k] > 0) {
                        risk = Math.max(risk, missing(k) / (double) covered(k).size());
                    }
                }
                if (risk < 0) {
                    risk = density;
                }
                if (risk < best - 1e-12) {
                    best = risk;
                    ties.clear();
                    ties.add(i);
                } else if (Math.abs(risk - best) <= 1e-12) {
                    ties.add(i);
                }
            }
            return ties.get((int) (rng.nextDouble() * ties.size()));
        }
    }
}
