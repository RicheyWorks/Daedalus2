// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import com.daedalus.world.companion.TonicBrewer.Brew;
import com.daedalus.world.companion.TuringCoat.Genes;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.SplittableRandom;

/**
 * Bond tonic litters (contest gap G32). Composes the Kennel Isle {@link TonicBrewer} and {@link TuringCoat}: a pair
 * that drank a breeding brew (a recipe with {@code breedChancePct}, such as Bond = Dozeleaf + Starkibble) gets that
 * bonus, scaled by the brew's strength factor, on top of the base odds. A successful pairing gives a seeded litter of
 * 1..{@link #MAX_LITTER} pups whose genes come from {@link TuringCoat#breed}. Pure and deterministic per seed.
 */
public final class KennelLitter {
    public static final double BASE_PCT = 30.0;
    public static final double CAP_PCT = 90.0;
    public static final int MAX_LITTER = 3;
    public static final int COOLDOWN_DAYS = 7;

    /** A breeding pet. {@code daysSinceLitter} is null if it never had one. */
    public record Parent(String name, Genes genes, Integer daysSinceLitter) {
        public boolean rested() {
            return daysSinceLitter == null || daysSinceLitter >= COOLDOWN_DAYS;
        }
    }

    public record Pup(String name, Genes genes) {
        /** Grows the pup's coat (costly: a full reaction-diffusion run). */
        public String coat(long seed) {
            return TuringCoat.coat(genes, seed).pattern();
        }
    }

    public record Attempt(double chancePct, boolean success, List<Pup> litter, String blockedReason) {
        public Attempt {
            litter = List.copyOf(litter);
        }
    }

    private KennelLitter() {
    }

    /** Breeding odds in percent for a pair, optionally after a brew both drank. */
    public static double chancePct(Optional<Brew> brew) {
        double bonus = brew.map(b -> b.recipe().breedChancePct() * b.factor()).orElse(0.0);
        return Math.min(CAP_PCT, BASE_PCT + Math.max(0, bonus));
    }

    /** One pairing attempt. Parents must be different pets and both rested. */
    public static Attempt pair(Parent mother, Parent father, Optional<Brew> brew, long seed) {
        if (mother.name().equals(father.name())) {
            return new Attempt(0, false, List.of(), "same pet");
        }
        if (!mother.rested() || !father.rested()) {
            return new Attempt(0, false, List.of(), "parent resting");
        }
        double pct = chancePct(brew);
        SplittableRandom r = new SplittableRandom(seed);
        boolean ok = r.nextDouble() * 100 < pct;
        List<Pup> pups = new ArrayList<>();
        if (ok) {
            int size = 1 + r.nextInt(MAX_LITTER);
            for (int i = 0; i < size; i++) {
                pups.add(new Pup(mother.name() + "-" + father.name() + "-" + (i + 1),
                    TuringCoat.breed(mother.genes(), father.genes(), r.nextLong())));
            }
        }
        return new Attempt(pct, ok, pups, null);
    }

    /** Success rate over {@code tries} seeds (for balancing and tests). */
    public static double observedRate(Parent m, Parent f, Optional<Brew> brew, long firstSeed, int tries) {
        int ok = 0;
        for (int i = 0; i < tries; i++) {
            if (pair(m, f, brew, firstSeed + i).success()) {
                ok++;
            }
        }
        return ok / (double) tries;
    }
}
