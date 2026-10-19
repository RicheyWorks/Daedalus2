// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.breeding;

import com.daedalus.world.odds.OddsRng;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

/**
 * Mendelian odds for Turing-coat pups: each parent passes one allele per locus, each with probability 1/2, loci
 * independent. {@link #cross} gives the exact coat table of a pairing (all 64 gamete pairs), {@link #litter} rolls a
 * seeded litter with the Combat Odds Engine's {@link OddsRng}, and {@link #carrierChance} is the Bayes answer the ark
 * breeders always ask: this pup shows no storm-mark, so how likely is it to carry one?
 */
public final class CoatOdds {

    private CoatOdds() {
    }

    /** Exact probability of every coat a pairing can produce, in Pattern x Colour x mark order; impossible coats left out. */
    public static Map<Coat, Double> cross(Genotype mother, Genotype father) {
        Map<Coat, Double> raw = new LinkedHashMap<>();
        for (Genotype pup : offspring(mother, father)) {
            raw.merge(pup.coat(), 1.0 / 64, Double::sum);
        }
        Map<Coat, Double> out = new LinkedHashMap<>();
        for (Coat.Pattern p : Coat.Pattern.values()) {
            for (Coat.Colour c : Coat.Colour.values()) {
                for (boolean m : new boolean[] {false, true}) {
                    Coat coat = new Coat(p, c, m);
                    Double v = raw.get(coat);
                    if (v != null) {
                        out.put(coat, v);
                    }
                }
            }
        }
        return Collections.unmodifiableMap(out);
    }

    /** Chance a pup of this pairing has a coat matching {@code wanted}. */
    public static double chance(Genotype mother, Genotype father, Predicate<Coat> wanted) {
        double p = 0;
        for (Map.Entry<Coat, Double> e : cross(mother, father).entrySet()) {
            if (wanted.test(e.getKey())) {
                p += e.getValue();
            }
        }
        return p;
    }

    /** Chance a pup is storm-marked (the quest pup). */
    public static double stormMarkedChance(Genotype mother, Genotype father) {
        return chance(mother, father, Coat::stormMarked);
    }

    /** P(pup carries a storm-mark allele | pup shows no storm-mark). NaN if every pup is storm-marked. */
    public static double carrierChance(Genotype mother, Genotype father) {
        int unmarked = 0;
        int carriers = 0;
        for (Genotype pup : offspring(mother, father)) {
            if (!pup.coat().stormMarked()) {
                unmarked++;
                if (pup.carriesStormMark()) {
                    carriers++;
                }
            }
        }
        return unmarked == 0 ? Double.NaN : (double) carriers / unmarked;
    }

    /** A seeded litter of {@code size} pups (1-8). Same seed, same pups. */
    public static List<Genotype> litter(Genotype mother, Genotype father, long seed, int size) {
        if (size < 1 || size > 8) {
            throw new IllegalArgumentException("a litter is 1-8 pups, got " + size);
        }
        List<Genotype> out = new ArrayList<>();
        for (int i = 0; i < size; i++) {
            OddsRng rng = OddsRng.forTrial(seed, i);
            out.add(new Genotype(
                    pick(rng, mother.pattern1(), mother.pattern2()), pick(rng, father.pattern1(), father.pattern2()),
                    pick(rng, mother.colour1(), mother.colour2()), pick(rng, father.colour1(), father.colour2()),
                    pick(rng, mother.storm1(), mother.storm2()), pick(rng, father.storm1(), father.storm2())));
        }
        return out;
    }

    private static char pick(OddsRng rng, char a, char b) {
        return rng.nextDouble() < 0.5 ? a : b;
    }

    /** All 64 equally likely pups of a pairing (with repeats). */
    static List<Genotype> offspring(Genotype m, Genotype f) {
        char[] mp = {m.pattern1(), m.pattern2()};
        char[] fp = {f.pattern1(), f.pattern2()};
        char[] mc = {m.colour1(), m.colour2()};
        char[] fc = {f.colour1(), f.colour2()};
        char[] ms = {m.storm1(), m.storm2()};
        char[] fs = {f.storm1(), f.storm2()};
        List<Genotype> out = new ArrayList<>(64);
        for (char a : mp) {
            for (char b : fp) {
                for (char c : mc) {
                    for (char d : fc) {
                        for (char e : ms) {
                            for (char g : fs) {
                                out.add(new Genotype(a, b, c, d, e, g));
                            }
                        }
                    }
                }
            }
        }
        return out;
    }
}
