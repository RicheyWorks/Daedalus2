// SPDX-License-Identifier: MIT
package com.daedalus.world.simulation;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/** Bounded checkpoint plus ordered inputs. Each retained transition carries its expected state hash. */
public final class SimulationTimeline {
    public static final int MAX_TAIL = 64;
    public record Entry(LivingWorld.Input input, String stateHash) {
        public Entry {
            Objects.requireNonNull(input, "input");
            if (stateHash == null || !stateHash.matches("[0-9a-f]{64}")) {
                throw new IllegalArgumentException("Invalid state hash");
            }
        }
    }
    public record Commit(SimulationTimeline timeline, LivingWorld.Transition transition) { }
    private final LivingWorld.State checkpoint;
    private final LivingWorld.State state;
    private final List<Entry> entries;

    private SimulationTimeline(LivingWorld.State checkpoint, LivingWorld.State state, List<Entry> entries) {
        this.checkpoint = Objects.requireNonNull(checkpoint);
        this.state = Objects.requireNonNull(state);
        this.entries = List.copyOf(entries);
    }
    public static SimulationTimeline start(LivingWorld.State state) {
        return new SimulationTimeline(state, state, List.of());
    }
    public static SimulationTimeline recover(LivingWorld.State checkpoint, List<Entry> entries) {
        if (entries.size() > MAX_TAIL) throw new IllegalArgumentException("Replay tail too large");
        LivingWorld.State state = checkpoint;
        for (Entry entry : entries) {
            LivingWorld.State next = LivingWorld.apply(state, entry.input()).state();
            if (next.revision() != state.revision() + 1 || !SimulationCodec.hash(next).equals(entry.stateHash())) {
                throw new IllegalArgumentException("Simulation replay diverged at revision " + next.revision());
            }
            state = next;
        }
        return new SimulationTimeline(checkpoint, state, entries);
    }
    public Commit append(LivingWorld.Input input) {
        LivingWorld.Transition transition = LivingWorld.apply(state, input);
        if (transition.state() == state) return new Commit(this, transition);
        LivingWorld.State base = entries.size() == MAX_TAIL ? state : checkpoint;
        List<Entry> tail = entries.size() == MAX_TAIL ? new ArrayList<>() : new ArrayList<>(entries);
        tail.add(new Entry(input, SimulationCodec.hash(transition.state())));
        return new Commit(new SimulationTimeline(base, transition.state(), tail), transition);
    }
    public LivingWorld.State checkpoint() { return checkpoint; }
    public LivingWorld.State state() { return state; }
    public List<Entry> entries() { return entries; }
}
