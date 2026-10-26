// SPDX-License-Identifier: MIT

package com.daedalus.world.odds;

import com.daedalus.world.tactics.TacticalOrders;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * The encounter spec the simulator runs: one player against a squad. Pure data; nothing here knows about Unreal, the
 * network or a clock. Build it by hand, or from a DTO 1 spec with {@link #fromOrders}.
 */
public record Encounter(Combatant player, List<Foe> foes, TargetPolicy policy, double maxSeconds) {

    public static final int MAX_FOES = TacticalOrders.MAX_ORDERS;
    public static final double MAX_SECONDS = 3600;

    /** One enemy and what its order makes it do. */
    public record Foe(Combatant stats, OrderProfile profile) {
        public Foe {
            Objects.requireNonNull(stats, "stats");
            Objects.requireNonNull(profile, "profile");
        }

        public static Foe fighting(Combatant stats) {
            return new Foe(stats, OrderProfile.fighting());
        }
    }

    public Encounter {
        Objects.requireNonNull(player, "player");
        Objects.requireNonNull(foes, "foes");
        Objects.requireNonNull(policy, "policy");
        if (foes.isEmpty() || foes.size() > MAX_FOES) {
            throw new IllegalArgumentException("an encounter needs 1.." + MAX_FOES + " foes");
        }
        if (!Double.isFinite(maxSeconds) || maxSeconds <= 0 || maxSeconds > MAX_SECONDS) {
            throw new IllegalArgumentException("maxSeconds must be in (0, " + MAX_SECONDS + "]");
        }
        foes = List.copyOf(foes);
    }

    /** Every foe fights from the start. */
    public static Encounter allOut(Combatant player, List<Combatant> foes, TargetPolicy policy, double maxSeconds) {
        List<Foe> list = new ArrayList<>(foes.size());
        for (Combatant c : foes) {
            list.add(Foe.fighting(c));
        }
        return new Encounter(player, list, policy, maxSeconds);
    }

    /**
     * Read a DTO 1 squad-orders spec (the Director's output): each order's unit is looked up in {@code stats} by id and
     * its verb picks the {@link OrderProfile}. A unit with no stats entry is an error, never a silent default.
     */
    public static Encounter fromOrders(TacticalOrders.Spec spec, Map<String, Combatant> stats, Combatant player,
                                       TargetPolicy policy, double maxSeconds) {
        return fromOrders(spec, stats, player, policy, maxSeconds, OrderProfile::of);
    }

    /** As {@link #fromOrders(TacticalOrders.Spec, Map, Combatant, TargetPolicy, double)} with tuned verb profiles. */
    public static Encounter fromOrders(TacticalOrders.Spec spec, Map<String, Combatant> stats, Combatant player,
                                       TargetPolicy policy, double maxSeconds,
                                       java.util.function.Function<TacticalOrders.Verb, OrderProfile> profiles) {
        Objects.requireNonNull(spec, "spec");
        Objects.requireNonNull(stats, "stats");
        Objects.requireNonNull(profiles, "profiles");
        List<Foe> foes = new ArrayList<>(spec.orders().size());
        for (TacticalOrders.Order o : spec.orders()) {
            Combatant c = stats.get(o.unit());
            if (c == null) {
                throw new IllegalArgumentException("no combat stats for unit " + o.unit());
            }
            foes.add(new Foe(c, Objects.requireNonNull(profiles.apply(o.verb()), "profile")));
        }
        return new Encounter(player, foes, policy, maxSeconds);
    }
}