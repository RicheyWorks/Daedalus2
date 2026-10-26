// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.companion.KennelArkLogs;
import com.daedalus.world.companion.KennelArkMuster;
import com.daedalus.world.companion.KennelRescue;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * G12 receipts for the Kennel Isle ark chapters (contest, art-master-flex): G50 "The Last Ark Bell"
 * ({@link RescueAdapter}), G92 "The Last Kennel Log" ({@link ArkLogsAdapter}) and G107 "The Muster at Hull Bay"
 * ({@link MusterAdapter}). Each reads the result the companion code already simulated; {@link #registerAll} adds all
 * three to a router without touching the hub. Companion of {@link KennelCareAdapters} (G75).
 */
public final class KennelArkAdapters {
    public static final String RESCUE_ID = "kennel.last-ark-bell";
    public static final String ARK_LOGS_ID = "kennel.last-kennel-log";
    public static final String MUSTER_ID = "kennel.muster-at-hull-bay";
    public static final int MAX_DAYS = 365;
    public static final int MAX_SOULS = 999;
    public static final int MAX_TRIPS = 99;

    private KennelArkAdapters() {
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

    /** Registers the three ark chapter adapters with inactive award policies (rescue / lore / husbandry tracks). */
    public static void registerAll(ActivityRouter r, ActivityMode mode) {
        r.register(new RescueAdapter(mode), RescueAdapter.Rescue.class, AwardPolicy.inactive(RESCUE_ID, "mastery.rescue"));
        r.register(new ArkLogsAdapter(mode), ArkLogsAdapter.Log.class, AwardPolicy.inactive(ARK_LOGS_ID, "mastery.lore"));
        r.register(new MusterAdapter(mode), MusterAdapter.Muster.class,
                AwardPolicy.inactive(MUSTER_ID, "mastery.husbandry"));
    }

    /** G50 The Last Ark Bell: souls saved and lost from the hound rescue plan. */
    public static final class RescueAdapter implements ActivityResultAdapter<RescueAdapter.Rescue> {
        public record Rescue(boolean complete, int saved, int lost, int trips, boolean abandoned) {
            public Rescue {
                if (saved < 0 || lost < 0 || saved + lost > MAX_SOULS || trips < 0 || trips > MAX_TRIPS
                        || (complete && saved == 0)) {
                    throw new IllegalArgumentException("rescue facts do not add up");
                }
            }

            /** One wreck run: {@link KennelRescue#plan}; complete when every survivor is saved (Kepler = the chapter). */
            public static Rescue of(KennelRescue.Wreck w, List<KennelRescue.Rescuer> team, int day, boolean abandoned) {
                KennelRescue.Plan p = KennelRescue.plan(w, team, day);
                return new Rescue(p.allSaved(), p.saved(), p.lost(), p.trips(), abandoned);
            }
        }

        private final ActivityDefinition definition;

        public RescueAdapter(ActivityMode mode) {
            definition = def(RESCUE_ID, mode, Map.of("complete", 1L, "saved", (long) MAX_SOULS, "lost", (long) MAX_SOULS,
                    "trips", (long) MAX_TRIPS));
        }

        @Override
        public ActivityDefinition definition() {
            return definition;
        }

        @Override
        public ActivityResultReceipt toReceipt(Session s, Rescue w) {
            Map<String, Long> m = new LinkedHashMap<>();
            m.put("complete", w.complete() ? 1L : 0L);
            m.put("saved", (long) w.saved());
            m.put("lost", (long) w.lost());
            m.put("trips", (long) w.trips());
            return issue(definition, s, outcome(w.abandoned(), w.complete()), m);
        }
    }

    /** G92 The Last Kennel Log: pages found and days used on the drifting plates. */
    public static final class ArkLogsAdapter implements ActivityResultAdapter<ArkLogsAdapter.Log> {
        public record Log(boolean complete, int daysUsed, int pages, boolean abandoned) {
            public Log {
                if (daysUsed < 0 || daysUsed > MAX_DAYS || pages < 0 || pages > KennelArkLogs.FRAGMENTS
                        || (complete && pages != KennelArkLogs.FRAGMENTS)) {
                    throw new IllegalArgumentException("log facts do not add up");
                }
            }

            public static Log of(KennelArkLogs.Hunt h, boolean abandoned) {
                return new Log(h.complete(), h.daysUsed(), h.pages().size(), abandoned);
            }
        }

        private final ActivityDefinition definition;

        public ArkLogsAdapter(ActivityMode mode) {
            definition = def(ARK_LOGS_ID, mode, Map.of("complete", 1L, "days", (long) MAX_DAYS,
                    "pages", (long) KennelArkLogs.FRAGMENTS));
        }

        @Override
        public ActivityDefinition definition() {
            return definition;
        }

        @Override
        public ActivityResultReceipt toReceipt(Session s, Log w) {
            Map<String, Long> m = new LinkedHashMap<>();
            m.put("complete", w.complete() ? 1L : 0L);
            m.put("days", (long) w.daysUsed());
            m.put("pages", (long) w.pages());
            return issue(definition, s, outcome(w.abandoned(), w.complete()), m);
        }
    }

    /** G107 The Muster at Hull Bay: posts filled, crew odds, dawns used and the last roll call's holds. */
    public static final class MusterAdapter implements ActivityResultAdapter<MusterAdapter.Muster> {
        public record Muster(boolean complete, int dawns, int posts, int crewOdds, int lastHolds, boolean abandoned) {
            public Muster {
                int roles = KennelArkMuster.ROLES.size();
                if (dawns < 0 || dawns > KennelArkMuster.QUEST_TRIES || posts < 0 || posts > roles || crewOdds < 0
                        || crewOdds > 100 * posts || lastHolds < 0 || lastHolds > posts
                        || (complete && (dawns == 0 || lastHolds < KennelArkMuster.LAUNCH_NEED))) {
                    throw new IllegalArgumentException("muster facts do not add up");
                }
            }

            public static Muster of(KennelArkMuster.QuestResult q, boolean abandoned) {
                List<Integer> h = q.holdsPerTry();
                return new Muster(q.complete(), q.triesUsed(), q.roster().posts().size(), q.roster().totalPct(),
                        h.isEmpty() ? 0 : h.get(h.size() - 1), abandoned);
            }
        }

        private final ActivityDefinition definition;

        public MusterAdapter(ActivityMode mode) {
            long roles = KennelArkMuster.ROLES.size();
            definition = def(MUSTER_ID, mode, Map.of("complete", 1L, "dawns", (long) KennelArkMuster.QUEST_TRIES,
                    "posts", roles, "crew_odds", 100L * roles, "last_holds", roles));
        }

        @Override
        public ActivityDefinition definition() {
            return definition;
        }

        @Override
        public ActivityResultReceipt toReceipt(Session s, Muster w) {
            Map<String, Long> m = new LinkedHashMap<>();
            m.put("complete", w.complete() ? 1L : 0L);
            m.put("dawns", (long) w.dawns());
            m.put("posts", (long) w.posts());
            m.put("crew_odds", (long) w.crewOdds());
            m.put("last_holds", (long) w.lastHolds());
            return issue(definition, s, outcome(w.abandoned(), w.complete()), m);
        }
    }
}
