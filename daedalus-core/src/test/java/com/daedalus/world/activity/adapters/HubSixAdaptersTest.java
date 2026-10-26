// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.activity.ReceiptJournal;
import com.daedalus.world.battlefield.BattlefieldEcology;
import com.daedalus.world.battlefield.BeaverWaters;
import com.daedalus.world.battlefield.BeeBloom;
import com.daedalus.world.battlefield.SalmonRun;
import com.daedalus.world.battlefield.SeedVault;
import com.daedalus.world.battlefield.TrophicCascade;
import com.daedalus.world.battlefield.Vegetation;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Contest G83: receipts hub VI over the landed Pythagoras ecology games, driven by the real game cores. */
class HubSixAdaptersTest {

    static final ActivityParticipant BEAVER =
            new ActivityParticipant("life:ark-beaver-2", ActivityParticipant.Kind.LIFE, "animal", "building");
    static final ActivityParticipant JAY =
            new ActivityParticipant("life:vault-jay-1", ActivityParticipant.Kind.LIFE, "bird", "caching");
    static final ActivityParticipant HIVE =
            new ActivityParticipant("colony:ark-hive-3", ActivityParticipant.Kind.COLONY, "social_insect", "pollinating");
    static final ActivityParticipant WOLF =
            new ActivityParticipant("life:ark-wolf-6", ActivityParticipant.Kind.LIFE, "animal", "hunting");
    static final ActivityParticipant BEAR =
            new ActivityParticipant("life:river-bear-1", ActivityParticipant.Kind.LIFE, "animal", "fishing");

