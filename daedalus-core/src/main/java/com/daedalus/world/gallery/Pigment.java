// SPDX-License-Identifier: MIT
package com.daedalus.world.gallery;

import java.util.List;
import java.util.Optional;

/**
 * GAL01 pigments. Primaries are ground from Gallery City chemistry (beets and cherries, dawnleaf, cobalt);
 * secondaries are mixed from two primaries, or ground directly from their own source where the realm has one
 * (oranges, copper verdigris). Proposed rules, original to Daedalus.
 */
public enum Pigment {
    RED(List.of("beet", "cherry")),
    YELLOW(List.of("dawnleaf")),
    BLUE(List.of("cobalt")),
    ORANGE(List.of("orange")),
    GREEN(List.of("copper")),
    VIOLET(List.of());

    private final List<String> sources;

    Pigment(List<String> sources) { this.sources = sources; }

    /** Chemistry ingredients that grind straight into this pigment (may be empty: mix only). */
    public List<String> sources() { return List.copyOf(sources); }

    public boolean primary() { return this == RED || this == YELLOW || this == BLUE; }

    /** The two primaries that mix into this secondary; empty for primaries. */
    public List<Pigment> components() {
        return switch (this) {
            case ORANGE -> List.of(RED, YELLOW);
            case GREEN -> List.of(YELLOW, BLUE);
            case VIOLET -> List.of(RED, BLUE);
            default -> List.of();
        };
    }

    /** Pigment ground from a chemistry ingredient key, if any. */
    public static Optional<Pigment> fromIngredient(String ingredient) {
        for (Pigment p : values()) if (p.sources.contains(ingredient)) return Optional.of(p);
        return Optional.empty();
    }
}
