// SPDX-License-Identifier: MIT
package com.daedalus.world.activity.adapters;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.fishing.CastSession;
import com.daedalus.world.fishing.Conditions;
import com.daedalus.world.fishing.FishSpecies;
import com.daedalus.world.fishing.FishTable;
import com.daedalus.world.fishing.Rarity;
import com.daedalus.world.labyrinth.EchoBellGate;
import com.daedalus.world.labyrinth.HornbackHerd;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ContestAdaptersTest {

    static final ActivityParticipant KITE_RAY =
            new ActivityParticipant("life:kite-ray-1", ActivityParticipant.Kind.LIFE, "animal", "scouting");
    static final ActivityParticipant DOG =
            new ActivityParticipant("life:kennel-dog-4", ActivityParticipant.Kind.LIFE, "animal", "herding");
    static final ActivityParticipant CRICKETS =
            new ActivityParticipant("colony:echo-crickets-1", ActivityParticipant.Kind.COLONY, "social_insect", "signaling");

    static ActivityResultAdapter.Session session(String id, ActivityParticipant p) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(p), List.of("evt:" + id), 1_760_866_000_000L);
    }

    static FishTable pond() {
        return new FishTable("prism", List.of(FishSpecies.of("Glimmer Dace", Rarity.COMMON, 6, 1.4, 4),
                FishSpecies.of("Cloud Carp", Rarity.UNCOMMON, 3, 1.1, 9),
                FishSpecies.of("Prism Eel", Rarity.RARE, 1, 0.8, 30)));
    }

    /** Casts that wait for the bite and strike: every one lands a fish. */
    static List<CastSession> goodCasts(int n) {
        List<CastSession> out = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            CastSession c = new CastSession(pond(), Conditions.DAY, 11, i);
            c.tick(c.waitSeconds() + 0.01);
            c.strike();
            out.add(c);
        }
        return out;
    }

    static List<Integer> perfectTaps(EchoBellGate g) {
        return g.rings().stream().map(EchoBellGate.Ring::echoMs).sorted().toList();
    }

    @Test
    void fishingOutingCountsRealCasts() {
        List<CastSession> casts = new ArrayList<>(goodCasts(6));
        CastSession early = new CastSession(pond(), Conditions.DAY, 11, 99);
        early.tick(0.1);
        early.strike();
        casts.add(early);
        FishingCastAdapter.Outing o = FishingCastAdapter.Outing.of(casts, 2, false);
        assertThat(o.casts()).isEqualTo(7);
        assertThat(o.caught()).isEqualTo(6);
        assertThat(o.missed()).isEqualTo(1);
        long rare = goodCasts(6).stream().filter(c -> c.fish().orElseThrow().rarity().isRare()).count();
        assertThat(o.rareCaught()).isEqualTo((int) rare);
        ActivityResultReceipt r = new FishingCastAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("fish-1", KITE_RAY), o);
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(r.measures()).containsEntry("caught", 6L).containsEntry("new_kinds", 2L).containsEntry("missed", 1L);
        ActivityResultReceipt empty = new FishingCastAdapter(ActivityMode.AUTHORITATIVE)
                .toReceipt(session("fish-2", KITE_RAY), FishingCastAdapter.Outing.of(List.of(early), 0, false));
        assertThat(empty.outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new FishingCastAdapter.Outing(1, 2, 0, 0, 0, false)).hasMessageContaining("add up");
    }

    @Test
    void hornbackPassageMapsTheRealSimulation() {
        HornbackHerd.Terrain open = new HornbackHerd.Terrain() {
            @Override public double coverAt(double x, double y) { return 0; }
            @Override public boolean burningAt(double x, double y) { return false; }
            @Override public boolean inside(double x, double y) { return x > -5000 && x < 8000 && y > -5000 && y < 8000; }
        };
        HornbackHerd.Report rep = HornbackHerd.run(9, 8, 0, 0, 3000, 0,
                List.of(new HornbackHerd.Trough(1500, 0, HornbackHerd.water(60))), open, HornbackHerd.Settings.DEFAULT, 240);
        HornbackPassageAdapter.Passage p = HornbackPassageAdapter.Passage.of(rep, false);
        ActivityResultReceipt r = new HornbackPassageAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("herd-1", DOG), p);
        assertThat(r.measures()).containsEntry("herd", 8L).containsEntry("arrived", (long) rep.arrived())
                .containsEntry("guided", rep.outcome() == HornbackHerd.Outcome.GUIDED ? 1L : 0L);
        assertThat(r.outcome()).isEqualTo(rep.outcome() == HornbackHerd.Outcome.GUIDED
                ? ActivityOutcome.COMPLETED : ActivityOutcome.FAILED);
        HornbackPassageAdapter.Passage stampede =
                new HornbackPassageAdapter.Passage(HornbackHerd.Outcome.STAMPEDE, 10, 4, 1, 2, 3, 0, false);
        assertThat(new HornbackPassageAdapter(ActivityMode.AUTHORITATIVE).toReceipt(session("herd-2", DOG), stampede)
                .outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new HornbackPassageAdapter.Passage(HornbackHerd.Outcome.GUIDED, 4, 5, 0, 0, 0, 0, false))
                .hasMessageContaining("add up");
    }

    @Test
    void echoBellListeningUsesTheGateVerdict() {
        EchoBellGate g = EchoBellGate.seeded(42L, 2, true);
        EchoBellGate.Verdict miss = g.judge(List.of(1));
        EchoBellGate.Verdict hit = g.retry().judge(perfectTaps(g));
        assertThat(hit.open()).isTrue();
        EchoBellAdapter a = new EchoBellAdapter(ActivityMode.AUTHORITATIVE);
        ActivityResultReceipt r = a.toReceipt(session("bell-1", CRICKETS), EchoBellAdapter.Listening.of(g, hit, 2, false));
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(r.measures()).containsEntry("bells", (long) g.rings().size()).containsEntry("gate_open", 1L)
                .containsEntry("attempts", 2L);
        assertThat(a.toReceipt(session("bell-2", CRICKETS), EchoBellAdapter.Listening.of(g, miss, 1, false)).outcome())
                .isEqualTo(ActivityOutcome.FAILED);
        assertThatThrownBy(() -> new EchoBellAdapter.Listening(4, 3, 1, true, false)).hasMessageContaining("every echo");
    }
}
