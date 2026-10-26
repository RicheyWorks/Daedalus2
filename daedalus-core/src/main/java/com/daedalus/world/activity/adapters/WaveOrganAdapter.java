// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.audio.WaveOrgan;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G109 Wave Organ: the companion that listened at the sea wall while you chose pipes is credited once
 * per tide. A true triad completes, anything else fails; the worst tuning error is kept in whole cents. Read-only on
 * the audio core.
 */
public final class WaveOrganAdapter implements ActivityResultAdapter<WaveOrganAdapter.Tide> {

    public static final String ACTIVITY_ID = "audio.wave-organ";

    /** Tide snapshot. */
    public record Tide(boolean triad, int worstCents, boolean abandoned) {
        public Tide {
            if (worstCents < 0) throw new IllegalArgumentException("negative cents");
        }

        public static Tide of(WaveOrgan.Verdict v, boolean abandoned) {
            double c = Math.abs(v.worstCents());
            int cents = Double.isFinite(c) ? (int) Math.min(1200, Math.round(c)) : 1200;
            return new Tide(v.triad(), cents, abandoned);
        }
    }

    private final ActivityDefinition definition;

    public WaveOrganAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "wave-organ-tide", 1, "shattered-planet", mode,
                Set.of("bird", "animal"), Set.of("listening", "singing", "observation"),
                Map.of("triad", 1L, "worst_cents", 1200L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Tide r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.triad() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("triad", Math.min(1L, (long) (r.triad() ? 1 : 0)));
        m.put("worst_cents", Math.min(1200L, (long) (r.worstCents())));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
