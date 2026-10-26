// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.brew.week.FirstWeek;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G62 The First Week Home (YTM story ch. 5): the companion that fetched water and foraged with you
 * is credited once per week. Surviving all {@link FirstWeek#DAYS} days completes; a week lost to thirst or hunger
 * fails; a week still running is refused unless abandoned. Read-only on the core.
 */
public final class FirstWeekAdapter implements ActivityResultAdapter<FirstWeekAdapter.Week> {

    public static final String ACTIVITY_ID = "brew.first-week-home";

    /** Survival-week snapshot. */
    public record Week(boolean survived, int days, int health, boolean sick, boolean abandoned) {
        public Week {
            if (days < 0 || days > FirstWeek.DAYS) throw new IllegalArgumentException("days out of range");
            if (health < 0 || health > FirstWeek.MAX) throw new IllegalArgumentException("health out of range");
            if (survived && health == 0) throw new IllegalArgumentException("a survived week keeps some health");
        }

        public static Week of(FirstWeek w, boolean abandoned) {
            boolean over = w.over() || w.lost();
            if (!over && !abandoned) throw new IllegalArgumentException("week still in progress");
            return new Week(over && !w.lost(), Math.min(FirstWeek.DAYS, w.day()), w.health(), w.sick(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public FirstWeekAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "first-week-home", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("foraging", "carrying", "scouting"),
                Map.of("days", 7L, "health", 100L, "sick", 1L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Week r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.survived() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("days", Math.min(7L, (long) (r.days())));
        m.put("health", Math.min(100L, (long) (r.health())));
        m.put("sick", Math.min(1L, (long) (r.sick() ? 1 : 0)));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
