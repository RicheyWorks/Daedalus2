// SPDX-License-Identifier: MIT
package com.daedalus.world.tactics;

import com.daedalus.world.tactics.SquadDirector.Unit;
import com.daedalus.world.tactics.TacticalOrders.Order;
import com.daedalus.world.tactics.TacticalOrders.Side;
import com.daedalus.world.tactics.TacticalOrders.Spec;
import com.daedalus.world.tactics.TacticalOrders.Vec;
import com.daedalus.world.tactics.TacticalOrders.Verb;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.List;
import java.util.Objects;

/** Strategic, pure encounter step. The host supplies trusted observations; Unreal owns movement and combat. */
public final class AdaptiveDirector {
    public static final int MAX_UNITS = TacticalOrders.MAX_ORDERS;
    public enum WeaponStyle { UNKNOWN, CLOSE, LONG_RANGE }

    public record Frame(String squad, String session, long tick, List<Unit> units,
                        Vec player, Vec objective, boolean objectiveThreatened, WeaponStyle weapon) {
        public Frame {
            id(squad); id(session);
            if (tick < 0 || tick > 100_000_000L) throw new IllegalArgumentException("DTO 1 tick range");
            Objects.requireNonNull(units);
            if (units.size() > MAX_UNITS) throw new IllegalArgumentException("At most 256 units per squad");
            var names = new HashSet<String>();
            for (Unit u : units) {
                Objects.requireNonNull(u); id(u.name()); point(u.at());
                if (!names.add(u.name())) throw new IllegalArgumentException("Duplicate unit");
                if (!Double.isFinite(u.health()) || !Double.isFinite(u.maxHealth())
                        || u.maxHealth() <= 0 || u.maxHealth() > 1_000_000
                        || u.health() < 0 || u.health() > u.maxHealth()) {
                    throw new IllegalArgumentException("Invalid authoritative health");
                }
            }
            units = List.copyOf(units.stream().sorted(Comparator.comparing(Unit::name)).toList());
            point(player); point(objective); Objects.requireNonNull(weapon);
        }
    }

    /** One faction's encounter-scoped receipt and bounded strategic history. Never an inventory ledger. */
    public record Memory(String faction, String session, long lastTick, int elevatedSamples,
                         int casualtyPressure, String frameHash) {
        public Memory {
            id(faction); id(session);
            if (lastTick < -1 || lastTick > 100_000_000L || elevatedSamples < 0 || elevatedSamples > 8
                    || casualtyPressure < 0 || casualtyPressure > 8
                    || frameHash == null || !frameHash.matches("[0-9a-f]{64}|-")) {
                throw new IllegalArgumentException("Invalid tactical memory");
            }
            if ((lastTick == -1) != frameHash.equals("-")) throw new IllegalArgumentException("Invalid receipt");
        }
        public static Memory initial(String faction, String session) {
            return new Memory(faction, session, -1, 0, 0, "-");
        }
        /** Explicit trusted host transition. Carries learned posture, halves casualty pressure between encounters. */
        public Memory nextEncounter(String nextSession) {
            if (session.equals(nextSession)) throw new IllegalArgumentException("A new session id is required");
            return new Memory(faction, nextSession, -1, elevatedSamples, casualtyPressure / 2, "-");
        }
    }

    public record Decision(Spec orders, Memory memory, int unitsEvaluated, int flankBudget,
                           double retreatBelow, String assessment) { }

    private AdaptiveDirector() { }

    /** Adapt a trusted Unreal DTR 1 snapshot; objective and player observations remain host-owned. */
    public static Frame fromRoster(TacticalOrders.Roster roster, Vec player, Vec objective,
                                   boolean objectiveThreatened, WeaponStyle weapon) {
        Objects.requireNonNull(roster);
        return new Frame(roster.squad(), roster.session(), roster.tick(), roster.toUnits(),
                player, objective, objectiveThreatened, weapon);
    }

