// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.activity.ReceiptJournal;
import com.daedalus.world.brew.apprentice.Apprenticeships;
import com.daedalus.world.brew.letters.Destination;
import com.daedalus.world.brew.lofts.GuestLofts;
import com.daedalus.world.brew.school.SongSchool;
import com.daedalus.world.forge.ArkDrydock;
import com.daedalus.world.forge.ArkDrydock.Ark;
import com.daedalus.world.forge.ArkDrydock.ArkClass;
import com.daedalus.world.forge.ArkDrydock.Life;
import com.daedalus.world.forge.ArkDrydock.Plate;
import com.daedalus.world.forge.ArkDrydock.Voyage;
import com.daedalus.world.forge.ScarDig;
import com.daedalus.world.forge.TemperForge.Quench;
import com.daedalus.world.forge.VoidCrossing;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Contest G168: receipts hub XIV over four landed games, driven by the real cores. */
class HubFourteenAdaptersTest {

    static final ActivityParticipant HOUND =
            new ActivityParticipant("life:loft-hound-1", ActivityParticipant.Kind.LIFE, "animal", "companionship");
    static final ActivityParticipant GOAT =
            new ActivityParticipant("life:scar-goat-2", ActivityParticipant.Kind.LIFE, "animal", "hauling");

    static ActivityResultAdapter.Session session(String id, ActivityParticipant p) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(p), List.of("evt:" + id), 1_760_882_000_000L);
    }

    @Test
    void guestLoftsSnugCompletesSprawlFailsUnsettledRefused() {
        GuestLoftsAdapter a = new GuestLoftsAdapter(ActivityMode.AUTHORITATIVE);
        for (long seed = 1; seed <= 10; seed++) {
            GuestLofts g = new GuestLofts(GuestLofts.fromFarIslands(Destination.island(), seed));
            assertThatThrownBy(() -> GuestLoftsAdapter.Stay.of(g, false)).hasMessageContaining("progress");
            assertThat(a.toReceipt(session("gl-a" + seed, HOUND), GuestLoftsAdapter.Stay.of(g, true)).outcome())
                    .isEqualTo(ActivityOutcome.ABANDONED);
            int n = 0;
            for (Map.Entry<String, Integer> e : g.greedyPlan().entrySet()) {
                g.assign("p" + n++, e.getKey(), e.getValue());
            }
            assertThat(g.settle("s")).isEqualTo(GuestLofts.Outcome.SNUG);
            var r = a.toReceipt(session("gl-" + seed, HOUND), GuestLoftsAdapter.Stay.of(g, false));
            assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
            assertThat(r.measures()).containsEntry("aired", (long) g.fewest()).containsEntry("fewest",
                    (long) g.fewest());
        }
        var sprawl = new GuestLoftsAdapter.Stay(5, 3, 8, false, false);
        assertThat(a.toReceipt(session("gl-x", HOUND), sprawl).outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new GuestLoftsAdapter.Stay(5, 3, 8, true, false)).hasMessageContaining("snug");
    }

    @Test
    void scarDigIngotsCompleteEmptyOrFaintFails() {
        ScarDigAdapter a = new ScarDigAdapter(ActivityMode.AUTHORITATIVE);
        ScarDig.Kit kit = new ScarDig.Kit(false, false, ScarDig.MAX_CANTEENS);
        int struck = 0;
        for (long seed = 1; seed <= 20; seed++) {
            ScarDig.Plan p = ScarDig.plan(seed);
            ScarDig.Result best = ScarDig.run(p, kit, ScarDig.prospector(p, kit));
            var r = a.toReceipt(session("sd-" + seed, GOAT), ScarDigAdapter.Dig.of(best, false));
            boolean ok = !best.fainted() && best.ingots() > 0;
            assertThat(r.outcome()).isEqualTo(ok ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
            assertThat(r.measures()).containsEntry("ingots", (long) best.ingots());
            if (ok) {
                struck++;
            }
            ScarDig.Result none = ScarDig.run(p, kit, List.of());
            assertThat(a.toReceipt(session("sd-n" + seed, GOAT), ScarDigAdapter.Dig.of(none, false)).outcome())
                    .isEqualTo(ActivityOutcome.FAILED);
        }
        assertThat(struck).isPositive();
        var fainted = new ScarDigAdapter.Dig(3, 6, 0, 0, true, false);
        assertThat(a.toReceipt(session("sd-f", GOAT), fainted).outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new ScarDigAdapter.Dig(-1, 0, 0, 0, false, false)).hasMessageContaining("haul");
    }

    static final Voyage KENNEL = new Voyage("Kennel Isle", 6);

    static Ark ark(int temper, int extraDl) {
        List<Plate> plates = new ArrayList<>();
        List<Integer> rivets = new ArrayList<>();
        for (int i = 0; i < ArkClass.SKIFF.plates(); i++) {
            plates.add(new Plate(temper, i == 3 ? Quench.SPRING : Quench.MAGMA, true));
            rivets.add(ArkDrydock.RIVETS_PER_SEAM);
        }
        Map<Life, Integer> m = new EnumMap<>(Life.class);
        m.put(Life.EMBERHEN, 2);
        m.put(Life.ASHGOAT, 2);
        m.put(Life.PET, 1);
        Ark dry = new Ark(ArkClass.SKIFF, plates, rivets, m, 0);
        return new Ark(ArkClass.SKIFF, plates, rivets, m, ArkDrydock.waterNeedDl(dry, KENNEL) + extraDl);
    }

    @Test
    void voidCrossingArrivalCompletesBreachFailsSailingRefused() {
        VoidCrossingAdapter a = new VoidCrossingAdapter(ActivityMode.AUTHORITATIVE);
        int arrived = 0;
        int failed = 0;
        for (long seed = 1; seed <= 30; seed++) {
            for (int temper : new int[] {95, 40}) {
                VoidCrossing.Crossing x = VoidCrossing.depart(ark(temper, 0), KENNEL, true, 6, seed);
                if (x.outcome() == VoidCrossing.Outcome.SAILING) {
                    assertThatThrownBy(() -> VoidCrossingAdapter.Passage.of(x, false)).hasMessageContaining("SAILING");
                }
                while (x.outcome() == VoidCrossing.Outcome.SAILING) {
                    x.sail(x.weakestPatchable());
                }
                var r = a.toReceipt(session("vc-" + seed + "-" + temper, GOAT), VoidCrossingAdapter.Passage.of(x, false));
                boolean ok = x.outcome() == VoidCrossing.Outcome.ARRIVED
                        || x.outcome() == VoidCrossing.Outcome.ARRIVED_WITH_LOSSES;
                assertThat(r.outcome()).isEqualTo(ok ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
                assertThat(r.measures()).containsEntry("lost", (long) x.lostHead());
                if (ok) {
                    arrived++;
                } else {
                    failed++;
                }
            }
        }
        assertThat(arrived).isPositive();
        assertThat(failed + arrived).isEqualTo(60);
        var breach = new VoidCrossingAdapter.Passage(false, 3, 20, 1, 0, false);
        assertThat(a.toReceipt(session("vc-b", GOAT), breach).outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new VoidCrossingAdapter.Passage(true, -1, 50, 0, 0, false))
                .hasMessageContaining("negative");
    }

    @Test
    void apprenticesStableCompletesUnstableFailsUnannouncedRefused() {
        ApprenticesAdapter a = new ApprenticesAdapter(ActivityMode.AUTHORITATIVE);
        int unstable = 0;
        for (long seed = 1; seed <= 20; seed++) {
            Apprenticeships good = Apprenticeships.forChildren(SongSchool.fromFarIslands(Destination.island(), seed), seed);
            assertThatThrownBy(() -> ApprenticesAdapter.Lantern.of(good, false)).hasMessageContaining("announced");
            int n = 0;
            for (Map.Entry<String, String> e : good.proposing(true).entrySet()) {
                good.pair("p" + n++, e.getKey(), e.getValue());
            }
            assertThat(good.announce("a")).isEqualTo(Apprenticeships.Outcome.STABLE);
            assertThat(a.toReceipt(session("ap-" + seed, HOUND), ApprenticesAdapter.Lantern.of(good, false))
                    .outcome()).isEqualTo(ActivityOutcome.COMPLETED);

            Apprenticeships bad = Apprenticeships.forChildren(SongSchool.fromFarIslands(Destination.island(), seed), seed);
            List<String> kids = new ArrayList<>(bad.childPrefs().keySet());
            List<String> masters = new ArrayList<>(Apprenticeships.MASTERS);
            java.util.Collections.reverse(masters);
            for (int i = 0; i < kids.size(); i++) {
                bad.pair("q" + i, kids.get(i), masters.get(i));
            }
            Apprenticeships.Outcome o = bad.announce("b");
            var r = a.toReceipt(session("ap-b" + seed, HOUND), ApprenticesAdapter.Lantern.of(bad, false));
            assertThat(r.outcome()).isEqualTo(o == Apprenticeships.Outcome.STABLE ? ActivityOutcome.COMPLETED
                    : ActivityOutcome.FAILED);
            if (o == Apprenticeships.Outcome.UNSTABLE) {
                unstable++;
                assertThat(r.measures().get("blocking")).isPositive();
            }
        }
        assertThat(unstable).isPositive();
        assertThatThrownBy(() -> new ApprenticesAdapter.Lantern(-1, 0, false)).hasMessageContaining("negative");
    }

    @Test
    void contestAllRoutesHubFourteenSettlesOnceAndReplays() {
        ActivityRouter r = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        assertThat(r.activities()).contains(GuestLoftsAdapter.ACTIVITY_ID, ScarDigAdapter.ACTIVITY_ID,
                VoidCrossingAdapter.ACTIVITY_ID, ApprenticesAdapter.ACTIVITY_ID);
        AwardPolicy policy = new AwardPolicy(ScarDigAdapter.ACTIVITY_ID, 1, "mastery.hauling",
                Map.of("ingots", 1L), 60);
        r.setPolicy(policy);
        ScarDigAdapter.Dig d = new ScarDigAdapter.Dig(2, 4, 0, 20, false, false);
        r.settle(ScarDigAdapter.ACTIVITY_ID, session("route-sd", GOAT), d);
        r.settle(ScarDigAdapter.ACTIVITY_ID, session("route-sd", GOAT), d);
        long once = r.total("life:scar-goat-2", "mastery.hauling");
        assertThat(once).isPositive();
        assertThat(ReceiptJournal.readAll(r.journal())).hasSize(1);
        ActivityRouter restarted = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        restarted.setPolicy(policy);
        assertThat(restarted.replay(r.journal())).isEqualTo(1);
        assertThat(restarted.total("life:scar-goat-2", "mastery.hauling")).isEqualTo(once);
        assertThatThrownBy(() -> r.settle(GuestLoftsAdapter.ACTIVITY_ID, session("route-x", GOAT), d))
                .hasMessageContaining("expects");
    }
}
