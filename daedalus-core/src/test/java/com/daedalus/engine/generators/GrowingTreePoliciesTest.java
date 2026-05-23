// SPDX-License-Identifier: MIT

package com.daedalus.engine.generators;

import com.daedalus.model.Point;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Direct unit tests of {@link GrowingTreePolicies}. Exercises each named factory against
 * synthetic active lists with a fixed-seed {@link Random} so the policy's contract can be
 * pinned independently of the {@link GrowingTreeEngine} loop. End-to-end seed mapping for
 * the registered Growing-Tree generators is covered by
 * {@link com.daedalus.engine.PerfectMazePropertyTest}.
 */
class GrowingTreePoliciesTest {

    /** Helper — build a small active list of distinct grid points. */
    private static List<Point> activeOf(int n) {
        List<Point> list = new ArrayList<>(n);
        for (int i = 0; i < n; i++) {
            list.add(new Point(i / 4, i % 4));   // walks a 4-wide strip
        }
        return list;
    }

    // ---------- stateless picks ----------

    @Test
    void newest_picksTailIndex() {
        GrowingTreePolicy p = GrowingTreePolicies.newest();
        assertThat(p.pickNext(activeOf(1), new Random())).isEqualTo(0);
        assertThat(p.pickNext(activeOf(5), new Random())).isEqualTo(4);
        assertThat(p.pickNext(activeOf(20), new Random())).isEqualTo(19);
    }

    @Test
    void oldest_picksHeadIndex() {
        GrowingTreePolicy p = GrowingTreePolicies.oldest();
        assertThat(p.pickNext(activeOf(1), new Random())).isEqualTo(0);
        assertThat(p.pickNext(activeOf(5), new Random())).isEqualTo(0);
        assertThat(p.pickNext(activeOf(20), new Random())).isEqualTo(0);
    }

    @Test
    void random_returnsIndexInRange_andConsultsRng() {
        GrowingTreePolicy p = GrowingTreePolicies.random();
        Random rng = new Random(2026_05_07L);
        for (int trial = 0; trial < 100; trial++) {
            int idx = p.pickNext(activeOf(7), rng);
            assertThat(idx).isBetween(0, 6);
        }
        // Reproducibility: same seed → same sequence.
        Random a = new Random(99L);
        Random b = new Random(99L);
        for (int trial = 0; trial < 20; trial++) {
            assertThat(p.pickNext(activeOf(11), a)).isEqualTo(p.pickNext(activeOf(11), b));
        }
    }

    @Test
    void middle_picksFloorOfHalfSize() {
        GrowingTreePolicy p = GrowingTreePolicies.middle();
        assertThat(p.pickNext(activeOf(1), new Random())).isEqualTo(0);
        assertThat(p.pickNext(activeOf(2), new Random())).isEqualTo(1);   // floor(2/2)
        assertThat(p.pickNext(activeOf(5), new Random())).isEqualTo(2);   // floor(5/2)
        assertThat(p.pickNext(activeOf(10), new Random())).isEqualTo(5);
    }

    // ---------- mixed ----------

    @Test
    void mixed_atOne_alwaysPicksNewest() {
        GrowingTreePolicy p = GrowingTreePolicies.mixed(1.0);
        Random rng = new Random(1L);
        for (int trial = 0; trial < 50; trial++) {
            assertThat(p.pickNext(activeOf(8), rng)).isEqualTo(7);
        }
    }

    @Test
    void mixed_atZero_isEquivalentToRandom() {
        // Both should consume rng identically (one nextInt per call) and produce the same
        // sequence — that's what "mixed(0) === random()" means at the contract level.
        GrowingTreePolicy mixed = GrowingTreePolicies.mixed(0.0);
        GrowingTreePolicy plainRandom = GrowingTreePolicies.random();

        Random a = new Random(7L);
        Random b = new Random(7L);
        for (int trial = 0; trial < 50; trial++) {
            assertThat(mixed.pickNext(activeOf(6), a))
                    .isEqualTo(plainRandom.pickNext(activeOf(6), b));
        }
    }

