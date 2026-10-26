// SPDX-License-Identifier: MIT

package com.daedalus.world.ecology;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

/** Analytical results for between-community measures, independent of the calculation code. */
class CommunityComparisonTest {

    @Test
    void sixMeasuresMatchAHandCalculatedCommunityPair() {
        // Two and three species, one shared; totals 3 and 5, shared abundance 1.
        // Squared abundances total 5 and 11; the abundance dot product is 2.
        CommunityComparison result = CommunityComparison.between(
                Map.of("fern", 1.0, "moss", 2.0),
                Map.of("moss", 1.0, "pine", 3.0, "reed", 1.0));

        assertThat(result.firstRichness()).isEqualTo(2);
        assertThat(result.secondRichness()).isEqualTo(3);
        assertThat(result.sharedRichness()).isEqualTo(1);
        assertThat(result.jaccard()).isCloseTo(1.0 / 4, within(1e-12));
        assertThat(result.sorensen()).isCloseTo(2.0 / 5, within(1e-12));
        assertThat(result.brayCurtis()).isCloseTo(3.0 / 4, within(1e-12));
        assertThat(result.renkonen()).isCloseTo(1.0 / 5, within(1e-12));
        assertThat(result.pianka()).isCloseTo(2.0 / Math.sqrt(55), within(1e-12));
        assertThat(result.whittakerTurnover()).isCloseTo(3.0 / 5, within(1e-12));
        assertThat(result.shared()).containsExactly("moss");
        assertThat(result.onlyFirst()).containsExactly("fern");
        assertThat(result.onlySecond()).containsExactly("pine", "reed");
    }

    @Test
    void fractionalAbundancesAreNotRoundedToIndividuals() {
        CommunityComparison result = CommunityComparison.between(
                Map.of("bee", 0.25), Map.of("bee", 0.75));

        assertThat(result.firstRichness()).isEqualTo(1);
        assertThat(result.secondRichness()).isEqualTo(1);
        assertThat(result.sharedRichness()).isEqualTo(1);
        assertThat(result.jaccard()).isEqualTo(1);
        assertThat(result.sorensen()).isEqualTo(1);
        assertThat(result.brayCurtis()).isCloseTo(0.5, within(1e-12));
        assertThat(result.renkonen()).isEqualTo(1);
        assertThat(result.pianka()).isEqualTo(1);
        assertThat(result.whittakerTurnover()).isZero();
    }

    @Test
    void emptyCommunitiesRetainEachMeasuresDeclaredConvention() {
        CommunityComparison both = CommunityComparison.between(Map.of(), Map.of());
        assertThat(both.firstRichness()).isZero();
        assertThat(both.secondRichness()).isZero();
        assertThat(both.sharedRichness()).isZero();
        assertThat(both.jaccard()).isEqualTo(1);
        assertThat(both.sorensen()).isEqualTo(1);
        assertThat(both.brayCurtis()).isZero();
        assertThat(both.renkonen()).isEqualTo(1);
        assertThat(both.pianka()).isZero();
        assertThat(both.whittakerTurnover()).isZero();

        CommunityComparison one = CommunityComparison.between(Map.of(), Map.of("bee", 1.0));
        assertThat(one.jaccard()).isZero();
        assertThat(one.sorensen()).isZero();
        assertThat(one.brayCurtis()).isEqualTo(1);
        assertThat(one.renkonen()).isZero();
        assertThat(one.pianka()).isZero();
        assertThat(one.whittakerTurnover()).isEqualTo(1);
        assertThat(one.onlyFirst()).isEmpty();
        assertThat(one.onlySecond()).containsExactly("bee");
    }

    @Test
    void disjointCommunitiesHaveNoOverlapEvenWhenBothArePopulated() {
        CommunityComparison result = CommunityComparison.between(
                Map.of("fern", 0.25, "moss", 1.0), Map.of("pine", 2.0));

        assertThat(result.sharedRichness()).isZero();
        assertThat(result.shared()).isEmpty();
        assertThat(result.jaccard()).isZero();
        assertThat(result.sorensen()).isZero();
        assertThat(result.brayCurtis()).isEqualTo(1);
        assertThat(result.renkonen()).isZero();
        assertThat(result.pianka()).isZero();
        assertThat(result.whittakerTurnover()).isEqualTo(1);
    }

