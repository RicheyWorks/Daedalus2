// SPDX-License-Identifier: MIT
package com.daedalus.world.simulation;

import com.daedalus.world.WorldId;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import static org.junit.jupiter.api.Assertions.*;

class LivingWorldTest {
    private static final String ACTION = "00000000-0000-0000-0000-000000000001";
    private LivingWorld.State initial() { return LivingWorld.initial(WorldId.ZERO, 0); }

    @Test void completeQuestConsumesFiniteWaterAndNpcRemembersWhoHelped() {
        var state = LivingWorld.apply(initial(), LivingWorld.Input.advance(6)).state();
        assertEquals(LivingWorld.Task.REQUEST_WATER, state.task());
        assertEquals("Keeper water exhausted", state.reason());
        var change = LivingWorld.apply(state, LivingWorld.Input.supply(ACTION, "alice", 3));
        assertEquals(1, change.state().water());
        assertEquals(3, change.state().keeperWater());
        assertTrue(change.state().questCompleted());
        assertEquals("alice", change.state().rememberedActor());
        assertEquals(LivingWorld.Task.WORK, change.state().task());
        assertEquals("Water need satisfied", change.state().reason());
        assertEquals("npc-zero", change.state().npcId());
        assertTrue(change.emitted().stream().anyMatch(e -> e.kind() == LivingWorld.EventKind.QUEST_COMPLETED));
    }
    @Test void duplicateHasIdenticalReceiptNoSecondTransferAndConflictCannotMutate() {
        var input = LivingWorld.Input.supply(ACTION, "alice", 3);
        var first = LivingWorld.apply(initial(), input);
        var later = LivingWorld.apply(first.state(), LivingWorld.Input.advance(64)).state();
        var again = LivingWorld.apply(later, input);
        assertSame(later, again.state());
        assertEquals(first.receipt(), again.receipt());
        assertTrue(again.duplicate());
        assertTrue(again.emitted().isEmpty());
        assertThrows(IllegalArgumentException.class, () -> LivingWorld.apply(later, LivingWorld.Input.supply(ACTION, "bob", 3)));
        assertThrows(IllegalArgumentException.class, () -> LivingWorld.apply(later, LivingWorld.Input.supply(ACTION, "alice", 2)));
    }
    @Test void invalidInputsAndInsufficientStockAreAtomic() {
        String before = SimulationCodec.hash(initial());
        assertThrows(IllegalArgumentException.class, () -> LivingWorld.Input.supply(ACTION, "alice", 0));
        assertThrows(IllegalArgumentException.class, () -> LivingWorld.Input.supply(ACTION, "alice", 4));
        assertThrows(IllegalArgumentException.class, () -> LivingWorld.Input.supply("short", "alice", 1));
        assertThrows(IllegalArgumentException.class, () -> LivingWorld.Input.supply(ACTION, "../bad", 1));
        assertThrows(IllegalArgumentException.class, () -> LivingWorld.Input.advance(-1));
        assertThrows(IllegalArgumentException.class, () -> new LivingWorld.Input(LivingWorld.Kind.ACTIVITY, 2, "", ""));
        assertThrows(IllegalArgumentException.class, () -> new LivingWorld.Input(LivingWorld.Kind.ADVANCE, 1, ACTION, ""));
        var empty = LivingWorld.apply(initial(), LivingWorld.Input.supply(ACTION, "alice", 3)).state();
        assertThrows(IllegalArgumentException.class, () -> LivingWorld.apply(empty,
                LivingWorld.Input.supply("00000000-0000-0000-0000-000000000002", "alice", 1)));
        assertEquals(before, SimulationCodec.hash(initial()));
    }
    @Test void drySpellHasPredictableStartEndAndRegenerationStopsDuringIt() {
        var state = LivingWorld.apply(initial(), LivingWorld.Input.advance(23)).state();
        int water = state.water();
        assertFalse(state.drySpell());
        state = LivingWorld.apply(state, LivingWorld.Input.advance(24)).state();
        assertTrue(state.drySpell());
        assertEquals(water, state.water());
        state = LivingWorld.apply(state, LivingWorld.Input.advance(35)).state();
        assertEquals(water, state.water());
        state = LivingWorld.apply(state, LivingWorld.Input.advance(36)).state();
        assertFalse(state.drySpell());
        assertEquals(water + 1, state.water());
        assertEquals(1, state.events().stream().filter(e -> e.kind() == LivingWorld.EventKind.WORLD_EVENT_STARTED).count());
        assertEquals(1, state.events().stream().filter(e -> e.kind() == LivingWorld.EventKind.WORLD_EVENT_ENDED).count());
    }
    @Test void clockBoundsBackwardsTimeAndInactiveRules() {
        var first = initial();
        assertEquals(LivingWorld.Task.REST, first.task());
        assertEquals("Night schedule", first.reason());
        assertSame(first, LivingWorld.apply(first, LivingWorld.Input.advance(0)).state());
        assertSame(first, LivingWorld.apply(first, LivingWorld.Input.activity(true)).state());
        var active = LivingWorld.apply(first, LivingWorld.Input.advance(Long.MAX_VALUE)).state();
        var inactive = LivingWorld.apply(LivingWorld.apply(first, LivingWorld.Input.activity(false)).state(),
                LivingWorld.Input.advance(Long.MAX_VALUE)).state();
        assertEquals(64, active.tick());
        assertEquals(active.water(), inactive.water());
        assertEquals(active.task(), inactive.task());
        assertEquals(active.events(), inactive.events());
        assertFalse(inactive.active());
    }
    @Test void deterministicReplayRoundTripAndCompactionPreserveEveryDecision() throws IOException {
        var one = SimulationTimeline.start(initial());
        var two = SimulationTimeline.start(initial());
        for (int i = 0; i < 200; i++) {
            var input = LivingWorld.Input.advance(i * 12L);
            one = one.append(input).timeline();
            two = two.append(input).timeline();
            if (i == 5) {
                var action = LivingWorld.Input.supply(ACTION, "alice", 3);
                one = one.append(action).timeline(); two = two.append(action).timeline();
            }
            byte[] bytes = SimulationCodec.encode(new SimulationCodec.Stored(1000, 100, "alice", one));
            one = SimulationCodec.decode(bytes).timeline();
            assertEquals(two.state(), one.state());
            assertEquals(SimulationCodec.hash(two.state()), SimulationCodec.hash(one.state()));
        }
        assertTrue(one.checkpoint().revision() > 0);
        assertTrue(one.entries().size() <= SimulationTimeline.MAX_TAIL);
        assertEquals(LivingWorld.MAX_EVENTS, one.state().events().size());
        assertTrue(one.append(LivingWorld.Input.supply(ACTION, "alice", 3)).transition().duplicate());
    }
    @Test void replayRejectsDivergenceAndDuplicateLogEntries() {
        var start = initial();
        var advance = LivingWorld.Input.advance(10);
        var change = LivingWorld.apply(start, advance).state();
        var entry = new SimulationTimeline.Entry(advance, SimulationCodec.hash(change));
        assertEquals(change, SimulationTimeline.recover(start, List.of(entry)).state());
        assertThrows(IllegalArgumentException.class, () -> SimulationTimeline.recover(start,
                List.of(new SimulationTimeline.Entry(advance, "0".repeat(64)))));
        assertThrows(IllegalArgumentException.class, () -> SimulationTimeline.recover(start, List.of(entry, entry)));
        assertThrows(IllegalArgumentException.class, () -> SimulationTimeline.recover(start, java.util.Collections.nCopies(65, entry)));
        assertThrows(IllegalArgumentException.class, () -> new SimulationTimeline.Entry(advance, "bad"));
    }
    @Test void codecRejectsCorruptionTruncationOversizeAndUnknownVersion() {
        byte[] bytes = SimulationCodec.encode(new SimulationCodec.Stored(1000, 100, "alice", SimulationTimeline.start(initial())));
        assertThrows(IOException.class, () -> SimulationCodec.decode(new byte[0]));
        assertThrows(IOException.class, () -> SimulationCodec.decode(new byte[SimulationCodec.MAX_BYTES + 1]));
        bytes[6] ^= 1;
        assertThrows(IOException.class, () -> SimulationCodec.decode(bytes));
        assertThrows(IllegalArgumentException.class, () -> new SimulationCodec.Stored(-1, 1, "alice", SimulationTimeline.start(initial())));
        assertThrows(IllegalArgumentException.class, () -> new SimulationCodec.Stored(0, 0, "alice", SimulationTimeline.start(initial())));
    }
    @Test void stateOwnsImmutableCollectionsAndRejectsBadCursor() {
        var events = new ArrayList<LivingWorld.Event>();
        var state = new LivingWorld.State(1, WorldId.ZERO, 0, 0, 0, 3, 0, false, "", true, 0, Map.of(), events);
        events.add(new LivingWorld.Event(1, 0, LivingWorld.EventKind.NPC_STATE_CHANGED, "test"));
        assertTrue(state.events().isEmpty());
        assertThrows(UnsupportedOperationException.class, () -> state.receipts().put(ACTION, null));
        assertThrows(IllegalArgumentException.class, () -> new LivingWorld.State(2, WorldId.ZERO, 0, 0, 0,
                3, 0, false, "", true, 0, Map.of(), List.of()));
        assertThrows(IllegalArgumentException.class, () -> new LivingWorld.State(1, WorldId.ZERO, 0, 0, 0,
                3, 0, false, "", true, 5, Map.of(), List.of()));
        assertThrows(IllegalArgumentException.class, () -> new LivingWorld.Event(0, 0, LivingWorld.EventKind.NPC_STATE_CHANGED, "x"));
        assertThrows(IllegalArgumentException.class, () -> new LivingWorld.Receipt("alice", 0, 0, 1, false));
    }
    @Test void checksummedButUnsupportedOrMalformedPayloadsAreRejected() throws Exception {
        byte[] valid = SimulationCodec.encode(new SimulationCodec.Stored(1000, 100, "alice", SimulationTimeline.start(initial())));
        byte[] body = java.util.Arrays.copyOf(valid, valid.length - 32);
        byte[] version = body.clone();
        java.nio.ByteBuffer.wrap(version).putInt(4, 2);
        assertThrows(IOException.class, () -> SimulationCodec.decode(withChecksum(version)));
        byte[] rate = body.clone();
        java.nio.ByteBuffer.wrap(rate).putLong(16, 0);
        assertThrows(IOException.class, () -> SimulationCodec.decode(withChecksum(rate)));
        byte[] count = body.clone();
        java.nio.ByteBuffer.wrap(count).putInt(count.length - 4, 65);
        assertThrows(IOException.class, () -> SimulationCodec.decode(withChecksum(count)));
        assertThrows(IOException.class, () -> SimulationCodec.decode(withChecksum(java.util.Arrays.copyOf(body, body.length + 1))));
        assertThrows(IOException.class, () -> SimulationCodec.decode(withChecksum(java.util.Arrays.copyOf(body, body.length - 1))));
    }
    private static byte[] withChecksum(byte[] body) throws Exception {
        byte[] bytes = java.util.Arrays.copyOf(body, body.length + 32);
        byte[] checksum = java.security.MessageDigest.getInstance("SHA-256").digest(body);
        System.arraycopy(checksum, 0, bytes, body.length, checksum.length);
        return bytes;
    }
    @Test void receiptBoundRefusesNewActionButStillHonorsOldReceipt() {
        var receipts = new java.util.TreeMap<String, LivingWorld.Receipt>();
        for (int i = 0; i < LivingWorld.MAX_RECEIPTS; i++) {
            receipts.put(new UUID(0, i).toString(), new LivingWorld.Receipt("alice", 1, 0, 1, false));
        }
        var full = new LivingWorld.State(1, WorldId.ZERO, 0, 0, 1, 3, 0, false, "", true, 0, receipts, List.of());
        assertThrows(IllegalStateException.class, () -> LivingWorld.apply(full,
                LivingWorld.Input.supply(new UUID(1, 1).toString(), "alice", 1)));
        assertTrue(LivingWorld.apply(full, LivingWorld.Input.supply(ACTION, "alice", 1)).duplicate());
    }
}