    public static Decision decide(Memory before, Frame f) {
        Objects.requireNonNull(before); Objects.requireNonNull(f);
        if (!before.session().equals(f.session())) throw new IllegalArgumentException("Session mismatch");
        if (f.tick() < before.lastTick()) throw new IllegalArgumentException("Stale observation");
        String hash = frameHash(f);
        boolean duplicate = f.tick() == before.lastTick();
        if (duplicate && !hash.equals(before.frameHash())) throw new IllegalArgumentException("Conflicting observation tick");
        List<Unit> alive = f.units().stream().filter(u -> u.health() > 0).toList();
        double meanZ = alive.stream().mapToDouble(u -> u.at().z()).average().orElse(f.player().z());
        boolean contact = alive.stream().anyMatch(Unit::seesPlayer);
        boolean high = contact && f.player().z() - meanZ > 300;
        int elevated = duplicate ? before.elevatedSamples()
                : Math.min(8, Math.max(0, before.elevatedSamples() + (high ? 1 : -1)));
        int pressure = Math.max(before.casualtyPressure(), Math.min(8, f.units().size() - alive.size()));
        Memory memory = new Memory(before.faction(), before.session(), f.tick(), elevated, pressure, hash);
        double retreat = Math.min(0.45, 0.30 + pressure * 0.025);
        int flankBudget = pressure >= 2 ? 1 : 2;
        double radius = f.weapon() == WeaponStyle.LONG_RANGE ? 1200 : 900;
        boolean defend = f.objectiveThreatened() || high || elevated >= 3;
        Unit anchor = alive.stream().filter(u -> u.health() / u.maxHealth() >= retreat)
                .min(Comparator.<Unit>comparingDouble(u -> distance2(u.at(), f.objective())).thenComparing(Unit::name))
                .orElse(null);
        Spec baseline = SquadDirector.decide(f.squad(), f.tick(), alive, f.player(),
                new SquadDirector.Settings(retreat, radius, 1500, 300, 2600));
        var byName = new java.util.HashMap<String, Unit>();
        for (Unit u : alive) byName.put(u.name(), u);
        List<Order> orders = new ArrayList<>();
        int flanks = 0;
        int reinforcements = 0;
        String assessment = "contact=" + contact + "; elevation=" + elevated + "; losses=" + pressure
                + "; weapon=" + f.weapon();
        for (Order order : baseline.orders()) {
            Unit u = byName.get(order.unit());
            Order next = order;
            if (!contact) {
                next = new Order(u.name(), Verb.HOLD, Side.NONE, u.at(), "no current squad sighting; do not use hidden player position");
            } else if (u.health() / u.maxHealth() < retreat) {
                next = new Order(u.name(), Verb.RETREAT, Side.NONE,
                        SquadDirector.awayFrom(f.player(), u.at(), 1500), "preserve unit; faction casualty pressure=" + pressure);
            } else if (order.verb() != Verb.HOLD && defend && u.equals(anchor)) {
                next = new Order(u.name(), Verb.DEFEND, Side.NONE, f.objective(), "guard objective; " + assessment);
            } else if (order.verb() == Verb.FLANK || (defend && order.verb() == Verb.ATTACK)) {
                if (flanks >= flankBudget) {
                    next = new Order(u.name(), Verb.DEFEND, Side.NONE, f.objective(), "flank budget exhausted; preserve reserve");
                } else {
                    Side side = flanks++ == 0 ? Side.LEFT : Side.RIGHT;
                    next = new Order(u.name(), Verb.FLANK, side,
                            SquadDirector.flankPoint(f.player(), f.objective(), side, radius),
                            "coordinate with objective guard; " + side + "; radius=" + (int) radius);
                }
            } else if (order.verb() == Verb.DEFEND && f.objectiveThreatened() && alive.size() > 3 && reinforcements++ == 0) {
                next = new Order(u.name(), Verb.REINFORCE, Side.NONE, f.objective(), "reinforce threatened objective; one reserve only");
            }
            // A coordinate at the wire boundary may have no legal geometric retreat/flank point.
            if (!validPoint(next.at())) next = new Order(u.name(), Verb.HOLD, Side.NONE, u.at(), "target outside DTO 1 bounds");
            orders.add(next);
        }
        return new Decision(new Spec(f.squad(), f.tick(), orders), memory, f.units().size(), flankBudget, retreat, assessment);
    }

    static String digest(String text) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
    }

    private static String frameHash(Frame f) {
        // Preserve the original record text exactly: persisted DTM 1 receipts depend on it.
        // A single builder avoids intermediate Vec, Unit and collection strings per observation.
        var text = new StringBuilder(256 + f.units().size() * 160);
        text.append("Frame[squad=").append(f.squad()).append(", session=").append(f.session())
                .append(", tick=").append(f.tick()).append(", units=[");
        boolean separator = false;
        for (Unit u : f.units()) {
            if (separator) text.append(", ");
            separator = true;
            text.append("Unit[name=").append(u.name()).append(", at=");
            appendPoint(text, u.at());
            text.append(", health=").append(u.health()).append(", maxHealth=").append(u.maxHealth())
                    .append(", seesPlayer=").append(u.seesPlayer()).append(']');
        }
        text.append("], player=");
        appendPoint(text, f.player());
        text.append(", objective=");
        appendPoint(text, f.objective());
        text.append(", objectiveThreatened=").append(f.objectiveThreatened())
                .append(", weapon=").append(f.weapon()).append(']');
        return digest(text.toString());
    }

    private static void appendPoint(StringBuilder text, Vec v) {
        text.append("Vec[x=").append(v.x()).append(", y=").append(v.y()).append(", z=").append(v.z()).append(']');
    }

    private static double distance2(Vec a, Vec b) {
        double x = a.x() - b.x(), y = a.y() - b.y(), z = a.z() - b.z();
        return x * x + y * y + z * z;
    }
    static void id(String value) {
        if (value == null || !TacticalOrders.token(value)) throw new IllegalArgumentException("Invalid tactical id");
    }
    private static boolean validPoint(Vec v) {
        return v != null && Double.isFinite(v.x()) && Double.isFinite(v.y()) && Double.isFinite(v.z())
                && Math.abs(v.x()) <= TacticalOrders.MAX_COORD && Math.abs(v.y()) <= TacticalOrders.MAX_COORD
                && Math.abs(v.z()) <= TacticalOrders.MAX_COORD;
    }
    private static void point(Vec v) {
        if (!validPoint(v)) throw new IllegalArgumentException("Invalid position");
    }
}