    @Test
    void mixed_atHalf_useNextBoolean_soOnlyOneRngBitConsumedPerCall() {
        // The 50/50 case is a special-cased fast path that uses rng.nextBoolean(). This
        // matters for seed reproducibility — GrowingTreeGenerator's pre-refactor lambda
        // also used nextBoolean, so any seed pinned against it must still resolve.
        GrowingTreePolicy p = GrowingTreePolicies.mixed(0.5);

        // Seed where nextBoolean() yields true on the first call → should pick newest.
        Random pinTrue = new Random(0L);
        // (Sanity-check the assumption.)
        Random probe = new Random(0L);
        boolean firstBit = probe.nextBoolean();
        int expected = firstBit ? 9 : new Random(0L).nextInt(10);
        // We want a seed where firstBit is true. If 0L doesn't give true, find one.
        if (!firstBit) {
            long s = 1L;
            while (!new Random(s).nextBoolean()) s++;
            pinTrue = new Random(s);
            firstBit = true;
            expected = 9;
        }
        assertThat(p.pickNext(activeOf(10), pinTrue)).isEqualTo(expected);
    }

    @Test
    void mixed_rejectsOutOfRangeProbability() {
        assertThatThrownBy(() -> GrowingTreePolicies.mixed(-0.0001))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("[0.0, 1.0]");
        assertThatThrownBy(() -> GrowingTreePolicies.mixed(1.0001))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> GrowingTreePolicies.mixed(Double.NaN))
                .isInstanceOf(IllegalArgumentException.class);
    }

    // ---------- quadratic norm ----------

    @Test
    void quadraticNorm_picksMaxRowSquaredPlusColSquared() {
        GrowingTreePolicy p = GrowingTreePolicies.quadraticNorm();

        // Hand-crafted list: index 2 has the largest norm (3² + 3² = 18).
        List<Point> active = List.of(
                new Point(0, 0),   // norm 0
                new Point(1, 2),   // norm 5
                new Point(3, 3),   // norm 18  <- winner
                new Point(2, 2),   // norm 8
                new Point(0, 4)    // norm 16
        );
        assertThat(p.pickNext(active, new Random(0L))).isEqualTo(2);
    }

    @Test
    void quadraticNorm_breaksTiesWithRng_stableUnderSameSeed() {
        GrowingTreePolicy p = GrowingTreePolicies.quadraticNorm();

        // All four points share the maximum norm of 5 (1²+2² and 2²+1²).
        List<Point> ties = List.of(
                new Point(1, 2),
                new Point(2, 1),
                new Point(1, 2),
                new Point(2, 1)
        );

        // Same seed twice → identical answer (tie-break is rng-deterministic).
        int first = p.pickNext(ties, new Random(123L));
        int second = p.pickNext(ties, new Random(123L));
        assertThat(first).isEqualTo(second);
        assertThat(first).isBetween(0, 3);
    }

    // ---------- newest with norm jump (Lightning's policy) ----------

    @Test
    void newestWithNormJump_atZero_isEquivalentToNewest() {
        // The 0.0 endpoint returns the newest() singleton directly — no nextDouble()
        // consumed per call. Verify the consumption pattern matches plain newest().
        GrowingTreePolicy hybrid = GrowingTreePolicies.newestWithNormJump(0.0);
        GrowingTreePolicy plainNewest = GrowingTreePolicies.newest();

        Random a = new Random(11L);
        Random b = new Random(11L);
        for (int trial = 0; trial < 40; trial++) {
            assertThat(hybrid.pickNext(activeOf(8), a))
                    .isEqualTo(plainNewest.pickNext(activeOf(8), b));
        }
        // Both should also still be in lockstep on the rng state — sanity-check by
        // pulling one more int from each and asserting they match.
        assertThat(a.nextInt()).isEqualTo(b.nextInt());
    }

    @Test
    void newestWithNormJump_atOne_isEquivalentToQuadraticNorm() {
        GrowingTreePolicy hybrid = GrowingTreePolicies.newestWithNormJump(1.0);
        GrowingTreePolicy plainNorm = GrowingTreePolicies.quadraticNorm();

        List<Point> active = List.of(
                new Point(0, 0),
                new Point(1, 2),
                new Point(3, 3),
                new Point(2, 2),
                new Point(0, 4)
        );
        // Same seed → same answer (the quadratic-norm tie-break is rng-deterministic
        // and at pJump=1.0 we should not consume an extra nextDouble first).
        Random a = new Random(0L);
        Random b = new Random(0L);
        assertThat(hybrid.pickNext(active, a)).isEqualTo(plainNorm.pickNext(active, b));
        assertThat(a.nextInt()).isEqualTo(b.nextInt());
    }

    @Test
    void newestWithNormJump_isSeedDeterministic() {
        GrowingTreePolicy p = GrowingTreePolicies.newestWithNormJump(0.25);

        // Use a Lightning-shaped active list — points include both tail-end newest
        // candidates and a high-norm corner — so the choice can flip per branch.
        List<Point> active = List.of(
                new Point(0, 0),
                new Point(1, 1),
                new Point(5, 5),
                new Point(2, 7),
                new Point(8, 3)
        );

        Random a = new Random(2026_05_11L);
        Random b = new Random(2026_05_11L);
        for (int trial = 0; trial < 50; trial++) {
            int aPick = p.pickNext(active, a);
            int bPick = p.pickNext(active, b);
            assertThat(aPick).isEqualTo(bPick);
            assertThat(aPick).isBetween(0, active.size() - 1);
        }
    }

    @Test
    void newestWithNormJump_takesBothBranches_underReasonableSampleCount() {
        // At pJump = 0.5, a fair sample should hit both branches. The newest branch
        // always returns the tail index; the jump branch will (in the hand-crafted
        // active list below) almost always return the high-norm index. Confirm both
        // outcomes appear so the composition is exercising both component policies.
        GrowingTreePolicy p = GrowingTreePolicies.newestWithNormJump(0.5);

        // High-norm winner at index 2; tail is at index 3.
        List<Point> active = List.of(
                new Point(0, 0),
                new Point(1, 1),
                new Point(9, 9),   // norm 162 — runaway winner
                new Point(0, 2)    // tail
        );

        Random rng = new Random(7L);
        boolean sawTail = false;
        boolean sawJump = false;
        for (int trial = 0; trial < 200 && !(sawTail && sawJump); trial++) {
            int pick = p.pickNext(active, rng);
            if (pick == 3) sawTail = true;
            else if (pick == 2) sawJump = true;
        }
        assertThat(sawTail).as("newest branch should fire over 200 trials at pJump=0.5").isTrue();
        assertThat(sawJump).as("jump branch should fire over 200 trials at pJump=0.5").isTrue();
    }

    @Test
    void newestWithNormJump_rejectsOutOfRangeProbability() {
        assertThatThrownBy(() -> GrowingTreePolicies.newestWithNormJump(-0.0001))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("[0.0, 1.0]");
        assertThatThrownBy(() -> GrowingTreePolicies.newestWithNormJump(1.0001))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> GrowingTreePolicies.newestWithNormJump(Double.NaN))
                .isInstanceOf(IllegalArgumentException.class);
    }

    // ---------- turing machine ----------

    @Test
    void turingMachine_cyclesNewestOldestRandomMiddle_fourCallsReturnExpectedShape() {
        GrowingTreePolicy p = GrowingTreePolicies.turingMachine();
        List<Point> active = activeOf(8);
        Random rng = new Random(2026L);

        // State 0 → newest (size − 1)
        assertThat(p.pickNext(active, rng)).isEqualTo(7);
        // State 1 → oldest (0)
        assertThat(p.pickNext(active, rng)).isEqualTo(0);
        // State 2 → random — just verify it's in range, value depends on rng
        int randomIdx = p.pickNext(active, rng);
        assertThat(randomIdx).isBetween(0, 7);
        // State 3 → middle (size / 2 = 4)
        assertThat(p.pickNext(active, rng)).isEqualTo(4);
        // Wraps to state 0 → newest again
        assertThat(p.pickNext(active, rng)).isEqualTo(7);
    }

    @Test
    void turingMachine_returnsFreshInstancePerCall_soStateNeverLeaks() {
        // Two independent generations must each start at state 0 (newest pick). If the
        // factory cached a singleton, the second call's first pick would be at state 1
        // (oldest, returning 0).
        GrowingTreePolicy first = GrowingTreePolicies.turingMachine();
        GrowingTreePolicy second = GrowingTreePolicies.turingMachine();

        List<Point> active = activeOf(5);
        Random rng = new Random();
        assertThat(first.pickNext(active, rng)).isEqualTo(4);   // state 0 — newest
        assertThat(second.pickNext(active, rng)).isEqualTo(4);  // state 0 — newest, independently
    }
}
