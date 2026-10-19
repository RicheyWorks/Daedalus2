// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.battlefield.AshfallRegrowth;
import com.daedalus.world.battlefield.FirelineWarden;
import com.daedalus.world.companion.KennelWaterLoop;
import com.daedalus.world.forge.ForgeGrades.Material;
import com.daedalus.world.forge.TemperForge;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class HubThreeAdaptersTest {

    static final ActivityParticipant CORSO =
            new ActivityParticipant("life:tank-corso", ActivityParticipant.Kind.LIFE, "animal", "guarding");
    static final ActivityParticipant MULE =
            new ActivityParticipant("life:forge-mule-1", ActivityParticipant.Kind.LIFE, "animal", "carrying");
    static final ActivityParticipant JAY =
            new ActivityParticipant("life:ash-jay-3", ActivityParticipant.Kind.LIFE, "bird", "seeding");

    static ActivityResultAdapter.Session session(String id, ActivityParticipant p) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(p), List.of("evt:" + id), 1_760_872_000_000L);
    }

    @Test
    void kennelWaterReadsARealQuietSpring() throws Exception {
        Path p = Path.of("..", "data", "islands", "kennel-water-v1.json");
        KennelWaterLoop w = KennelWaterLoop.load(Files.exists(p) ? p : Path.of("data", "islands", "kennel-water-v1.json"));
        List<KennelWaterLoop.Animal> pack = List.of(new KennelWaterLoop.Animal("rex", "dog"),
                new KennelWaterLoop.Animal("tank", "cane_corso"), new KennelWaterLoop.Animal("g1", "goat"));
        KennelWaterLoop.QuestResult q = w.quietSpring(pack, 0, List.of(5, 1));
        KennelWaterAdapter.Watch watch = KennelWaterAdapter.Watch.of(q, false);
        assertThat(watch.passed()).isEqualTo(q.passed());
        assertThat(watch.days()).isEqualTo(q.log().size());
        ActivityResultReceipt r = new KennelWaterAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("kw-1", CORSO), watch);
        assertThat(r.outcome()).isEqualTo(q.passed() ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new KennelWaterAdapter.Watch(true, 1, 2, 0, 0, false)).hasMessageContaining("add up");
    }

    @Test
    void temperForgeReadsAJudgedBlade() {
        TemperForge.Blank b = TemperForge.blank(Material.STEEL, 7);
        TemperForge.Result ideal = TemperForge.judge(b, TemperForge.idealRun(b, TemperForge.Quench.SPRING));
        TemperForgeAdapter.Temper t = TemperForgeAdapter.Temper.of(ideal, false);
        assertThat(t.cracked()).isFalse();
        assertThat(t.perfectStrikes()).isEqualTo(b.strikes());
        ActivityResultReceipt r = new TemperForgeAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("tf-1", MULE), t);
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(r.measures()).containsEntry("temper", (long) ideal.temper());
        assertThatThrownBy(() -> new TemperForgeAdapter.Temper(1, 1, 1, 0, true, 1, true, false))
                .hasMessageContaining("ark plate");
    }

    @Test
    void ashfallMapsOutcomeAndOldGrowth() {
        AshfallRegrowth.Report rep = new AshfallRegrowth.Report(AshfallRegrowth.Outcome.RESTORED, 12, 0.4567,
                Map.of(), 1, 3, 2, 1);
        AshfallRegrowthAdapter.Regrowth g = AshfallRegrowthAdapter.Regrowth.of(rep, false);
        assertThat(g.oldGrowthPm()).isEqualTo(457);
        ActivityResultReceipt r = new AshfallRegrowthAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("ash-1", JAY), g);
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        AshfallRegrowth.Report scorched = new AshfallRegrowth.Report(AshfallRegrowth.Outcome.SCORCHED, 4, 0, Map.of(),
                3, 90, 0, 0);
        assertThat(new AshfallRegrowthAdapter(ActivityMode.AUTHORITATIVE)
                .toReceipt(session("ash-2", JAY), AshfallRegrowthAdapter.Regrowth.of(scorched, false)).outcome())
                .isEqualTo(ActivityOutcome.FAILED);
    }

    @Test
    void firelineRefusesAFireStillBurning() {
        FirelineWarden.Report held = new FirelineWarden.Report(FirelineWarden.Outcome.HELD, 300, 0.81, 40, 12, 6, 2, 3);
        FirelineWardenAdapter.Defence d = FirelineWardenAdapter.Defence.of(held, false);
        assertThat(d.result()).isEqualTo(1);
        assertThat(d.savedPm()).isEqualTo(810);
        assertThat(new FirelineWardenAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("fw-1", MULE), d).outcome())
                .isEqualTo(ActivityOutcome.COMPLETED);
        FirelineWarden.Report burning = new FirelineWarden.Report(FirelineWarden.Outcome.BURNING, 10, 0.9, 1, 0, 0, 0, 5);
        assertThatThrownBy(() -> FirelineWardenAdapter.Defence.of(burning, false)).hasMessageContaining("still burning");
    }

    @Test
    void contestAllRoutesElevenGamesAndSettlesOnce() {
        ActivityRouter r = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        assertThat(r.activities()).hasSizeGreaterThanOrEqualTo(11).contains(KennelWaterAdapter.ACTIVITY_ID, TemperForgeAdapter.ACTIVITY_ID,
                AshfallRegrowthAdapter.ACTIVITY_ID, FirelineWardenAdapter.ACTIVITY_ID);
        r.setPolicy(new AwardPolicy(FirelineWardenAdapter.ACTIVITY_ID, 1, "mastery.firefighting",
                Map.of("result", 10L), 50));
        FirelineWardenAdapter.Defence saved = new FirelineWardenAdapter.Defence(2, 200, 950, 5, 8, 4, 1, false);
        r.settle(FirelineWardenAdapter.ACTIVITY_ID, session("route-fw", MULE), saved);
        r.settle(FirelineWardenAdapter.ACTIVITY_ID, session("route-fw", MULE), saved);
        assertThat(r.total("life:forge-mule-1", "mastery.firefighting")).isEqualTo(20);
    }
}
