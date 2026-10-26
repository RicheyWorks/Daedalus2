// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.brew.stones.ChoirStones;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G53 Choir Stones (YTM story ch. 4): the companion that hauled stones and listened for fraying rope
 * is credited once per tremor run. A finished quest completes; a night that cut a fragment off before the quest was
 * done is a failure; otherwise the run is still in play and refused unless abandoned. Read-only on the core.
 */
public final class ChoirStonesAdapter implements ActivityResultAdapter<ChoirStonesAdapter.Watch> {

    public static final String ACTIVITY_ID = "brew.choir-stones";

    /** Tremor-run snapshot. */
    public record Watch(boolean questComplete, boolean cutOff, int stones, int heldNights, boolean abandoned) {
        public Watch {
            if (stones < 0 || heldNights < 0) throw new IllegalArgumentException("negative watch facts");
            if (questComplete && cutOff) throw new IllegalArgumentException("a completed watch cut nothing off");
        }

        public static Watch of(ChoirStones c, boolean abandoned) {
            boolean done = c.quest().complete();
            ChoirStones.Night last = c.lastNight();
            boolean cut = !done && last != null && !last.held();
            if (!done && !cut && !abandoned) throw new IllegalArgumentException("tremor run still in progress");
            return new Watch(done, cut, c.stones().size(), c.heldNights(), abandoned);
        }

        boolean held() { return questComplete && !cutOff; }
    }

    private final ActivityDefinition definition;

    public ChoirStonesAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "choir-stones-watch", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("listening", "hauling", "observation"),
                Map.of("stones", 64L, "held_nights", 365L, "cut_off", 1L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Watch r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.held() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("stones", Math.min(64L, (long) (r.stones())));
        m.put("held_nights", Math.min(365L, (long) (r.heldNights())));
        m.put("cut_off", Math.min(1L, (long) (r.cutOff() ? 1 : 0)));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
