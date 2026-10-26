// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.odds.insurance.UnderwriterQuest;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
/**
 * G12 adapter for G80 The Ark Underwriter: the ledger-keeping companion learns from one insured season. SOLVENT
 * completes; BUST is a failure. QUOTING, REJECTED (the player may quote again) and APPROVED are still in progress
 * and refused unless the host abandoned the quest. Herbs are rounded; a bust records its shortfall.
 */
public final class ArkUnderwriterAdapter implements ActivityResultAdapter<ArkUnderwriterAdapter.Season> {

    public static final String ACTIVITY_ID = "odds.ark-underwriter";

    /** Season snapshot; bust risk is the approved board's insolvency in per mille. */
    public record Season(boolean solvent, int closeHerbs, int shortfallHerbs, int bustRiskPm, boolean abandoned) {
        public Season {
            if (closeHerbs < 0 || shortfallHerbs < 0) throw new IllegalArgumentException("negative season facts");
            if (bustRiskPm < 0 || bustRiskPm > 1000) throw new IllegalArgumentException("bust risk out of 0-1000");
            if (solvent && shortfallHerbs > 0) throw new IllegalArgumentException("a solvent pool has no shortfall");
        }

        public static Season of(UnderwriterQuest q, boolean abandoned) {
            UnderwriterQuest.Stage st = q.stage();
            boolean done = st == UnderwriterQuest.Stage.SOLVENT || st == UnderwriterQuest.Stage.BUST;
            if (!done && !abandoned) throw new IllegalArgumentException("season still in progress: " + st);
            int risk = q.board() == null ? 0
                    : (int) Math.max(0, Math.min(1000, Math.round(q.board().insolvency() * 1000)));
            long close = done ? Math.round(q.close()) : 0L;
            return new Season(st == UnderwriterQuest.Stage.SOLVENT, (int) Math.max(0, Math.min(1_000_000, close)),
                    (int) Math.max(0, Math.min(1_000_000, -close)), risk, abandoned);
        }
    }

    private final ActivityDefinition definition;

    public ArkUnderwriterAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "ark-underwriter", 1, "sky-islands", mode,
                Set.of("animal", "bird"), Set.of("counting", "guarding"),
                Map.of("solvent", 1L, "close_herbs", 1_000_000L, "shortfall_herbs", 1_000_000L,
                        "bust_risk_pm", 1000L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Season r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.solvent() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("solvent", r.solvent() ? 1L : 0L);
        m.put("close_herbs", (long) r.closeHerbs());
        m.put("shortfall_herbs", (long) r.shortfallHerbs());
        m.put("bust_risk_pm", (long) r.bustRiskPm());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}