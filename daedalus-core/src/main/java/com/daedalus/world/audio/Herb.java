package com.daedalus.world.audio;

import java.util.List;
import java.util.Locale;

/**
 * A herb as the sound system sees it.
 *
 * @param id herb id (e.g. "mint", "Doleaf"); the island canon or its stable hash picks the pitch class
 * @param potency 0..1 (growth stage: seed/sprout/bloom)
 */
public record Herb(String id, double potency) {
    /**
     * The twelve island canon herbs, one per chromatic step (pitch class = index). Same order as
     * Youtube Master Island's {@code herbcombo.py} and {@code brew.PitchTable.ISLAND_CANON}.
     */
    public static final List<String> CANON = List.of("Doleaf", "Sharpcress", "Rebell", "Flatfern", "Mimint", "Fasage",
            "Hushmoss", "Solthorn", "Gloryroot", "Lavine", "Dronebloom", "Tisquill");

    /** Validates. */
    public Herb {
        if (id == null || id.isBlank()) {
            throw new IllegalArgumentException("herb id required");
        }
        potency = Math.max(0, Math.min(1, potency));
    }

    /**
     * Pitch class 0..11: the canon index for the twelve {@link #CANON} herbs (case-insensitive), otherwise
     * FNV-1a of the lower-case id (fallback for non-canon herbs); stable across JVMs and ports.
     */
    public int pitchClass() {
        String key = id.strip().toLowerCase(Locale.ROOT);
        for (int i = 0; i < CANON.size(); i++) {
            if (CANON.get(i).toLowerCase(Locale.ROOT).equals(key)) {
                return i;
            }
        }
        int h = 0x811c9dc5;
        for (char c : key.toCharArray()) {
            h ^= c;
            h *= 0x01000193;
        }
        return Integer.remainderUnsigned(h, 12);
    }
}
