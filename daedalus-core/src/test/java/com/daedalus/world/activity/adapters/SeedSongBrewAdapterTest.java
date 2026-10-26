// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.brew.story.SeedSongSpring;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class SeedSongBrewAdapterTest {

    static final ActivityParticipant GOAT =
            new ActivityParticipant("life:homestead-goat-2", ActivityParticipant.Kind.LIFE, "animal", "brewing");

    static ActivityResultAdapter.Session session(String id) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "ytm-host", "verify:" + id,
                List.of(GOAT), List.of("evt:" + id), 1_760_866_000_000L);
    }

    @Test
    void aCompanionWhoBrewsWithYouIsCreditedOnceThroughTheRouter() {
        ActivityRouter r = new ActivityRouter();
        SeedSongBrewAdapter.register(r, ActivityMode.AUTHORITATIVE);
        assertThat(r.activities()).containsExactly(SeedSongBrewAdapter.ACTIVITY_ID);
        r.setPolicy(new AwardPolicy(SeedSongBrewAdapter.ACTIVITY_ID, 1, "mastery.brewing",
                Map.of("restored", 5L, "springs_purified", 3L), 100));
        var e = SeedSongBrewAdapter.Evening.between(new SeedSongSpring.Tally(1, 0, 1, 0),
                new SeedSongSpring.Tally(3, 2, 3, 1), false);
        assertThat(e).isEqualTo(new SeedSongBrewAdapter.Evening(2, 2, 2, 1, false));
        r.settle(SeedSongBrewAdapter.ACTIVITY_ID, session("eve-1"), e);
        r.settle(SeedSongBrewAdapter.ACTIVITY_ID, session("eve-1"), e);
        assertThat(r.total("life:homestead-goat-2", "mastery.brewing")).isEqualTo(16);
        var rec = r.receipt(SeedSongBrewAdapter.ACTIVITY_ID, session("eve-1"), e);
        assertThat(rec.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(rec.measures()).containsEntry("restored", 2L).containsEntry("skipped", 2L)
                .containsEntry("springs_purified", 2L).containsEntry("clean_draws", 1L);
    }

    @Test
    void outcomesAndBounds() {
        var a = new SeedSongBrewAdapter(ActivityMode.AUTHORITATIVE);
        assertThat(a.toReceipt(session("x1"), new SeedSongBrewAdapter.Evening(0, 3, 0, 0, false)).outcome())
                .isEqualTo(ActivityOutcome.FAILED);
        assertThat(a.toReceipt(session("x2"), new SeedSongBrewAdapter.Evening(1, 0, 1, 0, true)).outcome())
                .isEqualTo(ActivityOutcome.ABANDONED);
        assertThatThrownBy(() -> new SeedSongBrewAdapter.Evening(-1, 0, 0, 0, false)).hasMessageContaining("negative");
        assertThatThrownBy(() -> new SeedSongBrewAdapter.Evening(1, 0, 2, 0, false)).hasMessageContaining("purified");
        assertThatThrownBy(() -> a.toReceipt(session("x3"), new SeedSongBrewAdapter.Evening(33, 0, 0, 0, false)))
                .hasMessageContaining("out of bounds");
        assertThat(a.definition().activityId()).isEqualTo("brew.seed-song-spring");
    }
}
