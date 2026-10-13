// SPDX-License-Identifier: MIT

package com.daedalus.world.tactics;

import com.daedalus.world.tactics.TacticalOrders.Event;
import com.daedalus.world.tactics.TacticalOrders.EventKind;
import com.daedalus.world.tactics.TacticalOrders.Events;
import com.daedalus.world.tactics.TacticalOrders.Roster;
import com.daedalus.world.tactics.TacticalOrders.Spec;
import com.daedalus.world.tactics.TacticalOrders.Vec;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * The Java end of the Unreal tactics adapter (ADR-060 "transport"): Unreal posts a squad's DTR 1 roster and its
 * DTE 1 events about once a second, and gets one DTO 1 spec back to hand to {@code UDaedalusTactics::ApplyOrders}.
 * <ul>
 *   <li><b>Fencing</b> per (session, squad), as the native side does: a newer tick is decided; the same tick again
 *       returns the spec already decided for it (a retried request is harmless); an older tick is refused as stale.
 *       A new session (Unreal restarted Play) starts fresh.</li>
 *   <li><b>The player</b> is where the latest PLAYER event put them. With none yet for the session there is nothing
 *       to fight, so every unit HOLDs where it is (the brain is not asked).</li>
 *   <li><b>The brain</b> is pluggable: the baseline {@link SquadDirector} by default; Astra's adaptive director
 *       (PR32) plugs in through {@link Brain} without the transport changing.</li>
 *   <li><b>Bounded:</b> at most {@link #MAX_SQUADS} (session, squad) entries, oldest dropped first; the parsers
 *       already cap a roster at 256 units and a batch at 512 events.</li>
 * </ul>
 * Thread-safe: one lock covers map work and the decision. A custom brain may perform durable storage;
 * its latency serializes requests to this host and must be measured off Unreal's game thread.
 */
public final class TacticsHost {

    public static final int MAX_SQUADS = 4096;

    /** Decides one squad's orders. The baseline is {@code SquadDirector::decide}. */
    @FunctionalInterface
    public interface Brain {
        Spec decide(String squad, long tick, List<SquadDirector.Unit> units, Vec player);
    }

    /** Context-aware strategy retains the authoritative session and complete roster. */
    @FunctionalInterface
    public interface ContextBrain {
        Spec decide(Roster roster, Vec player);
    }

    /** What happened to a request: APPLY (new spec), REPEAT (same tick, same spec), STALE (older tick, no spec). */
    public enum Result { APPLY, REPEAT, STALE }

    public record Decision(Result result, String spec, String why) {
    }

    private record Key(String session, String squad) {
    }

    private static final class Squad {
        long tick;
        String spec;
    }

    private record PlayerObservation(long tick, Vec at) { }

    private final ContextBrain brain;
    private final Object lock = new Object();
    private final Map<String, PlayerObservation> players = new LinkedHashMap<>(16, 0.75f, true);
    private final Map<Key, Squad> squads = new LinkedHashMap<>(16, 0.75f, true) {
        @Override
        protected boolean removeEldestEntry(Map.Entry<Key, Squad> eldest) {
            return size() > MAX_SQUADS;
        }
    };

    public TacticsHost() {
        this(SquadDirector::decide);
    }

    public TacticsHost(Brain brain) {
        Objects.requireNonNull(brain, "brain");
        this.brain = (roster, player) -> brain.decide(roster.squad(), roster.tick(), roster.toUnits(), player);
    }

    private TacticsHost(ContextBrain brain) {
        this.brain = Objects.requireNonNull(brain, "brain");
    }

    public static TacticsHost withContext(ContextBrain brain) {
        return new TacticsHost(brain);
    }

    /**
     * One round trip. {@code rosterText} is DTR 1 (required); {@code eventsText} is DTE 1 or empty. Bad input throws
     * {@link IllegalArgumentException} with the parser's line-numbered reason, before anything is remembered.
     */
    public Decision decide(String rosterText, String eventsText) {
        Roster roster = TacticalOrders.parseRoster(Objects.requireNonNull(rosterText, "roster"));
        Events events = eventsText == null || eventsText.isBlank() ? null : TacticalOrders.parseEvents(eventsText);
        Vec latest = null;
        if (events != null) {
            for (Event e : events.events()) {
                if (e.kind() == EventKind.PLAYER) {
                    latest = e.at();
                }
            }
        }
        synchronized (lock) {
            Key key = new Key(roster.session(), roster.squad());
            Squad s = squads.get(key);
            if (s != null && roster.tick() == s.tick) {
                return new Decision(Result.REPEAT, s.spec, "repeat: tick " + s.tick);
            }
            if (s != null && roster.tick() < s.tick) {
                return new Decision(Result.STALE, "", "stale tick " + roster.tick() + " < " + s.tick);
            }
            PlayerObservation previous = players.get(roster.session());
            PlayerObservation observation = previous;
            if (latest != null && (previous == null || events.tick() > previous.tick())) {
                observation = new PlayerObservation(events.tick(), latest);
            }
            Vec player = observation == null ? null : observation.at();
            List<SquadDirector.Unit> units = roster.toUnits();
            Spec spec = player == null ? holdAll(roster.squad(), roster.tick(), units)
                    : brain.decide(roster, player);
            String wire = TacticalOrders.write(spec);
            if (observation != null) {
                players.put(roster.session(), observation);
                while (players.size() > MAX_SQUADS) {
                    players.remove(players.keySet().iterator().next());
                }
            }
            if (s == null) {
                s = new Squad();
                squads.put(key, s);
            }
            s.tick = roster.tick();
            s.spec = wire;
            return new Decision(Result.APPLY, s.spec, player == null ? "no PLAYER event yet: hold" : "decided");
        }
    }

    /** Squads remembered now (for stats). */
    public int squads() {
        synchronized (lock) {
            return squads.size();
        }
    }

    private static Spec holdAll(String squad, long tick, List<SquadDirector.Unit> units) {
        List<TacticalOrders.Order> orders = new java.util.ArrayList<>();
        for (SquadDirector.Unit u : units) {
            if (orders.size() >= TacticalOrders.MAX_ORDERS) {
                break;
            }
            orders.add(new TacticalOrders.Order(u.name(), TacticalOrders.Verb.HOLD, TacticalOrders.Side.NONE, u.at(),
                    "no sighting of the player yet"));
        }
        orders.sort(java.util.Comparator.comparing(TacticalOrders.Order::unit));
        return new Spec(squad, tick, orders);
    }
}
