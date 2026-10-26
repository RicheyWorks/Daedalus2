// SPDX-License-Identifier: MIT
package com.daedalus.world.ark.supply;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for the Ark Supply Run: the animal crew that carried the cargo learns logistics (role
 * {@code carrying}) from the settled {@link SupplyRun.Delivery}. Complete deliveries complete; short ones are a
 * settleable failure; a run abandoned at the pier pays nothing.
 */
public final class SupplyRunAdapter implements ActivityResultAdapter<SupplyRunAdapter.Run> {

    public static final String ACTIVITY_ID = "ark.supply-run";

    /** A settled delivery, or an abandoned run. */
    public record Run(int watches, int kgCarried, int requestsMet, int requestsTotal, int passengersFed,
                      int passengersTotal, boolean abandoned) {
        public Run {
            if (watches < 0 || kgCarried < 0 || requestsMet < 0 || requestsMet > requestsTotal || passengersFed < 0
                    || passengersFed > passengersTotal)
                throw new IllegalArgumentException("run facts do not add up");
        }

        public static Run of(SupplyRun.Delivery d) {
            return new Run(d.watches(), d.kgCarried(), d.requestsMet(), d.requestsTotal(), d.passengersFed(),
                    d.passengersTotal(), false);
        }

        public boolean complete() { return requestsMet == requestsTotal && passengersFed == passengersTotal; }
    }

    private final ActivityDefinition definition;

    public SupplyRunAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "ark-supply-run", 1, "sky-islands", mode,
                Set.of("animal", "bird", "social_insect"), Set.of("carrying", "logistics", "guarding"),
                Map.of("watches", 10_000L, "kg_carried", (long) SupplyRun.HOLD_KG, "requests_met", 16L,
                        "requests_total", 16L, "passengers_fed", 64L, "passengers_total", 64L), 16);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Run r) {
        ActivityOutcome outcome = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.complete() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("watches", (long) r.watches());
        m.put("kg_carried", (long) r.kgCarried());
        m.put("requests_met", (long) r.requestsMet());
        m.put("requests_total", (long) r.requestsTotal());
        m.put("passengers_fed", (long) r.passengersFed());
        m.put("passengers_total", (long) r.passengersTotal());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                outcome, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
