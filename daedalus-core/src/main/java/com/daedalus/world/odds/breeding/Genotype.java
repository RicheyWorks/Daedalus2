// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.breeding;

import com.daedalus.world.companion.TuringCoat;
import java.util.Locale;

/**
 * A Turing-coat pup's genes at its three coat loci, two alleles each. Written as three letter pairs, e.g.
 * {@code "SB EA CM"}: pattern (S spots, B stripes/bands, L labyrinth, P plain; each a {@link TuringCoat} kennel line),
 * colour (E ember, A ash), storm-mark (C clear, M marked; the mark shows only in MM). Immutable value.
 */
public record Genotype(char pattern1, char pattern2, char colour1, char colour2, char storm1, char storm2) {

    static final String PATTERN = "SBLP";
    static final String COLOUR = "EA";
    static final String STORM = "CM";

    public Genotype {
        check(pattern1, PATTERN, "pattern");
        check(pattern2, PATTERN, "pattern");
        check(colour1, COLOUR, "colour");
        check(colour2, COLOUR, "colour");
        check(storm1, STORM, "storm");
        check(storm2, STORM, "storm");
    }

    private static void check(char c, String allowed, String locus) {
        if (allowed.indexOf(c) < 0) {
            throw new IllegalArgumentException(locus + " allele must be one of " + allowed + ", got '" + c + "'");
        }
    }

    /** Parses {@code "SB EA CM"} (case-insensitive, spaces optional). */
    public static Genotype parse(String text) {
        if (text == null) {
            throw new IllegalArgumentException("no genotype");
        }
        String s = text.replace(" ", "").toUpperCase(Locale.ROOT);
        if (s.length() != 6) {
            throw new IllegalArgumentException("genotype needs 3 letter pairs, got '" + text + "'");
        }
        return new Genotype(s.charAt(0), s.charAt(1), s.charAt(2), s.charAt(3), s.charAt(4), s.charAt(5));
    }

    /** The coat these genes show. */
    public Coat coat() {
        Coat.Pattern p = PATTERN.indexOf(pattern1) <= PATTERN.indexOf(pattern2) ? pattern(pattern1) : pattern(pattern2);
        Coat.Colour c;
        if (colour1 != colour2) {
            c = Coat.Colour.SMOKE;
        } else {
            c = colour1 == 'E' ? Coat.Colour.EMBER : Coat.Colour.ASH;
        }
        return new Coat(p, c, storm1 == 'M' && storm2 == 'M');
    }

    /** The G21 TuringCoat genes of the line this pup expresses: grow them to draw the coat. */
    public TuringCoat.Genes turingGenes() {
        return coat().pattern().genes();
    }

    /** The coat key the pup's skin actually grows into (runs the G21 Gray-Scott model; costs a few ms). */
    public String grownCoatKey(long seed) {
        return TuringCoat.coat(turingGenes(), seed).pattern();
    }

    /** True when the pup carries at least one storm-mark allele. */
    public boolean carriesStormMark() {
        return storm1 == 'M' || storm2 == 'M';
    }

    private static Coat.Pattern pattern(char a) {
        return switch (a) {
            case 'S' -> Coat.Pattern.SPOTS;
            case 'B' -> Coat.Pattern.STRIPES;
            case 'L' -> Coat.Pattern.LABYRINTH;
            default -> Coat.Pattern.PLAIN;
        };
    }

    /** {@code "SB EA CM"}, each pair in canonical (dominant-first) order. */
    @Override
    public String toString() {
        return pair(pattern1, pattern2, PATTERN) + " " + pair(colour1, colour2, COLOUR) + " " + pair(storm1, storm2, STORM);
    }

    private static String pair(char a, char b, String order) {
        return order.indexOf(a) <= order.indexOf(b) ? "" + a + b : "" + b + a;
    }
}
