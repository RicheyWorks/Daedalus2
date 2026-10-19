// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.companion.KennelBond;
import com.daedalus.world.companion.KennelGrowth;
import com.daedalus.world.companion.KennelTraining;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Contest gap G75: G12 receipts for the Kennel Isle care quests. G37 "The Keeper's Mark" ({@link BondAdapter}), G61
 * "First Words" ({@link TrainingAdapter}) and G65 "Growing Up" ({@link GrowthAdapter}) each read the quest result
 * the companion code already simulated. {@link #registerAll} adds all three to a router without touching the hub.
 */
public final class KennelCareAdapters {
    public static final String BOND_ID = "kennel.keepers-mark";
    public static final String TRAINING_ID = "kennel.first-words";
    public static final String GROWTH_ID = "kennel.growing-up";
    public static final int MAX_DAYS = 365;

    private KennelCareAdapters() {
    }

    private static ActivityDefinition def(String id, ActivityMode mode, Map<String, Long> max) {
        return new ActivityDefinition(id, id.replace('.', '-'), 1, "kennel-isle", mode, Set.of("animal"),
                Set.of("guarding", "carrying", "companion"), max, 2);
    }

    private static ActivityOutcome outcome(boolean abandoned, boolean complete) {
        return abandoned ? ActivityOutcome.ABANDONED : complete ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
    }

    private static ActivityResultReceipt issue(ActivityDefinition d, ActivityResultAdapter.Session s, ActivityOutcome o,
                                               Map<String, Long> m) {
        return ActivityResultReceipt.issue(d, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(), o,
                s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }

    /** Registers the three kennel care adapters with inactive award policies (husbandry / training tracks). */
    public static void registerAll(ActivityRouter r, ActivityMode mode) {
        r.register(new BondAdapter(mode), BondAdapter.Mark.class, AwardPolicy.inactive(BOND_ID, "mastery.husbandry"));
        r.register(new TrainingAdapter(mode), TrainingAdapter.Words.class,
                AwardPolicy.inactive(TRAINING_ID, "mastery.training"));
        r.register(new GrowthAdapter(mode), GrowthAdapter.Growth.class,
                AwardPolicy.inactive(GROWTH_ID, "mastery.husbandry"));
    }

    /** G37 Keeper's Mark. */
    public static final class BondAdapter implements ActivityResultAdapter<BondAdapter.Mark> {
        public record Mark(boolean complete, int days, int finalBond, boolean abandoned) {
            public Mark {
                if (days < 0 || days > MAX_DAYS || finalBond < 0 || finalBond > 100) {
                    throw new IllegalArgumentException("mark facts do not add up");
                }
            }

            public static Mark of(KennelBond.QuestResult q, boolean abandoned) {
                List<Integer> t = q.trail();
                return new Mark(q.complete(), t.size() - 1, t.get(t.size() - 1), abandoned);
            }
        }

        private final ActivityDefinition definition;

        public BondAdapter(ActivityMode mode) {
            definition = def(BOND_ID, mode, Map.of("complete", 1L, "days", (long) MAX_DAYS, "final_bond", 100L));
        }

        @Override
        public ActivityDefinition definition() {
            return definition;
        }

        @Override
        public ActivityResultReceipt toReceipt(Session s, Mark w) {
            Map<String, Long> m = new LinkedHashMap<>();
            m.put("complete", w.complete() ? 1L : 0L);
            m.put("days", (long) w.days());
            m.put("final_bond", (long) w.finalBond());
            return issue(definition, s, outcome(w.abandoned(), w.complete()), m);
        }
    }

    /** G61 First Words. */
    public static final class TrainingAdapter implements ActivityResultAdapter<TrainingAdapter.Words> {
        public record Words(boolean complete, int sessions, int learned, int finalBond, boolean abandoned) {
            public Words {
                if (sessions < 0 || sessions > KennelTraining.QUEST_SESSIONS || learned < 0 || learned > 5
                    || finalBond < 0 || finalBond > 100) {
                    throw new IllegalArgumentException("words facts do not add up");
                }
            }

            public static Words of(KennelTraining.QuestResult q, boolean abandoned) {
                return new Words(q.complete(), q.sessionsUsed(), q.after().learned().size(), q.after().bond(),
                        abandoned);
            }
        }

        private final ActivityDefinition definition;

        public TrainingAdapter(ActivityMode mode) {
            definition = def(TRAINING_ID, mode, Map.of("complete", 1L, "sessions",
                    (long) KennelTraining.QUEST_SESSIONS, "learned", 5L, "final_bond", 100L));
        }

        @Override
        public ActivityDefinition definition() {
            return definition;
        }

        @Override
        public ActivityResultReceipt toReceipt(Session s, Words w) {
            Map<String, Long> m = new LinkedHashMap<>();
            m.put("complete", w.complete() ? 1L : 0L);
            m.put("sessions", (long) w.sessions());
            m.put("learned", (long) w.learned());
            m.put("final_bond", (long) w.finalBond());
            return issue(definition, s, outcome(w.abandoned(), w.complete()), m);
        }
    }

    /** G65 Growing Up. */
    public static final class GrowthAdapter implements ActivityResultAdapter<GrowthAdapter.Growth> {
        public record Growth(boolean complete, int days, int stage, boolean abandoned) {
            public Growth {
                if (days < 0 || days > MAX_DAYS || stage < 0 || stage >= KennelGrowth.Stage.values().length) {
                    throw new IllegalArgumentException("growth facts do not add up");
                }
            }

            public static Growth of(KennelGrowth.QuestResult q, boolean abandoned) {
                List<KennelGrowth.Stage> t = q.trail();
                return new Growth(q.complete(), t.size() - 1, t.get(t.size() - 1).ordinal(), abandoned);
            }
        }

        private final ActivityDefinition definition;

        public GrowthAdapter(ActivityMode mode) {
            definition = def(GROWTH_ID, mode, Map.of("complete", 1L, "days", (long) MAX_DAYS, "stage",
                    (long) (KennelGrowth.Stage.values().length - 1)));
        }

        @Override
        public ActivityDefinition definition() {
            return definition;
        }

        @Override
        public ActivityResultReceipt toReceipt(Session s, Growth w) {
            Map<String, Long> m = new LinkedHashMap<>();
            m.put("complete", w.complete() ? 1L : 0L);
            m.put("days", (long) w.days());
            m.put("stage", (long) w.stage());
            return issue(definition, s, outcome(w.abandoned(), w.complete()), m);
        }
    }
}