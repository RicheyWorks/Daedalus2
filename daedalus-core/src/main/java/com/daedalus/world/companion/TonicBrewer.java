// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import com.daedalus.world.companion.TonicBook.Mod;
import com.daedalus.world.companion.TonicBook.Recipe;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Optional;

/**
 * Brews Kennel Isle tonics by the rules in {@link TonicBook}. Pure and deterministic: the same herbs, coat,
 * drinker, stage and charm always give the same {@link Brew}.
 * <p>Strength: {@code S = clamp(base * coat * drinker * stage, 0, 2 * base)}, so every mod scales by
 * {@code f = clamp(coat * drinker * stage, 0, 2)}. An "add" mod becomes {@code value * f}; a "mul" mod becomes
 * {@code 1 + (value - 1) * f}. Duration is {@code durationSec * charm}. The Cane Corso drinks at full strength (1.0).</p>
 */
public final class TonicBrewer {
    /** Drinker kinds the book knows. */
    public static final String CANE_CORSO = "cane_corso";
    /** A pack member, half strength. */
    public static final String PACK_MEMBER = "packMember";

    /** One scaled, ready-to-apply tonic. */
    public record Brew(Recipe recipe, double factor, List<Mod> mods, int durationSec) {
        /** Defensive copy. */
        public Brew {
            mods = List.copyOf(mods);
        }
    }

    private final TonicBook book;

    /** Creates a brewer over a loaded book. */
    public TonicBrewer(TonicBook book) {
        this.book = book;
    }

    /**
     * Brews the herbs for one drinker.
     * @param herbs 1 to maxHerbs distinct herb names, any order
     * @param coatPattern Spots, Stripes, Labyrinth or None (unknown = None)
     * @param drinkerKind {@link #CANE_CORSO}, {@link #PACK_MEMBER} or anything else (= "other")
     * @param stage companion stage 1-3 (other values = no bonus)
     * @param matchingCharm whether the drinker wears a matching charm
     * @return the brew, or empty when the herb set makes no tonic
     */
    public Optional<Brew> brew(Collection<String> herbs, String coatPattern, String drinkerKind, int stage,
                               boolean matchingCharm) {
        return book.recipe(herbs).map(r -> scale(r, coatPattern, drinkerKind, stage, matchingCharm));
    }

    /** Percent chance a Labyrinth coat lands a second roll (tonics.json coat.Labyrinth.secondRollPct). */
    public static final int LABYRINTH_SECOND_ROLL_PCT = 10;

    /** A brew plus whether the Labyrinth second roll landed (the tonic hits twice: factor doubled, 2x cap). */
    public record RolledBrew(Brew brew, boolean secondRoll) { }

    /**
     * Seeded brew: like {@link #brew} but a Labyrinth coat gets a deterministic 10% second roll that applies the
     * effect again (strength factor doubled, still clamped to 2). The same seed and herbs always give the same result.
     */
    public Optional<RolledBrew> brew(Collection<String> herbs, String coatPattern, String drinkerKind, int stage,
                                     boolean matchingCharm, long seed) {
        return book.recipe(herbs).map(r -> {
            boolean second = "Labyrinth".equals(coatPattern) && secondRoll(seed, r.id());
            Brew b = scale(r, coatPattern, drinkerKind, stage, matchingCharm, second ? 2.0 : 1.0);
            return new RolledBrew(b, second);
        });
    }

    /** Deterministic 10% roll from a seed and recipe id (SplitMix64 finaliser). */
    static boolean secondRoll(long seed, String recipeId) {
        long z = seed ^ (0x9E3779B97F4A7C15L * recipeId.hashCode());
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        z ^= z >>> 31;
        return Math.floorMod(z, 100L) < LABYRINTH_SECOND_ROLL_PCT;
    }

    Brew scale(Recipe r, String coatPattern, String drinkerKind, int stage, boolean matchingCharm) {
        return scale(r, coatPattern, drinkerKind, stage, matchingCharm, 1.0);
    }

    Brew scale(Recipe r, String coatPattern, String drinkerKind, int stage, boolean matchingCharm, double extra) {
        double raw = book.coatMultiplier(coatPattern, r.shape()) * book.drinkerMultiplier(drinkerKind)
            * book.stageMultiplier(stage) * extra;
        double f = Math.max(0.0, Math.min(2.0, raw));
        List<Mod> out = new ArrayList<>();
        for (Mod m : r.mods()) {
            double v = "mul".equals(m.op()) ? 1.0 + (m.value() - 1.0) * f : m.value() * f;
            out.add(new Mod(m.stat(), m.op(), round(v)));
        }
        int dur = (int) Math.round(r.durationSec() * book.charmMultiplier(matchingCharm));
        return new Brew(r, round(f), out, dur);
    }

    private static double round(double v) {
        return Math.round(v * 1_000_000.0) / 1_000_000.0;
    }
}
