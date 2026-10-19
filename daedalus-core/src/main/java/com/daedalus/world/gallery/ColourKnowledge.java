// SPDX-License-Identifier: MIT
package com.daedalus.world.gallery;

import java.util.EnumMap;
import java.util.EnumSet;
import java.util.Map;
import java.util.Set;

/**
 * GAL01 colour knowledge: "make colour useful". A painter (player or companion) learns a colour by restoring
 * mural cells with it. Knowing a colour unlocks a city ability; a secondary can only be mixed once both of its
 * primaries are known. Learning is never lost (smudges cost pigment, not knowledge). Thresholds are proposed and
 * need owner tuning.
 */
public final class ColourKnowledge {

    /** Correct strokes needed to know a colour (proposed). */
    public static final int KNOW_AT = 3;

    /** City abilities colour knowledge unlocks (proposed, original names). */
    public enum Ability {
        /** RED: light a warm lantern that keeps the Grey Wash off one cell for a while. */
        EMBER_LANTERN(EnumSet.of(Pigment.RED)),
        /** BLUE: tint a canal or fountain so canal paths show on the map. */
        CANAL_TINT(EnumSet.of(Pigment.BLUE)),
        /** YELLOW: brighten a dim gallery so hidden frames can be seen. */
        SUNWASH(EnumSet.of(Pigment.YELLOW)),
        /** GREEN: coax a painted vine into a climbable trellis on a frame street. */
        TRELLIS_VINE(EnumSet.of(Pigment.GREEN)),
        /** VIOLET: read the curator's dusk inscriptions (GAL03 proof notes). */
        DUSK_READING(EnumSet.of(Pigment.VIOLET)),
        /** All three primaries: split light through a colour prism to reveal a mural's missing colours. */
        PRISM_SIGHT(EnumSet.of(Pigment.RED, Pigment.YELLOW, Pigment.BLUE));

        private final Set<Pigment> needs;

        Ability(Set<Pigment> needs) { this.needs = Set.copyOf(needs); }

        public Set<Pigment> needs() { return EnumSet.copyOf(needs); }
    }

    private final EnumMap<Pigment, Integer> strokes = new EnumMap<>(Pigment.class);

    /** Records one correct stroke of a colour. */
    public synchronized void learn(Pigment p) {
        if (p == null) throw new IllegalArgumentException("pigment required");
        strokes.merge(p, 1, Integer::sum);
    }

    public synchronized int strokes(Pigment p) { return strokes.getOrDefault(p, 0); }

    public synchronized boolean knows(Pigment p) { return strokes(p) >= KNOW_AT; }

    /** True when both primaries of a secondary are known (primaries are never mixed). */
    public synchronized boolean canMix(Pigment secondary) {
        if (secondary.primary()) return false;
        for (Pigment c : secondary.components()) if (!knows(c)) return false;
        return true;
    }

    /** Abilities currently unlocked. */
    public synchronized Set<Ability> abilities() {
        EnumSet<Ability> out = EnumSet.noneOf(Ability.class);
        for (Ability a : Ability.values()) {
            boolean all = true;
            for (Pigment p : a.needs) all &= knows(p);
            if (all) out.add(a);
        }
        return out;
    }

    /** Snapshot of stroke counts. */
    public synchronized Map<Pigment, Integer> snapshot() { return Map.copyOf(strokes); }
}
