// SPDX-License-Identifier: MIT

package com.daedalus.world;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class PlaceNamesTest {

    @Test
    void aKeyPicksAnInspiredStreetAndSkipsTakenNames() {
        String first = PlaceNames.of("plot-a");
        assertThat(first).isIn(PlaceNames.STREETS);
        String second = PlaceNames.of("plot-a", List.of(first));
        assertThat(second).isIn(PlaceNames.STREETS);
        assertThat(second).isNotEqualTo(first);
        assertThat(PlaceNames.of(null)).isIn(PlaceNames.STREETS);
        assertThat(PlaceNames.of("plot-a", PlaceNames.STREETS))
                .startsWith(PlaceNames.of("plot-a"))
                .endsWith(" " + (PlaceNames.STREETS.size() + 1));
    }
}
