// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.battlefield.SeedVault;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G43 Ark Seed Vault: the seed-caching birds and vault keepers learn from the voyage. Landing with
 * every species band alive completes; landing short is a failure; a vault still at sea is refused (no receipt for a
 * voyage in progress unless it was abandoned).
 */
public final class SeedVaultAdapter implements ActivityResultAdapter<SeedVaultAdapter.Voyage> {

    public static final String ACTIVITY_ID = "battlefield.ark-seed-vault";

    /** Voyage snapshot at landfall (or when abandoned). */
    public record Voyage(boolean landed, int years, int survivingSpecies, int speciesCarried, int caches,
                         boolean abandoned) {
        public Voyage {
            if (years < 0 || caches < 0 || speciesCarried < 1)
                throw new IllegalArgumentException("negative voyage facts");
            if (survivingSpecies < 0 || survivingSpecies > speciesCarried)
                throw new IllegalArgumentException("surviving species out of range");
            if (!landed && !abandoned) throw new IllegalArgumentException("voyage still in progress");
        }

        /** Every band the ark carried came home alive. */
        public boolean allBands() { return landed && survivingSpecies == speciesCarried; }

        public static Voyage of(SeedVault v, boolean abandoned) {
            return new Voyage(v.landed(), v.year(), v.survivingSpecies(), SeedVault.Species.values().length,
                    v.caches(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public SeedVaultAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "ark-seed-vault", 1, "shattered-planet", mode,
                Set.of("bird", "animal"), Set.of("seeding", "caching"),
                Map.of("all_bands", 1L, "years", 1_000L, "surviving_species", 64L, "caches", 1_000_000L), 4);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Voyage v) {
        ActivityOutcome o = v.abandoned() ? ActivityOutcome.ABANDONED
                : v.allBands() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("all_bands", v.allBands() ? 1L : 0L);
        m.put("years", (long) v.years());
        m.put("surviving_species", (long) v.survivingSpecies());
        m.put("caches", (long) v.caches());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}