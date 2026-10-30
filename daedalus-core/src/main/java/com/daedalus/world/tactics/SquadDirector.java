// SPDX-License-Identifier: MIT

package com.daedalus.world.tactics;

import com.daedalus.world.tactics.TacticalOrders.Order;
import com.daedalus.world.tactics.TacticalOrders.Side;
import com.daedalus.world.tactics.TacticalOrders.Spec;
import com.daedalus.world.tactics.TacticalOrders.Vec;
import com.daedalus.world.tactics.TacticalOrders.Verb;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * The baseline squad director (ADR-060), ported line for line from {@code DaedalusTacticsCore.h}'s {@code Decide}.
 * Unreal runs the C++ copy when no Java director is attached. This copy is the deterministic, explainable starting
 * point for the Java Adaptive Combat Director (NEXT-PHASE-COMBAT-AI.md): a richer director can replace any rule here
 * and still write the same DTO 1. Given the same inputs, it writes the same spec byte for byte as the C++;
 * {@code TacticsParityTest} checks 40 squads.
 * <ul>
 *   <li>Below {@code retreatBelow} health: RETREAT, straight away from the player.</li>
 *   <li>The nearest healthy unit ATTACKs, or DEFENDs the squad's centre when the player holds high ground.</li>
 *   <li>The next two FLANK, LEFT then RIGHT.</li>
 *   <li>Everyone else DEFENDs the centre.</li>
 *   <li>Nobody in range: everyone HOLDs where they are.</li>
 * </ul>
 * Cost is O(n log n). The result does not depend on input order: units are ranked by distance, then name.
 */
public final class SquadDirector {

    public record Unit(String name, Vec at, double health, double maxHealth, boolean seesPlayer) {
    }

    public record Settings(double retreatBelow, double flankRadius, double retreatDistance, double highGround,
                           double engage) {
        public static final Settings DEFAULT = new Settings(0.3, 900, 1500, 300, 2600);
    }

    /**
     * Where the cover is (ADR-060 + pythagoras's ADR-061). Given a spot and the threat, returns the best cover cell near
     * the spot as {x, y, score}, with the score being cover plus concealment from the threat. It avoids fire.
     * {@code BattlefieldEcology::bestCover} has exactly this shape, so it can be passed as a method reference.
     */
    @FunctionalInterface
    public interface CoverField {
        double[] bestCover(double ux, double uy, double thx, double thy, double radiusCm);
    }

    /** How orders use cover: search radius for each kind of order, and the least score worth moving for. */
    public record CoverRules(double flankSearch, double retreatSearch, double defendSearch, double minScore) {
        public static final CoverRules DEFAULT = new CoverRules(300, 600, 400, 0.4);
    }

    private SquadDirector() {
    }

    /** Where to stand to flank: Radius from the player, a quarter turn round from the squad's side of them. */
    public static Vec flankPoint(Vec player, Vec from, Side way, double radius) {
        double dx = from.x() - player.x();
        double dy = from.y() - player.y();
        double l = Math.sqrt(dx * dx + dy * dy);
        if (l < 1e-6) {
            dx = 1;
            dy = 0;
        } else {
            dx /= l;
            dy /= l;
        }
        double s = way == Side.LEFT ? 1.0 : -1.0;
        return new Vec(player.x() + -dy * s * radius, player.y() + dx * s * radius, player.z());
    }

    /** A point Distance from From, straight away from the player. */
    public static Vec awayFrom(Vec player, Vec from, double distance) {
        double dx = from.x() - player.x();
        double dy = from.y() - player.y();
        double l = Math.sqrt(dx * dx + dy * dy);
        if (l < 1e-6) {
            dx = 1;
            dy = 0;
        } else {
            dx /= l;
            dy /= l;
        }
        return new Vec(from.x() + dx * distance, from.y() + dy * distance, from.z());
    }

    private static double d2(Unit u, Vec p) {
        double dx = u.at().x() - p.x();
        double dy = u.at().y() - p.y();
        double dz = u.at().z() - p.z();
        return dx * dx + dy * dy + dz * dz;
    }

