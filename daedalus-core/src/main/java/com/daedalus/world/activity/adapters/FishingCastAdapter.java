// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.fishing.CastSession;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G07 sky-island fishing: a companion that fishes with you (a Kite Ray spotting ripples, a heron
 * watching the float) earns from the casts the {@link CastSession} rules already decided. Read-only on the fishing
 * core: it only counts finished casts.
 */
public final class FishingCastAdapter implements ActivityResultAdapter<FishingCastAdapter.Outing> {

    public static final String ACTIVITY_ID = "fishing.cast-outing";
    public static final int MAX_CASTS = 200;

    /** A finished fishing outing: casts made, fish landed, rare fish, first-of-kind log entries, missed bites. */
    public record Outing(int casts, int caught, int rareCaught, int newKinds, int missed, boolean abandoned) {
        public Outing {
            if (casts < 0 || caught < 0 || rareCaught < 0 || newKinds < 0 || missed < 0)
                throw new IllegalArgumentException("negative outing facts");
            if (caught + missed > casts || rareCaught > caught || newKinds > caught)
                throw new IllegalArgumentException("outing facts do not add up");
        }

        /**
         * Tallies finished casts. {@code newKinds} is how many of them the host's FishLog reported as first of
         * their kind. A cast still running counts as made but neither caught nor missed.
         */
        public static Outing of(List<CastSession> casts, int newKinds, boolean abandoned) {
            int caught = 0, rare = 0, missed = 0;
            for (CastSession c : casts) {
                switch (c.outcome()) {
                    case CAUGHT -> {
                        caught++;
                        if (c.fish().map(f -> f.rarity().isRare()).orElse(false)) rare++;
                    }
                    case TOO_SOON, GOT_AWAY -> missed++;
                    default -> { }
                }
            }
            return new Outing(casts.size(), caught, rare, newKinds, missed, abandoned);
        }
    }

    private final ActivityDefinition definition;

    public FishingCastAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "fishing-cast-outing", 1, "shattered-planet", mode,
                Set.of("animal", "bird", "fish"), Set.of("scouting", "observation", "current_travel"),
                Map.of("casts", (long) MAX_CASTS, "caught", (long) MAX_CASTS, "rare_caught", (long) MAX_CASTS,
                        "new_kinds", (long) MAX_CASTS, "missed", (long) MAX_CASTS), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Outing o) {
        ActivityOutcome outcome = o.abandoned() ? ActivityOutcome.ABANDONED
                : o.caught() > 0 ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("casts", (long) o.casts());
        m.put("caught", (long) o.caught());
        m.put("rare_caught", (long) o.rareCaught());
        m.put("new_kinds", (long) o.newKinds());
        m.put("missed", (long) o.missed());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                outcome, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
