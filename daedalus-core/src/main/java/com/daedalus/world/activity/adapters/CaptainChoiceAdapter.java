// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.odds.stopping.CaptainChoiceQuest;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G122 Choosing the Last Captain: the companion that sat beside you through the dock interviews is
 * credited once per quest. Hiring the single best sailor completes, any other hire fails; interviews still running are
 * refused unless the host abandoned the quest. Read-only on the odds core.
 */
public final class CaptainChoiceAdapter implements ActivityResultAdapter<CaptainChoiceAdapter.Hiring> {

    public static final String ACTIVITY_ID = "odds.captain-choice";

    /** Hiring snapshot. */
    public record Hiring(boolean best, int rank, int seen, boolean abandoned) {
        public Hiring {
            int n = CaptainChoiceQuest.CANDIDATES;
            if (seen < 0 || seen > n) throw new IllegalArgumentException("seen out of range");
            if (rank != -1 && (rank < 1 || rank > n)) throw new IllegalArgumentException("rank out of range");
            if (best && rank != 1) throw new IllegalArgumentException("best hire must be rank 1");
        }

        public static Hiring of(CaptainChoiceQuest q, boolean abandoned) {
            if (q.stage() == CaptainChoiceQuest.Stage.INTERVIEWING && !abandoned)
                throw new IllegalArgumentException("interviews still in progress: INTERVIEWING");
            return new Hiring(q.stage() == CaptainChoiceQuest.Stage.BEST_HIRED, q.hiredRank(), q.seen(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public CaptainChoiceAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "captain-choice", 1, "sky-islands", mode,
                Set.of("animal", "bird"), Set.of("scouting", "observation", "judgement"),
                Map.of("best", 1L, "rank", (long) CaptainChoiceQuest.CANDIDATES,
                        "seen", (long) CaptainChoiceQuest.CANDIDATES), 2);
    }
    @Override
    public ActivityDefinition definition() { return definition; }
    @Override
    public ActivityResultReceipt toReceipt(Session s, Hiring r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.best() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("best", r.best() ? 1L : 0L);
        m.put("rank", (long) Math.max(0, r.rank()));
        m.put("seen", (long) r.seen());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}