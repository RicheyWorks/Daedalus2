// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.model.Point;

import java.util.List;
import java.util.Random;

/**
 * Named, reusable {@link GrowingTreePolicy} factories. Each Growing-Tree generator in this
 * package picks one of these (or composes them) instead of inlining a lambda — keeps the
 * "the policy <em>is</em> the algorithm" abstraction visible at every call site, and lets
 * the policies themselves be unit-tested without spinning up the engine.
 *
 * <p>Stateless policies are returned as singletons (lambdas) where it's safe to share an
 * instance across generations; stateful policies (i.e. {@link #turingMachine()}) return a
 * fresh object per call, since the engine constructs nothing per-generation beyond what we
 * hand it and a state-machine policy must not leak state across runs.
 *
 * <p>Reproducibility note: every randomized policy here consults the {@link Random} the
 * engine threads through, so a {@code seed → maze} mapping is fully determined by
 * {@code (rows, cols, seed, policy)}. Don't introduce {@code Math.random()} or
 * {@code ThreadLocalRandom} into a policy or the engine's seed contract breaks.
 *
 * @since 1.0
 */
public final class GrowingTreePolicies {

    private GrowingTreePolicies() {}

    // ---------- stateless picks ----------

    /** Always pick the newest cell on the active list (tail). Recovers Recursive-Backtracker behavior. */
    public static GrowingTreePolicy newest() {
        return (active, rng) -> active.size() - 1;
    }

    /** Always pick the oldest cell on the active list (head). BFS-like, produces wide / wave growth. */
    public static GrowingTreePolicy oldest() {
        return (active, rng) -> 0;
    }

    /** Always pick a uniformly random cell from the active list. Behaves like a flavor of Prim's. */
    public static GrowingTreePolicy random() {
        return (active, rng) -> rng.nextInt(active.size());
    }

    /** Always pick the middle of the active list. Niche — used as one phase of the Turing state-machine. */
    public static GrowingTreePolicy middle() {
        return (active, rng) -> active.size() / 2;
    }

    /**
     * Pick newest with probability {@code pNewest}, otherwise pick a uniformly random cell.
     * The textured 50/50 default is what {@code GrowingTreeGenerator} uses; values closer to
     * {@code 1.0} feel like a backtracker, values closer to {@code 0.0} feel like Prim's.
     *
     * <p>Implementation note: the 50/50 case is special-cased to {@code rng.nextBoolean()} so
     * that it consumes exactly one bit of {@link Random} state per call — matches the
     * pre-refactor lambda byte-for-byte, preserving seed mapping for the existing
     * {@code GrowingTreeGenerator}. Other probabilities use {@code rng.nextDouble()}, which
     * has a different consumption pattern; pinning a non-0.5 mixed seed is a fresh contract.
     *
     * @param pNewest probability of picking the newest cell, in {@code [0.0, 1.0]}
     * @throws IllegalArgumentException if {@code pNewest} is NaN or out of range
     */
    public static GrowingTreePolicy mixed(double pNewest) {
        if (!(pNewest >= 0.0 && pNewest <= 1.0)) {  // !(>=0 && <=1) catches NaN too
            throw new IllegalArgumentException("pNewest must be in [0.0, 1.0], got " + pNewest);
        }
        if (pNewest == 0.5) {
            return (active, rng) -> rng.nextBoolean() ? active.size() - 1 : rng.nextInt(active.size());
        }
        if (pNewest == 1.0) return newest();
        if (pNewest == 0.0) return random();
        // Capture pNewest in the closure; can't switch to nextBoolean for arbitrary p.
        return (active, rng) -> rng.nextDouble() < pNewest
                ? active.size() - 1
                : rng.nextInt(active.size());
    }

