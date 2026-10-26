// SPDX-License-Identifier: MIT
package com.daedalus.world.tactics;

import java.util.Objects;
import java.util.function.Function;

/** Stateful host adapter. Persistence and faction/objective authorization stay with the trusted host. */
public final class AdaptiveTacticsBrain implements TacticsHost.ContextBrain {
    public record Key(String session, String squad, String faction) { }

    public record Context(String faction, TacticalOrders.Vec objective, boolean threatened,
                          AdaptiveDirector.WeaponStyle weapon) {
        public Context {
            AdaptiveDirector.id(faction);
            Objects.requireNonNull(objective);
            Objects.requireNonNull(weapon);
        }
    }

    /** Single-writer durable storage: null means absent; save must commit atomically or throw. */
    public interface Checkpoints {
        byte[] load(Key key);
        void save(Key key, byte[] checkpoint);
    }

    private final Checkpoints checkpoints;
    private final Function<TacticalOrders.Roster, Context> context;

    public AdaptiveTacticsBrain(Checkpoints checkpoints, Function<TacticalOrders.Roster, Context> context) {
        this.checkpoints = Objects.requireNonNull(checkpoints);
        this.context = Objects.requireNonNull(context);
    }

    /** Serializes this adapter's load/decide/commit sequence; do not share its store with another writer. */
    @Override
    public synchronized TacticalOrders.Spec decide(TacticalOrders.Roster roster, TacticalOrders.Vec player) {
        Context c = Objects.requireNonNull(context.apply(roster));
        Key key = new Key(roster.session(), roster.squad(), c.faction());
        byte[] saved = checkpoints.load(key);
        var before = saved == null ? AdaptiveDirector.Memory.initial(c.faction(), roster.session())
                : TacticalMemory.decode(saved);
        if (!before.faction().equals(c.faction())) throw new IllegalArgumentException("Checkpoint faction mismatch");
        var frame = AdaptiveDirector.fromRoster(roster, player, c.objective(), c.threatened(), c.weapon());
        var decision = AdaptiveDirector.decide(before, frame);
        // Validate output before durable state changes; a failed commit must never return an order.
        String wire = TacticalOrders.write(decision.orders());
        if (!TacticalOrders.parse(wire).ok()) throw new IllegalStateException("Invalid adaptive output");
        if (!decision.memory().equals(before)) checkpoints.save(key, TacticalMemory.encode(decision.memory()));
        return decision.orders();
    }
}
