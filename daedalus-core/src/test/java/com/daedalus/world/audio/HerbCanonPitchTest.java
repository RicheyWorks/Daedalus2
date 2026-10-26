// SPDX-License-Identifier: MIT
package com.daedalus.world.audio;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.brew.PitchTable;
import org.junit.jupiter.api.Test;

class HerbCanonPitchTest {
    @Test void canonHerbsUseTheIslandCanonIndex() {
        for (int i = 0; i < Herb.CANON.size(); i++) {
            String name = Herb.CANON.get(i);
            assertThat(new Herb(name, 1).pitchClass()).isEqualTo(i);
            assertThat(new Herb(" " + name.toUpperCase(java.util.Locale.ROOT) + " ", 1).pitchClass()).isEqualTo(i);
        }
    }

    @Test void canonMatchesBrewPitchTableExactly() {
        assertThat(Herb.CANON).hasSize(12);
        for (int i = 0; i < Herb.CANON.size(); i++) {
            assertThat(PitchTable.ISLAND_CANON.pitchOf(Herb.CANON.get(i))).contains(i);
            assertThat(PitchTable.HERB_CHORD.pitchOf(Herb.CANON.get(i))).contains(i);
        }
    }

    @Test void nonCanonHerbsKeepTheFnvFallback() {
        int h = 0x811c9dc5;
        for (char c : "mint".toCharArray()) {
            h ^= c;
            h *= 0x01000193;
        }
        assertThat(new Herb("mint", 1).pitchClass()).isEqualTo(Integer.remainderUnsigned(h, 12));
        assertThat(new Herb("Mint ", 1).pitchClass()).isEqualTo(new Herb("mint", 1).pitchClass());
    }
}