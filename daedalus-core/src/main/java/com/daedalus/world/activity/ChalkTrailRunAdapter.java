// SPDX-License-Identifier: MIT
package com.daedalus.world.activity;

import com.daedalus.world.labyrinth.ChalkTrail;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * Activity-result v1 adapter for the existing Labyrinth {@link ChalkTrail}: a companion that walks the maze with
 * the player and helps chalk the route learns scouting. The trail keeps its own rules; this adapter only reads the
 * finished trail (marks left, chalk remaining) and whether the exit was reached.
 *
 * <p>Tie-in: "Listen to the maze before trusting a map" - the creature learns the maze by marking it, so peaceful
 * scouting is a full growth path (What Life Learns), with no kill count.
 */
public final class ChalkTrailRunAdapter implements ActivityResultAdapter<ChalkTrailRunAdapter.Run> {

    public static final String ACTIVITY_ID = "labyrinth.chalk-trail";

    /** A finished chalk-trail run snapshot: marks kept, chalk left and carried in, and how the run ended. */
    public record Run(int marksKept, int chalkLeft, int chalkCarried, boolean exitReached, boolean abandoned) {
        public Run {
            if (marksKept < 0 || chalkLeft < 0) throw new IllegalArgumentException("negative trail facts");
            if (chalkCarried < chalkLeft) throw new IllegalArgumentException("chalkCarried < chalk left");
        }

        /** Snapshots the finished trail the host already owns. */
        public static Run of(ChalkTrail trail, int chalkCarried, boolean exitReached, boolean abandoned) {
            if (trail == null) throw new IllegalArgumentException("trail required");
            return new Run(trail.marks().size(), trail.charges(), chalkCarried, exitReached, abandoned);
        }
    }

    private final ActivityDefinition definition;

    public ChalkTrailRunAdapter(ActivityMode mode) {
        this.definition = new ActivityDefinition(ACTIVITY_ID, "chalk-trail-run", 1, "labyrinth", mode,
                Set.of("animal", "bird", "social_insect"), Set.of("scouting", "observation"),
                Map.of("marks_kept", 512L, "chalk_spent", 10_000L, "exit_reached", 1L), 4);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Run run) {
        ActivityOutcome outcome = run.abandoned() ? ActivityOutcome.ABANDONED
                : run.exitReached() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> measures = new LinkedHashMap<>();
        measures.put("marks_kept", (long) run.marksKept());
        measures.put("chalk_spent", (long) (run.chalkCarried() - run.chalkLeft()));
        measures.put("exit_reached", run.exitReached() ? 1L : 0L);
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                outcome, s.participants(), measures, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
