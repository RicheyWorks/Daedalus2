// SPDX-License-Identifier: MIT
package com.daedalus.world.simulation;

import com.daedalus.world.Npc;
import com.daedalus.world.WorldId;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;
import java.util.UUID;

/** Pure settlement decisions. Time and authenticated commands are inputs; no clocks or I/O. */
public final class LivingWorld {
    public static final int VERSION = 1;
    public static final int MAX_CATCH_UP = 64;
    public static final int MAX_RECEIPTS = 1024;
    public static final int MAX_EVENTS = 64;
    public static final int RESOURCE_CAPACITY = 12;

    private LivingWorld() { }

    public enum Kind { ADVANCE, SUPPLY, ACTIVITY }
    public enum EventKind { RESOURCE_REGENERATED, RESOURCE_CONSUMED, NPC_STATE_CHANGED,
        WORLD_EVENT_STARTED, WORLD_EVENT_ENDED, QUEST_COMPLETED, WATER_DELIVERED }
    public enum Task { REST, WORK, REQUEST_WATER }

    /** ADVANCE/ACTIVITY are trusted host inputs, never accepted from player action JSON. */
    public record Input(Kind kind, long value, String requestId, String actor) {
        public Input {
            Objects.requireNonNull(kind, "kind");
            Objects.requireNonNull(requestId, "requestId");
            Objects.requireNonNull(actor, "actor");
            if (kind == Kind.SUPPLY) {
                if (!UUID.fromString(requestId).toString().equals(requestId) || !identity(actor)
                        || value < 1 || value > 3) {
                    throw new IllegalArgumentException("Supply needs a canonical UUID, actor and 1..3 water");
                }
            } else if (!requestId.isEmpty() || !actor.isEmpty() || value < 0
                    || (kind == Kind.ACTIVITY && value > 1)) {
                throw new IllegalArgumentException("Invalid host input");
            }
        }
        public static Input advance(long tick) { return new Input(Kind.ADVANCE, tick, "", ""); }
        public static Input supply(String id, String actor, int water) {
            return new Input(Kind.SUPPLY, water, id, actor);
        }
        public static Input activity(boolean active) { return new Input(Kind.ACTIVITY, active ? 1 : 0, "", ""); }
    }

    public record Receipt(String actor, int water, long tick, long revision, boolean questCompleted) {
        public Receipt {
            if (!identity(actor) || water < 1 || water > 3 || tick < 0 || revision < 1) {
                throw new IllegalArgumentException("Invalid receipt");
            }
        }
    }

    public record Event(long sequence, long tick, EventKind kind, String detail) {
        public Event {
            if (sequence < 1 || tick < 0 || kind == null || detail == null || detail.length() > 256) {
                throw new IllegalArgumentException("Invalid event");
            }
        }
    }

    public record State(int version, WorldId worldId, long seed, long tick, long revision,
                        int water, int keeperWater, boolean questCompleted, String rememberedActor,
                        boolean active, long eventSequence, Map<String, Receipt> receipts, List<Event> events) {
        public State {
            Objects.requireNonNull(worldId, "worldId");
            if (version != VERSION || !identity(worldId.value()) || tick < 0 || revision < 0
                    || water < 0 || water > RESOURCE_CAPACITY || keeperWater < 0 || keeperWater > 6
                    || rememberedActor == null || (!rememberedActor.isEmpty() && !identity(rememberedActor))
                    || questCompleted != !rememberedActor.isEmpty() || eventSequence < 0
                    || receipts == null || receipts.size() > MAX_RECEIPTS || events == null
                    || events.size() > MAX_EVENTS) {
                throw new IllegalArgumentException("Invalid simulation snapshot");
            }
            receipts = Collections.unmodifiableMap(new TreeMap<>(receipts));
            events = List.copyOf(events);
            for (var entry : receipts.entrySet()) {
                if (!UUID.fromString(entry.getKey()).toString().equals(entry.getKey())
                        || entry.getValue() == null || entry.getValue().revision() > revision
                        || entry.getValue().tick() > tick) {
                    throw new IllegalArgumentException("Invalid receipt history");
                }
            }
            long previous = events.isEmpty() ? eventSequence : events.getFirst().sequence() - 1;
            long previousTick = 0;
            for (Event event : events) {
                if (event.sequence() != previous + 1 || event.tick() < previousTick || event.tick() > tick) {
                    throw new IllegalArgumentException("Unordered event history");
                }
                previous = event.sequence();
                previousTick = event.tick();
            }
            if (previous != eventSequence || (events.isEmpty() && eventSequence != 0)) {
                throw new IllegalArgumentException("Event cursor mismatch");
            }
        }
        public String npcId() { return Npc.ZERO_ID; }
        public long drySpellStart() { return 24 + Math.floorMod(seed, 12); }
        public boolean drySpell() { return tick >= drySpellStart() && tick < drySpellStart() + 12; }
        public Task task() { return taskAt(tick, keeperWater); }
        public String reason() {
            return switch (task()) {
                case REST -> "Night schedule";
                case WORK -> "Water need satisfied";
                case REQUEST_WATER -> "Keeper water exhausted";
            };
        }
    }