    /**
     * Pick the active cell with the largest quadratic norm {@code r² + c²}, breaking ties
     * uniformly at random. Used by {@link GaussGenerator}. The tie-break consults
     * {@code rng}, so the policy stays seed-deterministic.
     */
    public static GrowingTreePolicy quadraticNorm() {
        return (active, rng) -> {
            int idx = 0;
            long bestScore = Long.MIN_VALUE;
            for (int i = 0; i < active.size(); i++) {
                Point p = active.get(i);
                long score = (long) p.row() * p.row() + (long) p.col() * p.col();
                if (score > bestScore || (score == bestScore && rng.nextBoolean())) {
                    bestScore = score;
                    idx = i;
                }
            }
            return idx;
        };
    }

    /**
     * Mostly pick the newest cell, occasionally jump to the active cell with the largest
     * quadratic norm. The "spike" rate gives the Growing-Tree loop a Recursive-Backtracker
     * baseline (long carved corridors) punctuated by sharp forks toward the far corner —
     * visually evocative of a lightning bolt with branches, which is exactly what
     * {@link LightningGenerator} uses to restore its distinct identity after the
     * 2026-05-07 Growing-Tree unification collapsed it onto Gauss.
     *
     * <p>Edge cases: {@code pJump == 0.0} returns {@link #newest()} directly,
     * {@code pJump == 1.0} returns {@link #quadraticNorm()} directly. Both endpoints skip
     * the per-call {@code nextDouble()} that the mixed regime consumes, so the seed →
     * maze mapping at the endpoints matches the underlying policy byte-for-byte.
     *
     * <p>Random consumption (mixed regime): one {@code rng.nextDouble()} per call to
     * decide jump vs. newest. The newest branch consumes no further bits; the jump branch
     * delegates to {@link #quadraticNorm()}, which consults {@code rng.nextBoolean()} on
     * each tie encountered while scanning the active list.
     *
     * @param pJump probability of taking the quadratic-norm spike, in {@code [0.0, 1.0]}
     * @throws IllegalArgumentException if {@code pJump} is NaN or out of range
     */
    public static GrowingTreePolicy newestWithNormJump(double pJump) {
        if (!(pJump >= 0.0 && pJump <= 1.0)) {  // !(>=0 && <=1) catches NaN too
            throw new IllegalArgumentException("pJump must be in [0.0, 1.0], got " + pJump);
        }
        if (pJump == 0.0) return newest();
        if (pJump == 1.0) return quadraticNorm();
        // Capture pJump in the closure. Both component policies are stateless singletons,
        // so the composition is safe to share across generations.
        final GrowingTreePolicy newest = newest();
        final GrowingTreePolicy jump = quadraticNorm();
        return (active, rng) -> rng.nextDouble() < pJump
                ? jump.pickNext(active, rng)
                : newest.pickNext(active, rng);
    }

    // ---------- stateful ----------

    /**
     * Four-state finite machine that cycles through {@link #newest()}, {@link #oldest()},
     * {@link #random()}, and {@link #middle()}, advancing one step per {@code pickNext}
     * call. Returns a <b>fresh instance</b> on every invocation — necessary because the
     * state must not leak across generations.
     */
    public static GrowingTreePolicy turingMachine() {
        return new TuringMachinePolicy();
    }

    /** Implementation of {@link #turingMachine()} — package-private so tests can pin its state. */
    static final class TuringMachinePolicy implements GrowingTreePolicy {

        /** Cycles 0 → 1 → 2 → 3 → 0 …, advancing on every call. */
        private int state = 0;

        @Override
        public int pickNext(List<Point> active, Random rng) {
            int idx = switch (state) {
                case 0 -> active.size() - 1;          // newest (backtracker style)
                case 1 -> 0;                          // oldest (BFS-like)
                case 2 -> rng.nextInt(active.size()); // pure random (Prim-like)
                default -> active.size() / 2;         // middle — chaotic shift
            };
            state = (state + 1) % 4;
            return idx;
        }

        /** For tests only — observe the state without advancing it. */
        int state() {
            return state;
        }
    }
}
