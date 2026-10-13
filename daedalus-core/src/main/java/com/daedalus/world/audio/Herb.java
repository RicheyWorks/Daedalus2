package com.daedalus.world.audio;

/**
 * A herb as the sound system sees it.
 *
 * @param id herb id (e.g. "mint", "yarrow"); its stable hash picks the pitch class
 * @param potency 0..1 (growth stage: seed/sprout/bloom)
 */
public record Herb(String id, double potency) {
    /** Validates. */
    public Herb {
        if (id == null || id.isBlank()) {
            throw new IllegalArgumentException("herb id required");
        }
        potency = Math.max(0, Math.min(1, potency));
    }

    /** Pitch class 0..11 from FNV-1a of the lower-case id; stable across JVMs and ports. */
    public int pitchClass() {
        int h = 0x811c9dc5;
        for (char c : id.strip().toLowerCase(java.util.Locale.ROOT).toCharArray()) {
            h ^= c;
            h *= 0x01000193;
        }
        return Integer.remainderUnsigned(h, 12);
    }
}