    static ActivityResultAdapter.Session session(String id, ActivityParticipant p) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(p), List.of("evt:" + id), 1_760_872_000_000L);
    }

    // ---- G34 Beaver Waters: the same V valley the game's own tests use ----------------------------------------

    private static final int W = 16;
    private static final int H = 20;

    private static BeaverWaters spring(BeaverWaters.Settings s) {
        int[] g = new int[W * H];
        BattlefieldEcology f = new BattlefieldEcology(W, H, 100, 0, 0, 1);
        for (int j = 0; j < H; j++) {
            for (int i = 0; i < W; i++) {
                g[j * W + i] = 1000 - 40 * j + 30 * Math.abs(i - 8);
                f.set(i, j, i % 3 == 0 ? Vegetation.PINE : Vegetation.MEADOW);
            }
        }
        return BeaverWaters.spring(f, g, 8, 2, new BeaverWaters.Plot(11, 5, 12, 6), new BeaverWaters.Plot(7, 6, 9, 8), s);
    }

    private static void layer(BeaverWaters g, int half) {
        for (int i = 8 - half; i <= 8 + half; i++) {
            g.dam(i, 10);
        }
    }

    @Test
    void beaverWatersSnapshotsTheFinishedSpring() {
        BeaverWatersAdapter a = new BeaverWatersAdapter(ActivityMode.AUTHORITATIVE);
        BeaverWaters dry = spring(new BeaverWaters.Settings(40, 60, 1, 4, 0.75));
        BeaverWatersAdapter.Ponds none = BeaverWatersAdapter.Ponds.of(dry, false);
        assertThat(a.toReceipt(session("bw-0", BEAVER), none).outcome()).isEqualTo(ActivityOutcome.FAILED);

        BeaverWaters g = spring(new BeaverWaters.Settings(40, 60, 1, 4, 0.75));
        layer(g, 4);
        layer(g, 4);
        layer(g, 4);
        assertThat(g.outcome()).isEqualTo(BeaverWaters.Outcome.WET);
        BeaverWatersAdapter.Ponds wet = BeaverWatersAdapter.Ponds.of(g, false);
        ActivityResultReceipt r = a.toReceipt(session("bw-1", BEAVER), wet);
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(r.measures()).containsEntry("wet", 1L).containsEntry("home_flooded", 0L)
                .containsEntry("pond_cells", (long) g.pondCells());
        assertThat(wet.targetWetPm()).isGreaterThanOrEqualTo(750);

        g.dam(8, 10);
        assertThat(wet.pondCells()).as("the snapshot does not follow the live grid").isEqualTo(r.measures().get("pond_cells").intValue());
        assertThatThrownBy(() -> new BeaverWatersAdapter.Ponds(true, true, 1000, 1, 1, 0, 0, false))
                .hasMessageContaining("flooded");
    }

    @Test
    void beaverWatersFloodedHomesteadFails() {
        BeaverWaters g = spring(new BeaverWaters.Settings(400, 60, 0, 4, 0.75));
        for (int n = 0; n < 12 && g.outcome() != BeaverWaters.Outcome.FLOODED; n++) {
            layer(g, 7);
        }
        BeaverWatersAdapter.Ponds p = BeaverWatersAdapter.Ponds.of(g, false);
        assertThat(p.homeFlooded()).isTrue();
        assertThat(new BeaverWatersAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("bw-2", BEAVER), p).outcome())
                .isEqualTo(ActivityOutcome.FAILED);
    }

    // ---- G43 Ark Seed Vault -------------------------------------------------------------------------------------

    private static final SeedVault.Species[] ORTHODOX =
            {SeedVault.Species.WILLOW, SeedVault.Species.MEADOW_GRASS, SeedVault.Species.BRAMBLE, SeedVault.Species.PINE};

    private static SeedVault voyage(boolean regrowOak) {
        SeedVault v = SeedVault.stock(SeedVault.Settings.DEFAULT, 1);
        while (!v.landed()) {
            for (SeedVault.Species sp : ORTHODOX) {
                if (v.moisture(sp) > 6 && v.powerLeft() - 9 >= 18) v.dry(sp, 6);
            }
            if (regrowOak && v.regrowsLeft() > 0) v.regrow(SeedVault.Species.OAK);
            v.year(2);
        }
        return v;
    }

    @Test
    void seedVaultCompletesOnlyWithEveryBandHome() {
        SeedVaultAdapter a = new SeedVaultAdapter(ActivityMode.AUTHORITATIVE);
        SeedVaultAdapter.Voyage all = SeedVaultAdapter.Voyage.of(voyage(true), false);
        assertThat(all.allBands()).isTrue();
        assertThat(a.toReceipt(session("sv-1", JAY), all).measures())
                .containsEntry("all_bands", 1L).containsEntry("surviving_species", 5L);
        SeedVaultAdapter.Voyage noOak = SeedVaultAdapter.Voyage.of(voyage(false), false);
        assertThat(noOak.survivingSpecies()).isEqualTo(4);
        assertThat(a.toReceipt(session("sv-2", JAY), noOak).outcome()).isEqualTo(ActivityOutcome.FAILED);
    }

    @Test
    void seedVaultRefusesAVoyageStillAtSea() {
        SeedVault atSea = SeedVault.stock(SeedVault.Settings.DEFAULT, 1);
        atSea.year(2);
        assertThatThrownBy(() -> SeedVaultAdapter.Voyage.of(atSea, false)).hasMessageContaining("in progress");
        SeedVaultAdapter.Voyage quit = SeedVaultAdapter.Voyage.of(atSea, true);
        assertThat(new SeedVaultAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("sv-3", JAY), quit).outcome())
                .isEqualTo(ActivityOutcome.ABANDONED);
    }

    // ---- G48 Bee Bloom ------------------------------------------------------------------------------------------

    @Test
    void beeBloomCreditsTheHivesForAThrivingSeason() {
        BeeBloom.Settings d = BeeBloom.Settings.DEFAULT;
        BeeBloom.Settings calm = new BeeBloom.Settings(d.days(), d.coldC(), d.peakC(), d.noiseC(), 0.0, d.frostFrom(),
                d.frostTo(), d.baseC(), d.flightC(), d.hiveWakeGdd(), d.visitsPerHive(), d.starveDays(), 0, d.beds(),
                d.hives(), d.thriveSet());
        BeeBloom b = BeeBloom.season(calm, 2);
        b.sow(BeeBloom.Flora.WILLOW_CATKIN, 1);
        b.sow(BeeBloom.Flora.CROCUS, 1);
        b.sow(BeeBloom.Flora.CLOVER, 2);
        b.sow(BeeBloom.Flora.BRAMBLE, 1);
        b.sow(BeeBloom.Flora.HEATHER, 1);
        b.hive(3);
        BeeBloomAdapter.Season s = BeeBloomAdapter.Season.of(b.run(), false);
        assertThat(s.thriving()).isTrue();
        assertThat(s.frostDayPlusOne()).isZero();
        BeeBloomAdapter a = new BeeBloomAdapter(ActivityMode.AUTHORITATIVE);
        assertThat(a.toReceipt(session("bb-1", HIVE), s).measures()).containsEntry("hives_alive", 3L);

        BeeBloom late = BeeBloom.season(calm, 1);
        late.sow(BeeBloom.Flora.HEATHER, 6);
        late.hive(3);
        BeeBloomAdapter.Season starved = BeeBloomAdapter.Season.of(late.run(), false);
        assertThat(a.toReceipt(session("bb-2", HIVE), starved).outcome()).isEqualTo(ActivityOutcome.FAILED);
    }

    // ---- G58 Trophic Cascade ------------------------------------------------------------------------------------

    @Test
    void trophicCascadeCreditsTheWolvesForTheFearNotTheCull() {
        TrophicCascadeAdapter a = new TrophicCascadeAdapter(ActivityMode.AUTHORITATIVE);
        TrophicCascade wolves = TrophicCascade.valley(TrophicCascade.Settings.DEFAULT, 1);
        wolves.release(0, 6);
        TrophicCascadeAdapter.Valley home = TrophicCascadeAdapter.Valley.of(wolves.run(), false);
        assertThat(home.cascade()).isTrue();
        assertThat(home.colonies()).isPositive();
        assertThat(a.toReceipt(session("tc-1", WOLF), home).outcome()).isEqualTo(ActivityOutcome.COMPLETED);

        TrophicCascade hunted = TrophicCascade.valley(TrophicCascade.Settings.DEFAULT, 1);
        hunted.cull(60);
        TrophicCascadeAdapter.Valley culled = TrophicCascadeAdapter.Valley.of(hunted.run(), false);
        assertThat(culled.elk()).isLessThan(home.elk());
        assertThat(a.toReceipt(session("tc-2", WOLF), culled).outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new TrophicCascadeAdapter.Valley(true, 1001, 0, 0, 0, 0, false))
                .hasMessageContaining("willow");
    }

    // ---- G71 Salmon Run -----------------------------------------------------------------------------------------

    @Test
    void salmonRunCreditsTheRestoredRunAndRefusesNoCredit() {
        SalmonRunAdapter a = new SalmonRunAdapter(ActivityMode.AUTHORITATIVE);
        SalmonRun works = SalmonRun.river(SalmonRun.Settings.DEFAULT, 1);
        works.buildLadder();
        for (int i = 0; i < SalmonRun.Settings.DEFAULT.maxPonds(); i++) works.pond();
        works.harvest(0.4);
        SalmonRunAdapter.Run run = SalmonRunAdapter.Run.of(works.run(), false);
        assertThat(run.restored()).isTrue();
        assertThat(run.totalCatch()).isPositive();
        assertThat(a.toReceipt(session("sr-1", BEAR), run).outcome()).isEqualTo(ActivityOutcome.COMPLETED);

        SalmonRun greedy = SalmonRun.river(SalmonRun.Settings.DEFAULT, 1);
        greedy.harvest(0.85);
        SalmonRunAdapter.Run out = SalmonRunAdapter.Run.of(greedy.run(), false);
        assertThat(out.fishedOut()).isTrue();
        assertThat(a.toReceipt(session("sr-2", BEAR), out).measures()).containsEntry("fished_out", 1L);
        assertThatThrownBy(() -> new SalmonRunAdapter.Run(false, false, -1, 0, 0, 0, false))
                .hasMessageContaining("negative");
    }

    // ---- the hub ------------------------------------------------------------------------------------------------

    @Test
    void contestAllRoutesHubSixSettlesOnceAndReplays() {
        ActivityRouter r = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        assertThat(r.activities()).contains(BeaverWatersAdapter.ACTIVITY_ID, SeedVaultAdapter.ACTIVITY_ID,
                BeeBloomAdapter.ACTIVITY_ID, TrophicCascadeAdapter.ACTIVITY_ID, SalmonRunAdapter.ACTIVITY_ID);
        r.setPolicy(new AwardPolicy(TrophicCascadeAdapter.ACTIVITY_ID, 1, "mastery.hunting",
                Map.of("cascade", 25L), 40));
        TrophicCascadeAdapter.Valley v = new TrophicCascadeAdapter.Valley(true, 420, 2, 300, 12, 30, false);
        r.settle(TrophicCascadeAdapter.ACTIVITY_ID, session("route-tc", WOLF), v);
        r.settle(TrophicCascadeAdapter.ACTIVITY_ID, session("route-tc", WOLF), v);
        assertThat(r.total("life:ark-wolf-6", "mastery.hunting")).isEqualTo(25);
        assertThat(r.journal()).hasSize(1);

        ActivityRouter restarted = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        restarted.setPolicy(new AwardPolicy(TrophicCascadeAdapter.ACTIVITY_ID, 1, "mastery.hunting",
                Map.of("cascade", 25L), 40));
        assertThat(restarted.replay(r.journal())).isEqualTo(1);
        assertThat(restarted.total("life:ark-wolf-6", "mastery.hunting")).isEqualTo(25);
        assertThat(ReceiptJournal.readAll(r.journal())).hasSize(1);
        assertThatThrownBy(() -> r.settle(SalmonRunAdapter.ACTIVITY_ID, session("route-x", BEAR), v))
                .hasMessageContaining("expects");
    }
}