    @Test
    void scalingAvoidsOverflowAndRetainsSubnormalPresence() {
        double large = Double.MAX_VALUE;
        CommunityComparison result = CommunityComparison.between(
                Map.of("fern", large, "moss", large / 2),
                Map.of("fern", large / 2, "moss", large));

        assertThat(result.jaccard()).isEqualTo(1);
        assertThat(result.sorensen()).isEqualTo(1);
        assertThat(result.brayCurtis()).isCloseTo(1.0 / 3, within(1e-12));
        assertThat(result.renkonen()).isCloseTo(2.0 / 3, within(1e-12));
        assertThat(result.pianka()).isCloseTo(0.8, within(1e-12));
        assertThat(result.whittakerTurnover()).isZero();

        CommunityComparison tiny = CommunityComparison.between(
                Map.of("fern", Double.MIN_VALUE), Map.of("fern", Double.MIN_VALUE));
        assertThat(tiny.firstRichness()).isEqualTo(1);
        assertThat(tiny.sharedRichness()).isEqualTo(1);
        assertThat(tiny.brayCurtis()).isZero();
        assertThat(tiny.renkonen()).isEqualTo(1);
        assertThat(tiny.pianka()).isEqualTo(1);
    }

    @Test
    void zeroCountsAreAbsentAndPublishedListsAreSortedImmutableSnapshots() {
        Map<String, Double> first = new LinkedHashMap<>();
        first.put("zebra", 0.25);
        first.put("absent", 0.0);
        first.put("alpha", 1.0);
        Map<String, Double> second = new LinkedHashMap<>();
        second.put("zebra", 0.5);
        second.put("beta", 2.0);

        List<String> presence = CommunityComparison.presence(first);
        CommunityComparison result = CommunityComparison.between(first, second);
        assertThat(first).hasSize(3).containsEntry("absent", 0.0);
        assertThat(second).hasSize(2);
        first.clear();
        second.clear();

        assertThat(presence).containsExactly("alpha", "zebra");
        assertThat(result.firstRichness()).isEqualTo(2);
        assertThat(result.shared()).containsExactly("zebra");
        assertThat(result.onlyFirst()).containsExactly("alpha");
        assertThat(result.onlySecond()).containsExactly("beta");
        assertThatThrownBy(() -> presence.add("late")).isInstanceOf(UnsupportedOperationException.class);
        assertThatThrownBy(() -> result.shared().clear()).isInstanceOf(UnsupportedOperationException.class);
        assertThatThrownBy(() -> result.onlyFirst().clear()).isInstanceOf(UnsupportedOperationException.class);
        assertThatThrownBy(() -> result.onlySecond().clear()).isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void recordConstructionCopiesCallerOwnedLists() {
        List<String> shared = new ArrayList<>(List.of("moss"));
        List<String> onlyFirst = new ArrayList<>(List.of("fern"));
        List<String> onlySecond = new ArrayList<>(List.of("pine"));
        CommunityComparison result = new CommunityComparison(2, 2, 1,
                1.0 / 3, 0.5, 0.5, 0.5, 0.5, 0.5, shared, onlyFirst, onlySecond);
        shared.clear();
        onlyFirst.clear();
        onlySecond.clear();

        assertThat(result.shared()).containsExactly("moss");
        assertThat(result.onlyFirst()).containsExactly("fern");
        assertThat(result.onlySecond()).containsExactly("pine");
    }

    @Test
    void malformedCommunitiesAreRefusedOnEitherSide() {
        List<Map<String, Double>> malformed = List.of(
                Collections.singletonMap(null, 1.0),
                Map.of("", 1.0), Map.of(" \t", 1.0),
                Collections.singletonMap("fern", null),
                Map.of("fern", -0.1), Map.of("fern", Double.NaN),
                Map.of("fern", Double.POSITIVE_INFINITY),
                Map.of("fern", Double.NEGATIVE_INFINITY));
        for (Map<String, Double> community : malformed) {
            assertThatThrownBy(() -> CommunityComparison.between(community, Map.of()))
                    .isInstanceOf(IllegalArgumentException.class);
            assertThatThrownBy(() -> CommunityComparison.between(Map.of(), community))
                    .isInstanceOf(IllegalArgumentException.class);
        }
        assertThatThrownBy(() -> CommunityComparison.between(null, Map.of()))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CommunityComparison.between(Map.of(), null))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void regionalTurnoverIncludesEmptySitesInMeanLocalRichness() {
        // Regional richness 3; mean local richness 4/3; turnover 3 / (4/3) - 1 = 1.25.
        assertThat(CommunityComparison.whittakerTurnover(List.of(
                Map.of("fern", 1.0, "moss", 1.0),
                Map.of("moss", 2.0, "pine", 1.0), Map.of())))
                .isCloseTo(1.25, within(1e-12));
        assertThat(CommunityComparison.whittakerTurnover(List.of())).isZero();
        assertThat(CommunityComparison.whittakerTurnover(List.of(Map.of(), Map.of("absent", 0.0))))
                .isZero();
    }
}
