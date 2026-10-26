// SPDX-License-Identifier: MIT
package com.daedalus.world.gallery;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 activity-result adapter for GAL01 mural restoration: companions that help restore a living painting
 * (a Prism Finch carrying pigment, an Easel Mule hauling pots) earn restoration mastery through one receipt.
 * The painting keeps its rules; this adapter reads the finished session.
 */
public final class MuralRestorationAdapter implements ActivityResultAdapter<MuralRestorationAdapter.Session> {

    public static final String ACTIVITY_ID = "gallery.mural-restoration";

    /** A finished restoration session snapshot (cells restored this session, smudges, whether the painter left). */
    public record Session(int cellsRestored, int smudges, int coloursUsed, boolean living, boolean abandoned) {
        public Session {
            if (cellsRestored < 0 || smudges < 0 || coloursUsed < 0) throw new IllegalArgumentException("negative facts");
        }

        /** Snapshots a painting after a session that started with {@code restoredBefore} cells restored. */
        public static Session of(LivingPainting p, int restoredBefore, int smudgesBefore, boolean abandoned) {
            return new Session(p.restoredCells() - restoredBefore, p.smudges() - smudgesBefore, p.colours().size(),
                    p.state() == LivingPainting.State.LIVING, abandoned);
        }
    }

    private final ActivityDefinition definition;

    public MuralRestorationAdapter(ActivityMode mode) {
        this.definition = new ActivityDefinition(ACTIVITY_ID, "mural-restoration", 1, "gallery-city", mode,
                Set.of("animal", "bird", "social_insect"), Set.of("restoration", "carrying", "observation"),
                Map.of("cells_restored", (long) (LivingPainting.MAX_SIDE * LivingPainting.MAX_SIDE),
                        "smudges", 10_000L, "colours_used", (long) Pigment.values().length, "mural_living", 1L), 4);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(ActivityResultAdapter.Session s, Session r) {
        ActivityOutcome outcome = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.living() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("cells_restored", (long) r.cellsRestored());
        m.put("smudges", (long) r.smudges());
        m.put("colours_used", (long) r.coloursUsed());
        m.put("mural_living", r.living() ? 1L : 0L);
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                outcome, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
