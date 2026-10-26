// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;import com.daedalus.world.brew.letters.LettersByArk;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G97 Letters by Ark (YTM story ch. 10): the companion that carried jars down to Dov's post is
 * credited once per chapter run. A finished quest (four shipped, three landed good, two replies, Dov thanked)
 * completes; a chapter still in play is refused unless the host abandoned it. Read-only on the core.
 */
public final class LettersByArkAdapter implements ActivityResultAdapter<LettersByArkAdapter.Post> {

    public static final String ACTIVITY_ID = "brew.letters-by-ark";
    /** Cap on parcel counts. */
    public static final int MAX_PARCELS = 64;

    /** Post snapshot. */
    public record Post(boolean done, int steps, int landedGood, int replies, boolean abandoned) {
        public Post {
            if (steps < 0 || steps > 4) throw new IllegalArgumentException("steps out of range");
            if (landedGood < 0 || replies < 0) throw new IllegalArgumentException("negative post facts");
            if (done && steps != 4) throw new IllegalArgumentException("a done chapter has every step");
        }

        public static Post of(LettersByArk x, boolean abandoned) {
            boolean done = x.quest().complete();
            if (!done && !abandoned) throw new IllegalArgumentException("chapter still in progress");
            int good = (int) x.landed().stream().filter(LettersByArk.Arrival::good).count();
            return new Post(done, done ? 4 : Math.min(3, x.quest().stepIndex()), good, x.replies().size(), abandoned);
        }
    }

    private final ActivityDefinition definition;

    public LettersByArkAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "letters-by-ark", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("hauling", "companionship", "scouting"),
                Map.of("steps", 4L, "landed_good", (long) MAX_PARCELS, "replies", (long) MAX_PARCELS), 2);
    }
    @Override
    public ActivityDefinition definition() { return definition; }
    @Override
    public ActivityResultReceipt toReceipt(Session s, Post r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.done() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("steps", (long) r.steps());
        m.put("landed_good", Math.min((long) MAX_PARCELS, (long) r.landedGood()));
        m.put("replies", Math.min((long) MAX_PARCELS, (long) r.replies()));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}