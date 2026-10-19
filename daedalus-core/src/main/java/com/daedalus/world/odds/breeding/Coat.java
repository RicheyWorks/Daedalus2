// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.breeding;

import com.daedalus.world.companion.TuringCoat;
import java.util.Locale;

/**
 * What a Turing-coat pup looks like: its pattern, its colour and whether it carries the storm-mark. The pattern is not
 * a second coat model: each {@link Pattern} is one of art-master-flex's {@link TuringCoat} kennel lines (G21), and
 * {@link Pattern#coatKey()} is the key that line grows into ({@code Spots}, {@code Stripes}, {@code Labyrinth},
 * {@code None}), the same key the Kennel Isle {@code TonicBrewer} reads.
 */
public record Coat(Pattern pattern, Colour colour, boolean stormMarked) {

    /** Coat pattern, i.e. the TuringCoat line a pup expresses. Dominance runs SPOTS over STRIPES over LABYRINTH over PLAIN. */
    public enum Pattern {
        SPOTS("Spots"), STRIPES("Stripes"), LABYRINTH("Labyrinth"), PLAIN("None");

        private final String key;

        Pattern(String key) {
            this.key = key;
        }

        /** The TuringCoat / TonicBrewer coat key. */
        public String coatKey() {
            return key;
        }

        /** The TuringCoat starter line whose Gray-Scott genes grow this pattern. */
        public TuringCoat.Genes genes() {
            return switch (this) {
                case SPOTS -> TuringCoat.SPOTTED_LINE;
                case STRIPES -> TuringCoat.STRIPED_LINE;
                case LABYRINTH -> TuringCoat.LABYRINTH_LINE;
                default -> TuringCoat.PLAIN_LINE;
            };
        }
    }

    /** Coat colour. EMBER and ASH blend to SMOKE (incomplete dominance). */
    public enum Colour { EMBER, SMOKE, ASH }

    public Coat {
        if (pattern == null || colour == null) {
            throw new IllegalArgumentException("a coat needs a pattern and a colour");
        }
    }

    /** "storm-marked smoke stripes", "ember spots". */
    public String describe() {
        String base = colour.name().toLowerCase(Locale.ROOT) + " " + pattern.name().toLowerCase(Locale.ROOT);
        return stormMarked ? "storm-marked " + base : base;
    }
}