    public static Spec decide(String squad, long tick, List<Unit> input, Vec player) {
        return decide(squad, tick, input, player, Settings.DEFAULT);
    }

    public static Spec decide(String squad, long tick, List<Unit> input, Vec player, Settings s) {
        return decide(squad, tick, input, player, s, null, CoverRules.DEFAULT);
    }

    /**
     * As the baseline, but FLANK, RETREAT and DEFEND points move into the best cover nearby, when it scores at least
     * {@code rules.minScore()} against the player. Each such order's why says so, with the score. ATTACK keeps the
     * player's own spot. With no cover field this is exactly the baseline, the same spec as the C++.
     */
    public static Spec decide(String squad, long tick, List<Unit> input, Vec player, Settings s, CoverField cover,
                              CoverRules rules) {
        if (input.isEmpty()) {
            return new Spec(squad, tick, List.of());
        }
        List<Unit> units = new ArrayList<>(input);
        units.sort(Comparator.<Unit>comparingDouble(u -> d2(u, player)).thenComparing(Unit::name));
        if (units.size() > TacticalOrders.MAX_ORDERS) {
            // A spec carries at most MAX_ORDERS orders; a bigger squad orders its nearest, as the C++ does.
            units = new ArrayList<>(units.subList(0, TacticalOrders.MAX_ORDERS));
        }
        double mx = 0;
        double my = 0;
        double mz = 0;
        for (Unit u : units) {   // summed in ranked order, as in C++, so the centre is bit-identical
            mx += u.at().x();
            my += u.at().y();
            mz += u.at().z();
        }
        Vec mid = new Vec(mx / units.size(), my / units.size(), mz / units.size());
        boolean inRange = Math.sqrt(d2(units.get(0), player)) <= s.engage();
        boolean high = player.z() - mid.z() > s.highGround();
        int healthy = 0;
        List<Order> out = new ArrayList<>();
        for (Unit u : units) {
            double frac = u.maxHealth() > 0 ? u.health() / u.maxHealth() : 0;
            int dist = (int) Math.sqrt(d2(u, player));
            Verb verb;
            Side side = Side.NONE;
            Vec at;
            String why;
            if (!inRange) {
                verb = Verb.HOLD;
                at = u.at();
                why = "player out of range (" + dist + " cm)";
            } else if (frac < s.retreatBelow()) {
                verb = Verb.RETREAT;
                at = awayFrom(player, u.at(), s.retreatDistance());
                why = "health " + (int) (frac * 100) + "%";
            } else {
                int rank = healthy++;
                if (rank == 0) {
                    verb = high ? Verb.DEFEND : Verb.ATTACK;
                    at = high ? mid : player;
                    why = high ? "player holds high ground; hold the approach" : "closest (" + dist + " cm)";
                } else if (rank <= 2) {
                    verb = Verb.FLANK;
                    side = rank == 1 ? Side.LEFT : Side.RIGHT;
                    at = flankPoint(player, mid, side, s.flankRadius());
                    why = "cut off escape, " + (rank == 1 ? "left" : "right");
                } else {
                    verb = Verb.DEFEND;
                    at = mid;
                    why = "hold the squad's centre";
                }
            }
            if (cover != null && (verb == Verb.FLANK || verb == Verb.RETREAT || verb == Verb.DEFEND)) {
                double search = verb == Verb.FLANK ? rules.flankSearch() : verb == Verb.RETREAT ? rules.retreatSearch()
                        : rules.defendSearch();
                double[] c = cover.bestCover(at.x(), at.y(), player.x(), player.y(), search);
                if (c != null && c.length >= 3 && Double.isFinite(c[0]) && Double.isFinite(c[1]) && c[2] >= rules.minScore()) {
                    at = new Vec(c[0], c[1], at.z());
                    why = why + ", into cover (" + String.format(java.util.Locale.ROOT, "%.2f", c[2]) + ")";
                }
            }
            out.add(new Order(u.name(), verb, side, at, why));
        }
        out.sort(Comparator.comparing(Order::unit));
        return new Spec(squad, tick, out);
    }
}
