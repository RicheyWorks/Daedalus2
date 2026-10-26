// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.bricks.AssemblyRepair;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G16 Missing Piece Collector: a helper (a magpie spotting the genuine piece, a mule hauling the bag)
 * learns repair work from the {@link AssemblyRepair.Receipt} the repair already graded. A restored machine completes.
 */
public final class AssemblyRepairAdapter implements ActivityResultAdapter<AssemblyRepairAdapter.Repair> {

    public static final String ACTIVITY_ID = "bricks.assembly-repair";

    /** Repair snapshot. */
    public record Repair(boolean restored, int meanQuality, int piecesUsed, int rejects, int kilnUses,
                         boolean skyGateOpen, boolean abandoned) {
        public Repair {
            if (meanQuality < 0 || piecesUsed < 0 || rejects < 0 || kilnUses < 0)
                throw new IllegalArgumentException("negative repair facts");
            if (skyGateOpen && !restored) throw new IllegalArgumentException("the sky gate opens only on a restored machine");
        }

        public static Repair of(AssemblyRepair.Receipt r, boolean abandoned) {
            return new Repair(r.restored(), r.meanQuality(), r.piecesUsed().size(), r.rejects(), r.kilnUses(),
                    r.skyGateOpen(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public AssemblyRepairAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "assembly-repair", 1, "bricks", mode,
                Set.of("animal", "bird"), Set.of("scouting", "carrying"),
                Map.of("restored", 1L, "mean_quality", 10_000L, "pieces_used", 64L, "rejects", 1_000L,
                        "kiln_uses", 100L, "sky_gate_open", 1L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Repair r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.restored() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("restored", r.restored() ? 1L : 0L);
        m.put("mean_quality", (long) r.meanQuality());
        m.put("pieces_used", (long) r.piecesUsed());
        m.put("rejects", (long) r.rejects());
        m.put("kiln_uses", (long) r.kilnUses());
        m.put("sky_gate_open", r.skyGateOpen() ? 1L : 0L);
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
