// SPDX-License-Identifier: MIT
package com.daedalus.world.tactics;

import org.junit.jupiter.api.Test;
import java.util.HashMap;
import java.util.Map;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class AdaptiveTacticsBrainTest {
    private static final TacticalOrders.Vec PLAYER = new TacticalOrders.Vec(1000, 0, 0);
    private static final class Store implements AdaptiveTacticsBrain.Checkpoints {
        final Map<AdaptiveTacticsBrain.Key, byte[]> data = new HashMap<>();
        boolean fail;
        int writes;
        public byte[] load(AdaptiveTacticsBrain.Key key) { return data.get(key); }
        public void save(AdaptiveTacticsBrain.Key key, byte[] bytes) {
            if (fail) throw new IllegalStateException("disk unavailable");
            data.put(key, bytes.clone());
            writes++;
        }
    }
    private static AdaptiveTacticsBrain brain(Store store) {
        return new AdaptiveTacticsBrain(store, r -> new AdaptiveTacticsBrain.Context("raiders",
                new TacticalOrders.Vec(0, 0, 0), true, AdaptiveDirector.WeaponStyle.UNKNOWN));
    }
    private static TacticalOrders.Roster roster(String session, String squad, long tick) {
        return TacticalOrders.parseRoster("DTR 1\nsession " + session + " squad " + squad + " tick " + tick + "\n"
                + "unit guard SLIME 100 100 0 0 0 1\nunit scout SLIME 100 100 200 0 0 1\n"
                + "unit wounded SLIME 20 100 300 0 0 1\nunit fallen SLIME 0 100 400 0 0 0\n");
    }

    @Test void commitsBeforeReplyAndReplaysAfterAdapterRestart() {
        Store store = new Store();
        var first = brain(store).decide(roster("s", "q", 1), PLAYER);
        assertThat(first.orders()).extracting(TacticalOrders.Order::verb).containsExactly(
                TacticalOrders.Verb.DEFEND, TacticalOrders.Verb.FLANK, TacticalOrders.Verb.RETREAT);
        assertThat(store.writes).isEqualTo(1);
        assertThat(brain(store).decide(roster("s", "q", 1), PLAYER)).isEqualTo(first);
        assertThat(store.writes).isEqualTo(1);
        var saved = TacticalMemory.decode(store.data.values().iterator().next());
        assertThat(saved.casualtyPressure()).isEqualTo(1);
    }

    @Test void sessionsAndSquadsHaveIndependentReceipts() {
        Store store = new Store();
        var brain = brain(store);
        brain.decide(roster("s", "a", 9), PLAYER);
        brain.decide(roster("s", "b", 1), PLAYER);
        brain.decide(roster("new", "a", 1), PLAYER);
        assertThat(store.data).hasSize(3);
        assertThatThrownBy(() -> brain.decide(roster("s", "a", 8), PLAYER)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test void failedCommitReturnsNoOrdersAndRetryCanRecover() {
        Store store = new Store();
        store.fail = true;
        var brain = brain(store);
        assertThatThrownBy(() -> brain.decide(roster("s", "a", 1), PLAYER)).isInstanceOf(IllegalStateException.class);
        assertThat(store.data).isEmpty();
        store.fail = false;
        assertThat(brain.decide(roster("s", "a", 1), PLAYER).orders()).hasSize(3);
    }

    @Test void mismatchedAndCorruptedCheckpointsFailClosed() {
        Store store = new Store();
        var key = new AdaptiveTacticsBrain.Key("s", "a", "raiders");
        store.data.put(key, TacticalMemory.encode(AdaptiveDirector.Memory.initial("other", "s")));
        assertThatThrownBy(() -> brain(store).decide(roster("s", "a", 1), PLAYER)).isInstanceOf(IllegalArgumentException.class);
        store.data.put(key, new byte[] {1, 2});
        assertThatThrownBy(() -> brain(store).decide(roster("s", "a", 1), PLAYER)).isInstanceOf(IllegalArgumentException.class);
        assertThat(store.writes).isZero();
    }

    @Test void hostUsesAdaptiveBrainAndCachesRetriesWithoutExtraWrites() {
        Store store = new Store();
        var host = TacticsHost.withContext(brain(store));
        String r = "DTR 1\nsession s squad q tick 1\nunit a SLIME 100 100 0 0 0 1\n";
        String events = "DTE 1\ntick 1\nevent PLAYER player 1000 0 0 100\n";
        var first = host.decide(r, events);
        assertThat(first.result()).isEqualTo(TacticsHost.Result.APPLY);
        assertThat(host.decide(r, events).spec()).isEqualTo(first.spec());
        assertThat(store.writes).isEqualTo(1);
    }
}