    public record Transition(State state, Receipt receipt, boolean duplicate, List<Event> emitted) {
        public Transition { emitted = List.copyOf(emitted); }
    }

    public static State initial(WorldId worldId, long seed) {
        return new State(VERSION, worldId, seed, 0, 0, 3, 0, false, "", true, 0, Map.of(), List.of());
    }

    public static Transition apply(State before, Input input) {
        Objects.requireNonNull(before, "state");
        Objects.requireNonNull(input, "input");
        if (input.kind() == Kind.SUPPLY && before.receipts().containsKey(input.requestId())) {
            Receipt receipt = before.receipts().get(input.requestId());
            if (!receipt.actor().equals(input.actor()) || receipt.water() != input.value()) {
                throw new IllegalArgumentException("Request id already belongs to a different action");
            }
            return new Transition(before, receipt, true, List.of());
        }
        if (input.kind() == Kind.ADVANCE && input.value() <= before.tick()
                || input.kind() == Kind.ACTIVITY && (input.value() == 1) == before.active()) {
            return new Transition(before, null, false, List.of());
        }
        long revision = Math.addExact(before.revision(), 1);
        long tick = before.tick();
        int water = before.water();
        int keeper = before.keeperWater();
        boolean complete = before.questCompleted();
        String memory = before.rememberedActor();
        boolean active = before.active();
        Map<String, Receipt> receipts = new TreeMap<>(before.receipts());
        List<Event> emitted = new ArrayList<>();
        Receipt receipt = null;
        if (input.kind() == Kind.ADVANCE) {
            long steps = Math.min(MAX_CATCH_UP, input.value() - tick);
            for (long i = 0; i < steps; i++) {
                Task oldTask = taskAt(tick, keeper);
                tick++;
                long start = before.drySpellStart();
                if (tick == start) emit(before, emitted, tick, EventKind.WORLD_EVENT_STARTED, "DRY_SPELL");
                if (tick == start + 12) emit(before, emitted, tick, EventKind.WORLD_EVENT_ENDED, "DRY_SPELL");
                if (tick % 6 == 0 && !(tick >= start && tick < start + 12) && water < RESOURCE_CAPACITY) {
                    water++;
                    emit(before, emitted, tick, EventKind.RESOURCE_REGENERATED, "cistern:+1");
                }
                if (tick % 12 == 0 && keeper > 0) {
                    keeper--;
                    emit(before, emitted, tick, EventKind.RESOURCE_CONSUMED, "keeper:-1");
                }
                if (oldTask != taskAt(tick, keeper)) {
                    emit(before, emitted, tick, EventKind.NPC_STATE_CHANGED, taskAt(tick, keeper).name());
                }
            }
        } else if (input.kind() == Kind.SUPPLY) {
            int amount = Math.toIntExact(input.value());
            if (receipts.size() == MAX_RECEIPTS) throw new IllegalStateException("Receipt capacity reached");
            if (water < amount || keeper + amount > 6) throw new IllegalArgumentException("Insufficient water or keeper full");
            Task oldTask = taskAt(tick, keeper);
            water -= amount;
            keeper += amount;
            emit(before, emitted, tick, EventKind.WATER_DELIVERED, input.actor() + ":" + amount);
            if (!complete && keeper >= 3) {
                complete = true;
                memory = input.actor();
                emit(before, emitted, tick, EventKind.QUEST_COMPLETED, "keeper-shortage:" + memory);
            }
            if (oldTask != taskAt(tick, keeper)) emit(before, emitted, tick, EventKind.NPC_STATE_CHANGED, taskAt(tick, keeper).name());
            receipt = new Receipt(input.actor(), amount, tick, revision, complete);
            receipts.put(input.requestId(), receipt);
        } else {
            active = input.value() == 1;
        }
        List<Event> history = new ArrayList<>(before.events());
        history.addAll(emitted);
        if (history.size() > MAX_EVENTS) history = history.subList(history.size() - MAX_EVENTS, history.size());
        State after = new State(VERSION, before.worldId(), before.seed(), tick, revision, water, keeper,
                complete, memory, active, Math.addExact(before.eventSequence(), emitted.size()), receipts, history);
        return new Transition(after, receipt, false, emitted);
    }

    private static void emit(State before, List<Event> events, long tick, EventKind kind, String detail) {
        events.add(new Event(Math.addExact(before.eventSequence(), events.size() + 1L), tick, kind, detail));
    }

    private static Task taskAt(long tick, int water) {
        long hour = tick % 24;
        return hour < 6 || hour >= 18 ? Task.REST : water == 0 ? Task.REQUEST_WATER : Task.WORK;
    }

    private static boolean identity(String value) {
        return value != null && value.matches("[A-Za-z0-9_.:@-]{1,128}");
    }
}
