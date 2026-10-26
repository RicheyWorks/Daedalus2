// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.odds.ledger.KeepersLedgerQuest;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
/**
 * G12 adapter for G56 The Keeper's Ledger: the companion that kept the tally learns from the closed ledger. DOUBLED
 * completes; BROKE or OUT_OF_WAGERS is a failure; a ledger still OPEN is refused unless the host abandoned it.
 */
public final class KeepersLedgerAdapter implements ActivityResultAdapter<KeepersLedgerAdapter.Ledger> {

    public static final String ACTIVITY_ID = "odds.keepers-ledger";

    /** Ledger snapshot; keepers_mark means doubled without ever staking over the Kelly advice. */
    public record Ledger(boolean doubled, boolean keepersMark, int balance, int wagers, int disciplined,
                         boolean abandoned) {
        public Ledger {
            if (balance < 0 || wagers < 0 || disciplined < 0) throw new IllegalArgumentException("negative ledger facts");
            if (disciplined > wagers) throw new IllegalArgumentException("disciplined exceeds wagers");
            if (wagers > KeepersLedgerQuest.MAX_WAGERS) throw new IllegalArgumentException("wagers out of range");
            if (keepersMark && !doubled) throw new IllegalArgumentException("the Keeper's Mark needs a doubled ledger");
        }

        public static Ledger of(KeepersLedgerQuest q, boolean abandoned) {
            if (q.stage() == KeepersLedgerQuest.Stage.OPEN && !abandoned)
                throw new IllegalArgumentException("ledger still in progress: OPEN");
            return new Ledger(q.stage() == KeepersLedgerQuest.Stage.DOUBLED, q.keepersMark(), q.balance(),
                    q.history().size(), q.disciplined(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public KeepersLedgerAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "keepers-ledger", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("counting", "observation"),
                Map.of("doubled", 1L, "keepers_mark", 1L, "balance", 1_000_000L,
                        "wagers", (long) KeepersLedgerQuest.MAX_WAGERS, "disciplined", (long) KeepersLedgerQuest.MAX_WAGERS), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Ledger l) {
        ActivityOutcome o = l.abandoned() ? ActivityOutcome.ABANDONED
                : l.doubled() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("doubled", l.doubled() ? 1L : 0L);
        m.put("keepers_mark", l.keepersMark() ? 1L : 0L);
        m.put("balance", Math.min(1_000_000L, l.balance()));
        m.put("wagers", (long) l.wagers());
        m.put("disciplined", (long) l.disciplined());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}