// SPDX-License-Identifier: MIT

package com.daedalus.world.brew;

import com.daedalus.world.audio.Herb;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;

/**
 * Herb -> pitch class (0..11). Melody Brewing and prometheus's Harmonic Herbs share one pitch class per herb
 * (BREW_SPLIT.md); this interface keeps the brew bench independent of which table is the agreed one.
 */
@FunctionalInterface
public interface PitchTable {
    /** Pitch class of the herb, or empty if this table does not know it. */
    Optional<Integer> pitchOf(String herb);

    /** The Youtube Master Island canon from {@code herbcombo.py}: twelve herbs, one per chromatic step. */
    PitchTable ISLAND_CANON = new PitchTable() {
        private final Map<String, Integer> pcs = canon();

        @Override
        public Optional<Integer> pitchOf(String herb) {
            return herb == null ? Optional.empty() : Optional.ofNullable(pcs.get(herb.strip().toLowerCase(Locale.ROOT)));
        }
    };

    /** prometheus's HerbChord hash ({@link Herb#pitchClass()}); knows every non-blank id. */
    PitchTable HERB_CHORD = herb -> herb == null || herb.isBlank() ? Optional.empty() : Optional.of(new Herb(herb, 1).pitchClass());

    /** This table, falling back to {@code other} for herbs it does not know. */
    default PitchTable orElse(PitchTable other) {
        return herb -> pitchOf(herb).or(() -> other.pitchOf(herb));
    }

    /** The twelve island herbs in canon order (pitch class = index). */
    static Map<String, Integer> canon() {
        String[] names = {"Doleaf", "Sharpcress", "Rebell", "Flatfern", "Mimint", "Fasage", "Hushmoss", "Solthorn",
            "Gloryroot", "Lavine", "Dronebloom", "Tisquill"};
        Map<String, Integer> m = new LinkedHashMap<>();
        for (int i = 0; i < names.length; i++) {
            m.put(names[i].toLowerCase(Locale.ROOT), i);
        }
        return m;
    }
}
