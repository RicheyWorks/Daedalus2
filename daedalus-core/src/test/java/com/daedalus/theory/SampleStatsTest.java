// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

/**
 * {@link SampleStats}. The values here are computed by hand rather than copied from the
 * implementation's own output — a statistics class checked against itself proves only that it is
 * consistent, which is exactly the failure mode that makes a wrong interval look authoritative.
 */
class SampleStatsTest {

    @Test
    void meanAndSpreadMatchHandComputedValues() {
        // {2,4,4,4,5,5,7,9}: mean 5, sample sd (n-1 denominator) = sqrt(32/7) = 2.1381
        double[] values = {2, 4, 4, 4, 5, 5, 7, 9};

        SampleStats.Summary s = SampleStats.summarise(values);

        assertThat(s.n()).isEqualTo(8);
        assertThat(s.mean()).isEqualTo(5.0);
        assertThat(s.sd()).isCloseTo(2.1381, within(1e-4));
        assertThat(s.median()).isEqualTo(4.5);          // (4 + 5) / 2
        assertThat(s.cv()).isCloseTo(42.76, within(0.01));
    }

    @Test
    void theIntervalUsesStudentT_notTheNormalQuantile() {
        // n = 8 -> df 7 -> t = 2.365, not 1.96. Half-width = 2.365 * 2.1381 / sqrt(8) = 1.7876.
        // Using 1.96 would give 1.4816 — a 21% narrower interval, which is precisely the error
        // that turns "no measurable difference" into a confident claim.
        double[] values = {2, 4, 4, 4, 5, 5, 7, 9};

        SampleStats.Summary s = SampleStats.summarise(values);

        assertThat(s.low()).isCloseTo(5.0 - 1.7876, within(1e-3));
        assertThat(s.high()).isCloseTo(5.0 + 1.7876, within(1e-3));
        assertThat(s.high() - s.mean())
                .as("must be wider than the normal-quantile half-width of 1.4816")
                .isGreaterThan(1.6);
    }

    @Test
    void aConstantSampleHasNoSpreadAndNoInterval() {
        // Three solvers in this project explore every cell every time. That must come out as a
        // zero-width interval rather than a division by zero or a NaN leaking into JSON.
        SampleStats.Summary s = SampleStats.summarise(new double[] {441, 441, 441, 441});

        assertThat(s.sd()).isZero();
        assertThat(s.cv()).isZero();
        assertThat(s.low()).isEqualTo(441.0);
        assertThat(s.high()).isEqualTo(441.0);
        assertThat(s.skewed()).isFalse();
    }

    @Test
    void skewIsFlaggedWhenTheMeanStopsDescribingTheSample() {
        // One huge outlier drags the mean far off the median — the shape of IDA*'s work
        // distribution, whose measured coefficient of variation exceeded 130%.
        SampleStats.Summary skewed = SampleStats.summarise(new double[] {10, 11, 12, 13, 900});
        SampleStats.Summary even = SampleStats.summarise(new double[] {10, 11, 12, 13, 14});

        assertThat(skewed.skewed()).isTrue();
        assertThat(skewed.mean()).isGreaterThan(skewed.median());
        assertThat(even.skewed()).isFalse();
    }

    @Test
    void aPairedDifferenceThatSpansZeroIsNotDistinguishable() {
        double[] a = {10, 12, 11, 13, 12, 11};
        double[] b = {11, 11, 12, 12, 13, 10};   // differences: -1, +1, -1, +1, -1, +1

        SampleStats.Difference d = SampleStats.comparePaired(a, b);

        assertThat(d.meanDifference()).isZero();
        assertThat(d.low()).isNegative();
        assertThat(d.high()).isPositive();
        assertThat(d.distinguishable())
                .as("a difference whose interval contains zero is not a finding")
                .isFalse();
    }

    @Test
    void aConsistentDifferenceIsDistinguishableEvenWhenSmall() {
        // Every pair differs by exactly 2. Tiny, but never once ambiguous, so the interval
        // excludes zero — small and certain is a real result; large and noisy is not.
        double[] a = {100, 213, 57, 400, 12, 88};
        double[] b = {98, 211, 55, 398, 10, 86};

        SampleStats.Difference d = SampleStats.comparePaired(a, b);

        assertThat(d.meanDifference()).isEqualTo(2.0);
        assertThat(d.distinguishable()).isTrue();
        assertThat(d.low()).isEqualTo(2.0);
        assertThat(d.high()).isEqualTo(2.0);
    }

    @Test
    void pairingBeatsIgnoringThePairingWhenBothSeriesMoveTogether() {
        // Both series swing hugely from item to item but stay 5 apart. Paired, that is a certain
        // difference of 5; treating the samples as independent buries it in the shared swing.
        double[] a = {10, 100, 20, 200, 30, 300};
        double[] b = {5, 95, 15, 195, 25, 295};

        SampleStats.Difference paired = SampleStats.comparePaired(a, b);
        SampleStats.Summary sa = SampleStats.summarise(a);
        SampleStats.Summary sb = SampleStats.summarise(b);

        assertThat(paired.distinguishable()).isTrue();
        assertThat(paired.high() - paired.low()).isZero();
        assertThat(sa.high() - sa.low())
                .as("the unpaired intervals overlap completely, hiding a difference that is exact")
                .isGreaterThan(100);
        assertThat(sa.low()).isLessThan(sb.high());
    }

    @Test
    void aSampleTooSmallToDescribeIsRefused() {
        assertThatThrownBy(() -> SampleStats.summarise(new double[] {1}))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("at least 2");
        assertThatThrownBy(() -> SampleStats.comparePaired(new double[] {1, 2}, new double[] {1}))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("equal size");
    }
}
