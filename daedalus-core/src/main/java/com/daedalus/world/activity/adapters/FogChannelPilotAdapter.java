// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.pilot.FogChannelPilot;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G586 Fog Channel Pilot (2hot2trot): the Daedalus plug-in hook. A host that ran a fog reading
 * snapshots it with {@link Reading#of} and settles it through {@code ActivityRouter.register}; the game keeps its rules
 * and the adapter only maps the {@link FogChannelPilot.Judgement} to bounded measures. The C++ core exposes the same
 * activity id and measure names (FogActivityId, FogMeasures in DaedalusPilotFogChannelCore.h).
 */
public final class FogChannelPilotAdapter implements ActivityResultAdapter<FogChannelPilotAdapter.Reading> {

    public static final String ACTIVITY_ID = "pilot.fog-channel";
    /** Upper bound on any track cost: opening 5, then at most 9 drift and 13 echo per blast. */
    public static final long MAX_COST = 5L + (9L + 13L) * FogChannelPilot.MAX_BLASTS;

    /** Reading snapshot: blasts, cost, par, stars (0-3) and whether the quest was met. */
    public record Reading(int blasts, int cost, int par, int stars, boolean questDone, boolean abandoned) {
        public Reading {
            if (blasts < 0 || blasts > FogChannelPilot.MAX_BLASTS || cost < par || par < 0 || cost > MAX_COST || stars < 1
                    || stars > 3 || questDone != (stars == 3)) {
                throw new IllegalArgumentException("reading facts out of range");
            }
        }

        /** Snapshots the pilot's lanes for a harbour; a list that is not a real track is refused. */
        public static Reading of(FogChannelPilot.Harbour h, int[] lanes, boolean abandoned) {
            FogChannelPilot.Judgement j = FogChannelPilot.judge(h, lanes);
            if (j.cost() == FogChannelPilot.INVALID) {
                throw new IllegalArgumentException("not a track through this harbour");
            }
            return new Reading(h.blasts(), j.cost(), j.par(), j.stars(), j.questDone(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public FogChannelPilotAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "fog-channel-pilot", 1, "shattered-planet", mode,
                Set.of("bird", "animal"), Set.of("navigation", "observation"),
                Map.of("blasts", (long) FogChannelPilot.MAX_BLASTS, "cost", MAX_COST, "over_par", MAX_COST, "stars", 3L,
                        "quest_done", 1L), 2);
    }

    @Override
    public ActivityDefinition definition() {
        return definition;
    }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Reading r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED : r.questDone() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("blasts", (long) r.blasts());
        m.put("cost", (long) r.cost());
        m.put("over_par", (long) (r.cost() - r.par()));
        m.put("stars", (long) r.stars());
        m.put("quest_done", r.questDone() ? 1L : 0L);
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(), o,
                s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
