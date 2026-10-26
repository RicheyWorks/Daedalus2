// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.battlefield.PatchForager;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G129 Squirrel's Winter: the companion that ran the bramble patches with the red squirrel is credited
 * once per day. A HOARDED day completes, SHORT or STARVED fails; the share of the marginal-value best day is kept in
 * whole percent (capped at {@link #MAX_SHARE_PCT}). Read-only on the forager core; built from its own {@code Report}.
 */
public final class SquirrelsWinterAdapter implements ActivityResultAdapter<SquirrelsWinterAdapter.Hoard> {

    public static final String ACTIVITY_ID = "ecology.squirrels-winter";
    /** Cap on the share measure. */
    public static final int MAX_SHARE_PCT = 200;
    /** Cap on the visits measure. */
    public static final int MAX_VISITS = 10_000;

    /** Hoard snapshot. */
    public record Hoard(PatchForager.Outcome outcome, int sharePct, int visits, boolean abandoned) {
        public Hoard {
            if (outcome == null) throw new IllegalArgumentException("outcome required");
            if (sharePct < 0 || visits < 0) throw new IllegalArgumentException("negative hoard facts");
        }

        public static Hoard of(PatchForager.Report r, boolean abandoned) {
            double sh = r.share();
            int pct = Double.isFinite(sh) ? (int) Math.max(0, Math.min(MAX_SHARE_PCT, Math.round(sh * 100))) : 0;
            return new Hoard(r.outcome(), pct, r.visits().size(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public SquirrelsWinterAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "squirrels-winter", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("foraging", "observation", "companionship"),
                Map.of("hoarded", 1L, "share_pct", (long) MAX_SHARE_PCT, "visits", (long) MAX_VISITS), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Hoard r) {
        boolean hoarded = r.outcome() == PatchForager.Outcome.HOARDED;
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : hoarded ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("hoarded", hoarded ? 1L : 0L);
        m.put("share_pct", Math.min((long) MAX_SHARE_PCT, (long) r.sharePct()));
        m.put("visits", Math.min((long) MAX_VISITS, (long) r.visits()));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
