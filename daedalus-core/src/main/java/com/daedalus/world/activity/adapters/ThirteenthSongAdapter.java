// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.brew.song.ThirteenthSong;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G94 The Thirteenth Song (YTM story ch. 9): the companion that hummed the guests' verses back is
 * credited once per composing session. A brewed (or catalogued) island song completes; anything before that is
 * refused unless the host abandoned the session. Read-only on the core.
 */
public final class ThirteenthSongAdapter implements ActivityResultAdapter<ThirteenthSongAdapter.Composing> {

    public static final String ACTIVITY_ID = "brew.thirteenth-song";

    /** Composing snapshot. */
    public record Composing(boolean brewed, int verses, boolean composed, boolean abandoned) {
        public Composing {
            if (verses < 0 || verses > 32) throw new IllegalArgumentException("verses out of range");
            if (brewed && !composed) throw new IllegalArgumentException("only a composed song can be brewed");
        }

        public static Composing of(ThirteenthSong t, boolean abandoned) {
            boolean brewed = t.brewed() || t.quest().complete();
            if (!brewed && !abandoned) throw new IllegalArgumentException("song still in progress");
            return new Composing(brewed, t.gathered().size(), t.song() != null || brewed, abandoned);
        }
    }

    private final ActivityDefinition definition;

    public ThirteenthSongAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "thirteenth-song", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("listening", "singing", "companionship"),
                Map.of("verses", 32L, "composed", 1L, "brewed", 1L), 2);
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Composing r) {
        ActivityOutcome o = r.abandoned() ? ActivityOutcome.ABANDONED
                : r.brewed() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("verses", Math.min(32L, (long) (r.verses())));
        m.put("composed", Math.min(1L, (long) (r.composed() ? 1 : 0)));
        m.put("brewed", Math.min(1L, (long) (r.brewed() ? 1 : 0)));
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                o, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
