// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.activity.ChalkTrailRunAdapter;
import com.daedalus.world.activity.ProgressionLedger;
import com.daedalus.world.labyrinth.EchoBellGate;
import com.daedalus.world.labyrinth.HornbackHerd;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ActivityRouterTest {

    @Test
    void contestRouterKnowsTheThreeGamesAndPaysNothingUntilPolicyApproved() {
        ActivityRouter r = ActivityRouter.contest(ActivityMode.AUTHORITATIVE);
        assertThat(r.activities()).containsExactly(FishingCastAdapter.ACTIVITY_ID, EchoBellAdapter.ACTIVITY_ID,
                HornbackPassageAdapter.ACTIVITY_ID);
        FishingCastAdapter.Outing o = FishingCastAdapter.Outing.of(ContestAdaptersTest.goodCasts(3), 1, false);
        List<ProgressionLedger.Award> a = r.settle(FishingCastAdapter.ACTIVITY_ID,
                ContestAdaptersTest.session("route-1", ContestAdaptersTest.KITE_RAY), o);
        assertThat(a).singleElement().satisfies(x -> assertThat(x.points()).isZero());
        assertThat(r.history("life:kite-ray-1")).hasSize(1);
    }

    @Test
    void approvedPolicySettlesOnceAndNewRevisionDoesNotRepay() {
        ActivityRouter r = ActivityRouter.contest(ActivityMode.AUTHORITATIVE);
        r.setPolicy(new AwardPolicy(HornbackPassageAdapter.ACTIVITY_ID, 1, "mastery.herding",
                Map.of("calm_arrived", 2L, "guided", 10L), 100));
        HornbackPassageAdapter.Passage p =
                new HornbackPassageAdapter.Passage(HornbackHerd.Outcome.GUIDED, 10, 10, 9, 0, 0, 14, false);
        var s = ContestAdaptersTest.session("herd-9", ContestAdaptersTest.DOG);
        r.settle(HornbackPassageAdapter.ACTIVITY_ID, s, p);
        r.settle(HornbackPassageAdapter.ACTIVITY_ID, s, p);
        assertThat(r.total("life:kennel-dog-4", "mastery.herding")).isEqualTo(28);
        r.setPolicy(new AwardPolicy(HornbackPassageAdapter.ACTIVITY_ID, 2, "mastery.herding", Map.of("guided", 90L), 100));
        r.settle(HornbackPassageAdapter.ACTIVITY_ID, s, p);
        assertThat(r.total("life:kennel-dog-4", "mastery.herding")).isEqualTo(28);
    }

    @Test
    void wrongResultTypeUnknownActivityAndDuplicatesAreRejected() {
        ActivityRouter r = ActivityRouter.contest(ActivityMode.AUTHORITATIVE);
        var s = ContestAdaptersTest.session("bad-1", ContestAdaptersTest.CRICKETS);
        assertThatThrownBy(() -> r.receipt(EchoBellAdapter.ACTIVITY_ID, s, "not a result"))
                .hasMessageContaining("expects Listening");
        assertThatThrownBy(() -> r.receipt("gallery.nope", s, null)).hasMessageContaining("no adapter");
        assertThatThrownBy(() -> r.register(new EchoBellAdapter(ActivityMode.AUTHORITATIVE), EchoBellAdapter.Listening.class,
                AwardPolicy.inactive(EchoBellAdapter.ACTIVITY_ID, "t"))).hasMessageContaining("already registered");
        assertThatThrownBy(() -> r.register(new ChalkTrailRunAdapter(ActivityMode.AUTHORITATIVE), ChalkTrailRunAdapter.Run.class,
                AwardPolicy.inactive(EchoBellAdapter.ACTIVITY_ID, "t"))).hasMessageContaining("policy is for");
        r.register(new ChalkTrailRunAdapter(ActivityMode.AUTHORITATIVE), ChalkTrailRunAdapter.Run.class,
                AwardPolicy.inactive(ChalkTrailRunAdapter.ACTIVITY_ID, "mastery.scouting"));
        assertThat(r.activities()).hasSize(4);
        EchoBellGate g = EchoBellGate.seeded(42L, 2, true);
        assertThat(r.receipt(EchoBellAdapter.ACTIVITY_ID, s,
                EchoBellAdapter.Listening.of(g, g.judge(ContestAdaptersTest.perfectTaps(g)), 1, false)).measures())
                .containsEntry("gate_open", 1L);
    }
}
