// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import com.daedalus.world.BlockCoordinate;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.function.IntFunction;

/**
 * Where every ark is, and which are in the air (ADR-020). Pure and clock-free: every method takes
 * {@code now}, so a test drives time and the server passes its clock. Not thread-safe; the owner
 * serialises access (WorldService's world lock).
 *
 * <p>Only departures from home are state: an ark that has never sailed is at its home slot and
 * has no row. Rows survive restarts through {@link #toLines()} / {@link #fromLines}.
 */
public final class ArkFleet {

    /** Cruise speed in cubes per second, and the fixed time to cast off and to tie up. */
    public static final double SPEED = 12.0;
    public static final long HARBOUR_MS = 4_000;

    private record Row(int slot, Voyage voyage) {
    }

    private final TreeMap<String, Row> rows = new TreeMap<>();

    /** The slot an ark is moored at, or its destination while sailing. */
    public int slotOf(String arkId, int homeSlot) {
        Row r = rows.get(arkId);
        return r == null ? homeSlot : r.slot();
    }

    /** The voyage underway, or null when moored. Arrived voyages are settled by {@link #settle}. */
    public Voyage voyageOf(String arkId) {
        Row r = rows.get(arkId);
        return r == null ? null : r.voyage();
    }

    public static long duration(BlockCoordinate from, BlockCoordinate to) {
        double dx = to.x() - from.x();
        double dy = to.y() - from.y();
        double dz = to.z() - from.z();
        double cubes = Math.sqrt(dx * dx + dy * dy + dz * dz);
        return HARBOUR_MS + Math.round(cubes * 1000.0 / SPEED);
    }

    /**
     * Order an ark to another island. {@code berthOf} answers the berth of a raised slot, or null
     * when no island is there.
     */
    public Outcome sail(String arkId, int homeSlot, int toSlot, IntFunction<BlockCoordinate> berthOf,
                        long now) {
        Row r = rows.get(arkId);
        if (r != null && r.voyage() != null && !r.voyage().arrived(now)) {
            return new Outcome(VoyageResult.UNDERWAY, r.voyage());
        }
        int at = slotOf(arkId, homeSlot);
        if (at == toSlot) {
            return new Outcome(VoyageResult.ALREADY_THERE, null);
        }
        BlockCoordinate to = berthOf.apply(toSlot);
        if (to == null) {
            return new Outcome(VoyageResult.NO_SUCH_ISLAND, null);
        }
        BlockCoordinate from = berthOf.apply(at);
        Voyage v = new Voyage(arkId, at, toSlot, now, now + duration(from == null ? to : from, to));
        rows.put(arkId, new Row(toSlot, v));
        return new Outcome(VoyageResult.SAILING, v);
    }

    /** Voyages that have arrived by {@code now}; their arks are moored at the destination after. */
    public List<Voyage> settle(long now) {
        List<Voyage> arrived = new ArrayList<>();
        for (Map.Entry<String, Row> e : rows.entrySet()) {
            Voyage v = e.getValue().voyage();
            if (v != null && v.arrived(now)) {
                arrived.add(v);
                e.setValue(new Row(e.getValue().slot(), null));
            }
        }
        return arrived;
    }

    /** One line per ark that has ever left home: {@code arkId slot [from to depart arrive]}. */
    public List<String> toLines() {
        List<String> out = new ArrayList<>();
        for (Map.Entry<String, Row> e : rows.entrySet()) {
            Row r = e.getValue();
            Voyage v = r.voyage();
            out.add(v == null ? e.getKey() + " " + r.slot()
                    : e.getKey() + " " + r.slot() + " " + v.fromSlot() + " " + v.toSlot() + " "
                    + v.departAt() + " " + v.arriveAt());
        }
        return out;
    }

    public static ArkFleet fromLines(List<String> lines) {
        ArkFleet fleet = new ArkFleet();
        for (String line : lines) {
            String t = line.trim();
            if (t.isEmpty() || t.startsWith("#")) {
                continue;
            }
            String[] f = t.split("\\s+");
            if (f.length == 2) {
                fleet.rows.put(f[0], new Row(Integer.parseInt(f[1]), null));
            } else if (f.length == 6) {
                Voyage v = new Voyage(f[0], Integer.parseInt(f[2]), Integer.parseInt(f[3]),
                        Long.parseLong(f[4]), Long.parseLong(f[5]));
                fleet.rows.put(f[0], new Row(Integer.parseInt(f[1]), v));
            } else {
                throw new IllegalArgumentException("Bad fleet row: " + t);
            }
        }
        return fleet;
    }

    /** What an order produced: the named result and, when sailing or underway, the voyage. */
    public record Outcome(VoyageResult result, Voyage voyage) {
    }
}
