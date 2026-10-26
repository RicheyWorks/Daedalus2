// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.battlefield.BeaverWaters;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G34 Beaver Waters: the ark beaver colony learns dam work from the finished spring. The game keeps
 * no result record, so {@link Ponds#of} copies the final facts out of the simulation into an immutable snapshot;
 * the adapter never holds the live grid. WET completes; DRY or a FLOODED homestead is a failure.
 */
public final class BeaverWatersAdapter implements ActivityResultAdapter<BeaverWatersAdapter.Ponds> {

    public static final String ACTIVITY_ID = "battlefield.beaver-waters";

    /** Spring snapshot; the target's wet share is per mille. */
    public record Ponds(boolean wet, boolean homeFlooded, int targetWetPm, int pondCells, int wetCells, int felled,
                        int layersLeft, boolean abandoned) {
        public Ponds {
            if (pondCells < 0 || wetCells < 0 || felled < 0 || layersLeft < 0)
                throw new IllegalArgumentException("negative beaver facts");
            if (targetWetPm < 0 || targetWetPm > 1000) throw new IllegalArgumentException("target wet out of 0-1000");
            if (wet && homeFlooded) throw new IllegalArgumentException("a flooded homestead is never WET");
        }

        public static Ponds of(BeaverWaters g, boolean abandoned) {
            BeaverWaters.Outcome o = g.outcome();
            int pm = (int) Math.max(0, Math.min(1000, Math.round(g.targetWet() * 1000)));
            return new Ponds(o == BeaverWaters.Outcome.WET, o == BeaverWaters.Outcome.FLOODED, pm, g.pondCells(),
                    g.wetCells(), g.felled(), Math.max(0, g.layersLeft()), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public BeaverWatersAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "beaver-waters", 1, "shattered-planet", mode,
                Set.of("animal"), Set.of("building", "foraging"),
                Map.of("wet", 1L, "home_flooded", 1L, "target_wet_pm", 1000L, "pond_cells", 1_000_000L,
                        "wet_cells", 1_000_000L, "felled", 1_000_000L, "layers_left", 1_000_000L), 8);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Ponds p) {
        ActivityOutcome o = p.abandoned() ? ActivityOutcome.ABANDONED
                : p.wet() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("wet", p.wet() ? 1L : 0L);
        m.put("home_flooded", p.homeFlooded() ? 1L : 0L);
        m.put("target_wet_pm", (long) p.targetWetPm());
        m.put("pond_cells", (long) p.pondCells());
        m.put("wet_cells", (long) p.wetCells());
        m.put("felled", (long) p.felled());
        m.put("layers_left", (long) p.layersLeft());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}