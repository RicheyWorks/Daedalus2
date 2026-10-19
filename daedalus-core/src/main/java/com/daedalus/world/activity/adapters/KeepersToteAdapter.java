// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.odds.tote.ToteQuest;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
/**
 * G12 adapter for G88 The Keeper's Tote: the companion that read the crowd learns from one heat. WON completes;
 * LOST is a failure (the overlay measure still records whether the price was good). BOARD_OPEN and BACKED are
 * refused unless the host abandoned the heat.
 */
public final class KeepersToteAdapter implements ActivityResultAdapter<KeepersToteAdapter.Heat> {

    public static final String ACTIVITY_ID = "odds.keepers-tote";

    /** Heat snapshot. */
    public record Heat(boolean won, boolean overlay, long pool, boolean abandoned) {
        public Heat {
            if (pool < 0) throw new IllegalArgumentException("negative pool");
        }

        public static Heat of(ToteQuest q, boolean abandoned) {
            ToteQuest.Stage st = q.stage();
            boolean done = st == ToteQuest.Stage.WON || st == ToteQuest.Stage.LOST;
            if (!done && !abandoned) throw new IllegalArgumentException("heat still in progress: " + st);
            return new Heat(st == ToteQuest.Stage.WON, q.overlay(), q.pool(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public KeepersToteAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "keepers-tote", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("observation", "counting"),
                Map.of("won", 1L, "overlay", 1L, "pool", 1_000_000_000L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Heat h) {
        ActivityOutcome o = h.abandoned() ? ActivityOutcome.ABANDONED
                : h.won() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("won", h.won() ? 1L : 0L);
        m.put("overlay", h.overlay() ? 1L : 0L);
        m.put("pool", Math.min(1_000_000_000L, h.pool()));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}