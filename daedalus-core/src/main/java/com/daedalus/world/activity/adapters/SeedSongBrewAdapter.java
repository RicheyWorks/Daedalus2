// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityDefinition;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.brew.story.SeedSongSpring;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * G12 adapter for G33 The Seed-Song Spring: a companion who brews with you (a goat nosing herbs into the kettle, a
 * wren humming the opening back) is credited, once per session through the G23 {@link ActivityRouter}, for what the
 * {@link SeedSongSpring} rules already decided. Read-only on the brew core. Additive: register it on a router with
 * {@link #register}; the contest router itself is not changed.
 */
public final class SeedSongBrewAdapter implements ActivityResultAdapter<SeedSongBrewAdapter.Evening> {

    public static final String ACTIVITY_ID = "brew.seed-song-spring";
    public static final int MAX_RECORDS = 32;
    public static final int MAX_TRIES = 256;

    /** One brewing evening: records restored, kettles where the needle skipped, springs purified, clean draws. */
    public record Evening(int restored, int skipped, int springsPurified, int cleanDraws, boolean abandoned) {
        public Evening {
            if (restored < 0 || skipped < 0 || springsPurified < 0 || cleanDraws < 0)
                throw new IllegalArgumentException("negative evening facts");
            if (springsPurified > restored)
                throw new IllegalArgumentException("a spring is only purified by a restored record");
        }

        /** The evening between two chapter tallies (taken before and after the session). */
        public static Evening between(SeedSongSpring.Tally before, SeedSongSpring.Tally after, boolean abandoned) {
            return new Evening(after.restored() - before.restored(), after.skipped() - before.skipped(),
                    after.springsPurified() - before.springsPurified(), after.cleanDraws() - before.cleanDraws(),
                    abandoned);
        }
    }

    private final ActivityDefinition definition;

    public SeedSongBrewAdapter(ActivityMode mode) {
        definition = new ActivityDefinition(ACTIVITY_ID, "seed-song-brew-evening", 1, "shattered-planet", mode,
                Set.of("animal", "bird"), Set.of("brewing", "foraging", "listening"),
                Map.of("restored", (long) MAX_RECORDS, "skipped", (long) MAX_TRIES,
                        "springs_purified", (long) MAX_RECORDS, "clean_draws", (long) MAX_TRIES), 2);
    }

    /** Registers this adapter on a router under an inactive policy (points stay an owner decision). */
    public static void register(ActivityRouter router, ActivityMode mode) {
        router.register(new SeedSongBrewAdapter(mode), Evening.class,
                com.daedalus.world.activity.AwardPolicy.inactive(ACTIVITY_ID, "mastery.brewing"));
    }

    @Override
    public ActivityDefinition definition() { return definition; }

    @Override
    public ActivityResultReceipt toReceipt(Session s, Evening e) {
        ActivityOutcome outcome = e.abandoned() ? ActivityOutcome.ABANDONED
                : e.restored() > 0 ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED;
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("restored", (long) e.restored());
        m.put("skipped", (long) e.skipped());
        m.put("springs_purified", (long) e.springsPurified());
        m.put("clean_draws", (long) e.cleanDraws());
        return ActivityResultReceipt.issue(definition, s.resultId(), s.sessionId(), s.issuer(), s.verificationRef(),
                outcome, s.participants(), m, s.sourceEventRefs(), s.clockBoundaryMs());
    }
}
