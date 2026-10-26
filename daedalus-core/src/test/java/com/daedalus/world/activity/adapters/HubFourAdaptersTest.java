// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.audio.HerbChordGarden;
import com.daedalus.world.companion.KennelPantry;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class HubFourAdaptersTest {

    static final ActivityParticipant TANK =
            new ActivityParticipant("life:tank-corso", ActivityParticipant.Kind.LIFE, "animal", "guarding");
    static final ActivityParticipant HIVE =
            new ActivityParticipant("colony:chord-bees-1", ActivityParticipant.Kind.COLONY, "social_insect", "pollinating");

    static ActivityResultAdapter.Session session(String id, ActivityParticipant p) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(p), List.of("evt:" + id), 1_760_872_000_000L);
    }

    static final List<KennelPantry.Pet> PACK = List.of(new KennelPantry.Pet("pip", "pup"),
            new KennelPantry.Pet("rex", "dog"), new KennelPantry.Pet("tank", "cane_corso"),
            new KennelPantry.Pet("bo", "dog"));

    static KennelPantry pantry() throws Exception {
        Path p = Path.of("..", "data", "islands", "kennel-food-v1.json");
        return KennelPantry.load(Files.exists(p) ? p : Path.of("data", "islands", "kennel-food-v1.json"));
    }

    @Test
    void pantryReadsARealPackOrderQuest() throws Exception {
        KennelPantry k = pantry();
        KennelPantry.QuestResult fail = k.packOrder(PACK, new KennelPantry.Day(2, 1, 5));
        KennelPantryAdapter.Feeding f = KennelPantryAdapter.Feeding.of(fail, false);
        assertThat(f.passed()).isFalse();
        assertThat(f.days()).isEqualTo(fail.log().size());
        KennelPantryAdapter a = new KennelPantryAdapter(ActivityMode.AUTHORITATIVE);
        assertThat(a.toReceipt(session("kp-1", TANK), f).outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThat(a.toReceipt(session("kp-2", TANK), new KennelPantryAdapter.Feeding(true, 7, 0, 20, 28, 1, false))
                .outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThatThrownBy(() -> new KennelPantryAdapter.Feeding(true, 1, 2, 0, 0, 0, false))
                .hasMessageContaining("add up");
    }

    @Test
    void herbGardenReadsAJudgedBed() {
        HerbChordGarden g = HerbChordGarden.seeded(55L);
        HerbChordGarden.Verdict best = g.judge(g.solution());
        HerbGardenAdapter.Planting p = HerbGardenAdapter.Planting.of(best, false);
        assertThat(p.perfect()).isTrue();
        assertThat(p.lines()).isEqualTo(g.target());
        ActivityResultReceipt r = new HerbGardenAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("hg-1", HIVE), p);
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(r.measures()).containsEntry("perfect", 1L);
        assertThatThrownBy(() -> new HerbGardenAdapter.Planting(0, 3, true, false)).hasMessageContaining("target");
    }

    @Test
    void contestAllRoutesHubFourAndJournalsOnce() {
        ActivityRouter r = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        assertThat(r.activities()).hasSizeGreaterThanOrEqualTo(13).contains(KennelPantryAdapter.ACTIVITY_ID, HerbGardenAdapter.ACTIVITY_ID);
        r.setPolicy(new AwardPolicy(HerbGardenAdapter.ACTIVITY_ID, 1, "mastery.pollination", Map.of("lines", 2L), 20));
        HerbGardenAdapter.Planting p = new HerbGardenAdapter.Planting(4, 4, true, false);
        r.settle(HerbGardenAdapter.ACTIVITY_ID, session("route-hg", HIVE), p);
        r.settle(HerbGardenAdapter.ACTIVITY_ID, session("route-hg", HIVE), p);
        assertThat(r.total("colony:chord-bees-1", "mastery.pollination")).isEqualTo(8);
        assertThat(r.journal()).hasSize(1);
    }
}
