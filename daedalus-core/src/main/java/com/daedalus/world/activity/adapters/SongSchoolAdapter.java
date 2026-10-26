// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.brew.school.SongSchool;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G116 The Song School (YTM story ch. 11): the companion that sat in on Old Wick's lessons is credited
 * once per term. Graduating {@link SongSchool#GRADUATES_NEEDED} pupils completes; a term still under way is refused
 * unless the host abandoned it. Read-only on the core.
 */
public final class SongSchoolAdapter implements ActivityResultAdapter<SongSchoolAdapter.Term> {

    public static final String ACTIVITY_ID = "brew.song-school";
    /** Cap on the graduates measure. */
    public static final int MAX_PUPILS = 32;
    /** Cap on the days measure. */
    public static final int MAX_DAYS = 365;

    /** Term snapshot. */
    public record Term(int graduates, int days, boolean abandoned) {
        public Term {
            if (graduates < 0 || days < 0) throw new IllegalArgumentException("negative term facts");
        }

        public static Term of(SongSchool school, boolean abandoned) {
            int g = school.graduates().size();
            if (g < SongSchool.GRADUATES_NEEDED && !abandoned)
                throw new IllegalArgumentException("term still in progress");
            return new Term(g, school.day(), abandoned);
        }

        public boolean graduated() { return graduates >= SongSchool.GRADUATES_NEEDED; }
    }

    private final ActivityDefinition definition;

    public SongSchoolAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "song-school", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("listening", "singing", "companionship"),
                Map.of("graduates", (long) MAX_PUPILS, "days", (long) MAX_DAYS), 2);
    }
    @Override
    public ActivityDefinition definition() { return definition; }
    @Override
    public ActivityResultReceipt toReceipt(Session s, Term r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.graduated() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("graduates", Math.min((long) MAX_PUPILS, (long) r.graduates()));
        m.put("days", Math.min((long) MAX_DAYS, (long) r.days()));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}