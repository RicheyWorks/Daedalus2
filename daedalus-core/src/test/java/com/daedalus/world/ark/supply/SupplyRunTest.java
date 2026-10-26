// SPDX-License-Identifier: MIT
package com.daedalus.world.ark.supply;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.activity.ProgressionLedger;
import com.daedalus.world.ark.ArkFleet;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class SupplyRunTest {

    static final BlockCoordinate FROM = new BlockCoordinate(0, 40, 0);
    static final BlockCoordinate TO = new BlockCoordinate(480, 40, 0);
    static final List<Passenger> PASSENGERS = List.of(
            new Passenger("life:woolback-ewe-2", "animal", 1, 1),
            new Passenger("colony:emberbee-hive-2", "social_insect", 0, 0),
            new Passenger("life:mossback-hound-07", "animal", 1, 0));
    static final List<CrewMember> CREW = List.of(
            new CrewMember("life:easel-mule-1", "animal", 60, 10),
            new CrewMember("life:ark-goat-3", "animal", 25, 8));
    static final List<SupplyRequest> REQUESTS = List.of(
            new SupplyRequest("isle-a-0", Cargo.SEED_CACHE, 4),
            new SupplyRequest("isle-a-1", Cargo.WATER_CASK, 5),
            new SupplyRequest("isle-a-2", Cargo.TIMBER_BUNDLE, 2));

    static SupplyRun run() { return new SupplyRun("ark-3", FROM, TO, PASSENGERS, CREW, REQUESTS); }

    @Test
    void voyageLengthComesFromArkFleetAndSetsRations() {
        SupplyRun r = run();
        assertThat(r.durationMs()).isEqualTo(ArkFleet.duration(FROM, TO));
        int watches = (int) ((r.durationMs() + SupplyRun.WATCH_MS - 1) / SupplyRun.WATCH_MS);
        assertThat(r.watches()).isEqualTo(watches).isPositive();
        assertThat(r.waterNeeded()).isEqualTo(2 * watches);
        assertThat(r.fodderNeeded()).isEqualTo(watches);
        assertThat(r.crewCapacityKg()).isEqualTo(800);
    }

    @Test
    void fullLoadIsReadyAndDeliversExactlyOnce() {
        SupplyRun r = run();
        Load.full(r);
        assertThat(r.check().ready()).isTrue();
        r.depart(1_000);
        assertThat(r.deliver(1_000)).isEmpty();
        SupplyRun.Delivery d = r.deliver(1_000 + r.durationMs()).orElseThrow();
        assertThat(d.complete()).isTrue();
        assertThat(d.requestsMet()).isEqualTo(3);
        assertThat(d.passengersFed()).isEqualTo(3);
        assertThat(d.arrivedAtMs()).isEqualTo(1_000 + r.durationMs());
        assertThat(r.deliver(999_999)).contains(d);
        assertThat(r.status()).isEqualTo(SupplyRun.Status.DELIVERED);
        assertThatThrownBy(() -> r.load(Cargo.SALVE_JAR, 1)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void rationsComeOffTheTopBeforeRequests() {
        SupplyRun r = run();
        r.load(Cargo.SEED_CACHE, 4);
        r.load(Cargo.TIMBER_BUNDLE, 2);
        r.load(Cargo.WATER_CASK, r.waterNeeded()); // rations only: the request's 5 casks are missing
        r.load(Cargo.FODDER_BALE, r.fodderNeeded());
        SupplyRun.Check c = r.check();
        assertThat(c.waterShort()).isZero();
        assertThat(c.requestsShort()).containsExactly("isle-a-1");
        r.depart(0);
        SupplyRun.Delivery d = r.deliver(r.durationMs()).orElseThrow();
        assertThat(d.passengersFed()).isEqualTo(3);
        assertThat(d.requestsMet()).isEqualTo(2);
        assertThat(d.complete()).isFalse();
    }

    @Test
    void holdAndCrewLimitsHoldTheLine() {
        SupplyRun r = run();
        assertThat(r.load(Cargo.TIMBER_BUNDLE, 31)).isEqualTo(SupplyRun.LoadResult.OVER_VOLUME);  // 124 slots
        assertThat(r.load(Cargo.WATER_CASK, 81)).isEqualTo(SupplyRun.LoadResult.CREW_TIRED);      // 810 kg > crew 800
        assertThat(r.load(Cargo.WATER_CASK, 80)).isEqualTo(SupplyRun.LoadResult.LOADED);
        assertThat(r.kg()).isEqualTo(800);
        SupplyRun heavy = new SupplyRun("ark-4", FROM, TO, PASSENGERS,
                List.of(new CrewMember("life:titan-ox-1", "animal", 500, 100)), REQUESTS);
        assertThat(heavy.load(Cargo.WATER_CASK, 100)).isEqualTo(SupplyRun.LoadResult.LOADED);
        assertThat(heavy.load(Cargo.WATER_CASK, 1)).isEqualTo(SupplyRun.LoadResult.OVER_WEIGHT); // 1010 kg
        SupplyRun dense = new SupplyRun("ark-5", FROM, TO, PASSENGERS,
                List.of(new CrewMember("life:titan-ox-1", "animal", 500, 100)), REQUESTS);
        assertThat(dense.load(Cargo.TIMBER_BUNDLE, 30)).isEqualTo(SupplyRun.LoadResult.LOADED);
        assertThat(dense.kg()).isEqualTo(600);
        assertThat(dense.volume()).isEqualTo(120);
        assertThat(dense.load(Cargo.SALVE_JAR, 1)).isEqualTo(SupplyRun.LoadResult.OVER_VOLUME);
        assertThatThrownBy(() -> new SupplyRun("ark-6", FROM, TO, PASSENGERS, List.of(), REQUESTS))
                .hasMessageContaining("crew");
        assertThatThrownBy(() -> new Passenger("Bad", "animal", 0, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void islandRequestsAreSeededAndStartWithSeedCaches() {
        assertThat(SupplyRequest.forIsland(77)).isEqualTo(SupplyRequest.forIsland(77));
        for (long s = 0; s < 40; s++) {
            List<SupplyRequest> q = SupplyRequest.forIsland(s);
            assertThat(q).hasSizeBetween(2, 4);
            assertThat(q.get(0).cargo()).isEqualTo(Cargo.SEED_CACHE);
            assertThat(q.get(1).cargo()).isEqualTo(Cargo.WATER_CASK);
            assertThat(q.stream().map(SupplyRequest::cargo).distinct().count()).isEqualTo(q.size());
        }
    }

    @Test
    void crewIsCreditedOnceThroughG12() {
        SupplyRun r = run();
        Load.full(r);
        r.depart(0);
        SupplyRunAdapter.Run done = SupplyRunAdapter.Run.of(r.deliver(r.durationMs()).orElseThrow());
        SupplyRunAdapter a = new SupplyRunAdapter(ActivityMode.AUTHORITATIVE);
        List<ActivityParticipant> crew = List.of(
                new ActivityParticipant("life:easel-mule-1", ActivityParticipant.Kind.LIFE, "animal", "carrying"),
                new ActivityParticipant("life:ark-goat-3", ActivityParticipant.Kind.LIFE, "animal", "carrying"));
        ActivityResultAdapter.Session s = new ActivityResultAdapter.Session("sess-ark-3", "res-ark-3", "ark-host",
                "verify:ark-3", crew, List.of("evt:voyage-ark-3"), 1_760_870_000_000L);
        ActivityResultReceipt receipt = a.toReceipt(s, done);
        assertThat(receipt.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(receipt.measures()).containsEntry("requests_met", 3L).containsEntry("passengers_fed", 3L);
        ProgressionLedger ledger = new ProgressionLedger();
        AwardPolicy policy = new AwardPolicy(SupplyRunAdapter.ACTIVITY_ID, 1, "mastery.logistics",
                Map.of("requests_met", 5L, "passengers_fed", 2L), 50);
        ledger.credit(receipt, policy);
        ledger.credit(a.toReceipt(s, done), policy);
        assertThat(ledger.total("life:ark-goat-3", "mastery.logistics")).isEqualTo(21);
        SupplyRunAdapter.Run quit = new SupplyRunAdapter.Run(0, 0, 0, 3, 0, 3, true);
        assertThat(policy.points(a.toReceipt(new ActivityResultAdapter.Session("sess-ark-4", "res-ark-4", "ark-host",
                "verify:ark-4", crew, List.of(), 1L), quit))).isZero();
    }

    /** Loads exactly what the run needs. */
    static final class Load {
        static void full(SupplyRun r) {
            assertThat(r.load(Cargo.SEED_CACHE, 4)).isEqualTo(SupplyRun.LoadResult.LOADED);
            assertThat(r.load(Cargo.TIMBER_BUNDLE, 2)).isEqualTo(SupplyRun.LoadResult.LOADED);
            assertThat(r.load(Cargo.WATER_CASK, 5 + r.waterNeeded())).isEqualTo(SupplyRun.LoadResult.LOADED);
            assertThat(r.load(Cargo.FODDER_BALE, r.fodderNeeded())).isEqualTo(SupplyRun.LoadResult.LOADED);
        }
    }
}
