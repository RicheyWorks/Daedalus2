// SPDX-License-Identifier: MIT

package com.daedalus.world.parcels;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.district.DistrictOps;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * PAR01 mail route (contest gap G14): Postmaster Grue's delivery board in the Parcels. Each seeded day
 * hands the Courier a satchel of letters for plots of the district ({@link DistrictOps}); some are
 * Express with a deadline, and sometimes the Lost-Letter Ghost leaves a letter at a mailbox that must be
 * carried back to the helipad, whose helicopter flies it to another realm.
 *
 * <p><b>Boundary guidance.</b> Every mailbox stands on the street beside its plot, on the centre line of
 * the north-south road the plot faces. Routes run only on road centre lines, so a courier never cuts
 * through a claimed plot; a delivery made from inside any plot is refused ({@link Outcome#TRESPASS}).
 * {@link #waypoints} gives the turn-by-turn street path between two stops, and {@link #streetCubes} its
 * length, the true shortest street distance on the district's road grid.
 *
 * <p><b>Timed routes.</b> The par time comes from an exact solver (Held-Karp over the stops, from the
 * helipad and back) at {@link #PACE} cubes a second. Express deadlines are set from that optimal tour with
 * slack, so every day is solvable on time. Medals are bands of the par time.
 *
 * <p>Deterministic: one {@code SplittableRandom(seed)} per day. The session is host-authoritative: each
 * letter is delivered once and only from within {@link #REACH} of its mailbox.
 */
public final class MailRoute {

    /** Courier pace on the street, cubes per second. */
    public static final int PACE = 5;
    /** How close (horizontal cubes) the courier must stand to a mailbox or the helipad. */
    public static final double REACH = 2.0;
    public static final int MIN_LETTERS = 6;
    public static final int MAX_LETTERS = 10;
    /** Number of north-south (and east-west) roads: the ring roads and the streets between blocks. */
    public static final int ROADS = DistrictOps.BLOCKS + 1;
    static final int BLOCK_PITCH = 2 * DistrictOps.PLOT + DistrictOps.ROAD;

    /** What a letter asks of the courier. */
    public enum Kind { STANDARD, EXPRESS, GHOST_PICKUP }

    /** Postmaster Grue's medal for the day. */
    public enum Medal { GOLD, SILVER, BRONZE, NONE }

    /** A place on the street: the {@code road}-th north-south road at height-free coordinate z. */
    public record Stop(int road, int z) {

        public Stop {
            if (road < 0 || road >= ROADS) {
                throw new IllegalArgumentException("No road " + road);
            }
        }

        public int x() {
            return roadX(road);
        }

        public BlockCoordinate at() {
            return new BlockCoordinate(x(), DistrictOps.GROUND_Y + 1, z);
        }
    }

    /** One letter: its id, the plot it is for, its mailbox, kind, and deadline (seconds, Express only). */
    public record Letter(int id, int plot, Stop mailbox, Kind kind, int deadline) {
    }

    /** One day's satchel, its par tour (stop order by letter index) and par time. */
    public record Day(long seed, List<Letter> letters, List<Integer> parOrder, int parCubes, int parSeconds) {

        public Day {
            letters = List.copyOf(letters);
            parOrder = List.copyOf(parOrder);
        }
    }

    /** The outcome of one session action. */
    public enum Outcome { ON_TIME, LATE, PICKED_UP, UNKNOWN_LETTER, ALREADY_DONE, TOO_FAR, TRESPASS, NOT_HOLDING }

    /** The end-of-day receipt. */
    public record Receipt(int delivered, int late, int undelivered, boolean ghostReturned, int stamps, int seconds,
                          int parSeconds, Medal medal) {
    }

    private MailRoute() {
    }

    /** x of the centre line of the {@code k}-th north-south road. */
    public static int roadX(int k) {
        return DistrictOps.MIN_X + k * BLOCK_PITCH + DistrictOps.ROAD / 2;
    }

    /** z of the centre line of the {@code k}-th east-west road. */
    public static int roadZ(int k) {
        return DistrictOps.MIN_Z + k * BLOCK_PITCH + DistrictOps.ROAD / 2;
    }

    /** The helipad on the plaza: the crossing of the middle roads, where every round starts and ends. */
    public static Stop depot() {
        return new Stop(ROADS / 2, roadZ(ROADS / 2));
    }

    /** The mailbox of plot {@code n}: on the road its side of the block faces, level with its middle. */
    public static Stop mailbox(int n) {
        ParcelBounds b = DistrictOps.plotBounds(n);
        int col = n % DistrictOps.PLOTS_PER_SIDE;
        int road = col / 2 + col % 2;
        return new Stop(road, (b.minZ() + b.maxZ() + 1) / 2);
    }

    /** The east-west road that makes the shortest detour between two north-south roads. */
    private static int crossing(Stop a, Stop b) {
        int best = 0;
        long bestLen = Long.MAX_VALUE;
        for (int m = 0; m < ROADS; m++) {
            long len = Math.abs(a.z() - roadZ(m)) + (long) Math.abs(roadZ(m) - b.z());
            if (len < bestLen) {
                bestLen = len;
                best = m;
            }
        }
        return best;
    }

    /** Shortest street distance in cubes between two stops, along road centre lines only. */
    public static int streetCubes(Stop a, Stop b) {
        if (a.road() == b.road()) {
            return Math.abs(a.z() - b.z());
        }
        int m = crossing(a, b);
        return Math.abs(a.z() - roadZ(m)) + Math.abs(a.x() - b.x()) + Math.abs(roadZ(m) - b.z());
    }

    /** Turn-by-turn street path from {@code a} to {@code b}: the corners, start and end included. */
    public static List<BlockCoordinate> waypoints(Stop a, Stop b) {
        List<BlockCoordinate> out = new ArrayList<>();
        out.add(a.at());
        if (a.road() != b.road()) {
            int z = roadZ(crossing(a, b));
            int y = DistrictOps.GROUND_Y + 1;
            out.add(new BlockCoordinate(a.x(), y, z));
            out.add(new BlockCoordinate(b.x(), y, z));
        }
        out.add(b.at());
        return out;
    }

    /** True when (x, z) lies inside a claimable plot: the courier stays on the street. */
    public static boolean trespass(int x, int z) {
        return DistrictOps.plotAt(x, z) >= 0;
    }

    /** Total cubes of a tour from the helipad through {@code order} (letter indices) and back. */
    public static int tourCubes(List<Letter> letters, List<Integer> order) {
        Stop at = depot();
        int sum = 0;
        for (int i : order) {
            Stop next = letters.get(i).mailbox();
            sum += streetCubes(at, next);
            at = next;
        }
        return sum + streetCubes(at, depot());
    }

    /** Seconds to walk {@code cubes} at {@link #PACE}, rounded up. */
    public static int seconds(int cubes) {
        return (cubes + PACE - 1) / PACE;
    }

    /** The exact shortest tour (Held-Karp) from the helipad through every letter's mailbox and back. */
    static List<Integer> solve(List<Letter> letters) {
        int n = letters.size();
        int full = (1 << n) - 1;
        int[][] cost = new int[1 << n][n];
        int[][] prev = new int[1 << n][n];
        for (int[] row : cost) {
            Arrays.fill(row, Integer.MAX_VALUE);
        }
        for (int i = 0; i < n; i++) {
            cost[1 << i][i] = streetCubes(depot(), letters.get(i).mailbox());
            prev[1 << i][i] = -1;
        }
        for (int mask = 1; mask <= full; mask++) {
            for (int last = 0; last < n; last++) {
                int c = cost[mask][last];
                if (c == Integer.MAX_VALUE || (mask & (1 << last)) == 0) {
                    continue;
                }
                for (int next = 0; next < n; next++) {
                    if ((mask & (1 << next)) != 0) {
                        continue;
                    }
                    int m2 = mask | (1 << next);
                    int c2 = c + streetCubes(letters.get(last).mailbox(), letters.get(next).mailbox());
                    if (c2 < cost[m2][next]) {
                        cost[m2][next] = c2;
                        prev[m2][next] = last;
                    }
                }
            }
        }
        int best = 0;
        int bestCost = Integer.MAX_VALUE;
        for (int last = 0; last < n; last++) {
            int c = cost[full][last] + streetCubes(letters.get(last).mailbox(), depot());
            if (c < bestCost) {
                bestCost = c;
                best = last;
            }
        }
        List<Integer> order = new ArrayList<>();
        int mask = full;
        for (int at = best; at >= 0; ) {
            order.add(0, at);
            int p = prev[mask][at];
            mask &= ~(1 << at);
            at = p;
        }
        return order;
    }

    /** The day Postmaster Grue posts for {@code seed}. */
    public static Day day(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x9A501L);
        int count = MIN_LETTERS + rng.nextInt(MAX_LETTERS - MIN_LETTERS + 1);
        boolean ghost = rng.nextBoolean();
        Set<Integer> taken = new HashSet<>();
        List<Integer> plots = new ArrayList<>();
        while (plots.size() < count + (ghost ? 1 : 0)) {
            int n = rng.nextInt(DistrictOps.PLOTS_PER_SIDE * DistrictOps.PLOTS_PER_SIDE);
            if (DistrictOps.isPlot(n) && taken.add(n)) {
                plots.add(n);
            }
        }
        List<Letter> draft = new ArrayList<>();
        boolean[] express = new boolean[plots.size()];
        for (int i = 0; i < plots.size(); i++) {
            Kind kind = ghost && i == plots.size() - 1 ? Kind.GHOST_PICKUP
                    : rng.nextInt(4) == 0 ? Kind.EXPRESS : Kind.STANDARD;
            express[i] = kind == Kind.EXPRESS;
            draft.add(new Letter(i, plots.get(i), mailbox(plots.get(i)), kind, 0));
        }
        List<Integer> order = solve(draft);
        int cubes = tourCubes(draft, order);
        // Deadlines from the optimal tour's arrival times, with a quarter of slack plus ten seconds.
        int[] deadline = new int[draft.size()];
        Stop at = depot();
        int walked = 0;
        for (int i : order) {
            walked += streetCubes(at, draft.get(i).mailbox());
            at = draft.get(i).mailbox();
            deadline[i] = express[i] ? seconds(walked) * 5 / 4 + 10 : 0;
        }
        List<Letter> letters = new ArrayList<>();
        for (Letter l : draft) {
            letters.add(new Letter(l.id(), l.plot(), l.mailbox(), l.kind(), deadline[l.id()]));
        }
        return new Day(seed, letters, order, cubes, seconds(cubes));
    }

    static double reach(BlockCoordinate a, BlockCoordinate b) {
        int dx = a.x() - b.x();
        int dz = a.z() - b.z();
        return Math.sqrt((double) dx * dx + (double) dz * dz);
    }

    /** Medal for finishing in {@code seconds} against {@code par}, every letter delivered. */
    public static Medal medal(int seconds, int par) {
        if (seconds * 10L <= par * 11L) {
            return Medal.GOLD;
        }
        if (seconds * 20L <= par * 27L) {
            return Medal.SILVER;
        }
        if (seconds * 4L <= par * 7L) {
            return Medal.BRONZE;
        }
        return Medal.NONE;
    }

    /** One courier's round; the host owns this state. */
    public static final class Session {

        private final Day day;
        private final Outcome[] done;
        private boolean holdingGhost;

        public Session(Day day) {
            this.day = day;
            this.done = new Outcome[day.letters().size()];
        }

        /** Deliver (or, for the Ghost's letter, pick up) letter {@code id} at {@code elapsed} seconds. */
        public Outcome deliver(int id, BlockCoordinate courier, int elapsed) {
            if (id < 0 || id >= done.length) {
                return Outcome.UNKNOWN_LETTER;
            }
            if (done[id] != null) {
                return Outcome.ALREADY_DONE;
            }
            if (trespass(courier.x(), courier.z())) {
                return Outcome.TRESPASS;
            }
            Letter l = day.letters().get(id);
            if (reach(courier, l.mailbox().at()) > REACH) {
                return Outcome.TOO_FAR;
            }
            Outcome o;
            if (l.kind() == Kind.GHOST_PICKUP) {
                holdingGhost = true;
                o = Outcome.PICKED_UP;
            } else {
                o = l.kind() == Kind.EXPRESS && elapsed > l.deadline() ? Outcome.LATE : Outcome.ON_TIME;
            }
            done[id] = o;
            return o;
        }

        public boolean holdingGhost() {
            return holdingGhost;
        }

        /** Close the round at the helipad. Null when the courier is not there yet. */
        public Receipt finish(BlockCoordinate courier, int elapsed) {
            if (reach(courier, depot().at()) > REACH) {
                return null;
            }
            int delivered = 0;
            int late = 0;
            int undelivered = 0;
            int stamps = 0;
            for (int i = 0; i < done.length; i++) {
                Letter l = day.letters().get(i);
                if (l.kind() == Kind.GHOST_PICKUP) {
                    continue;
                }
                if (done[i] == null) {
                    undelivered++;
                } else {
                    delivered++;
                    stamps++;
                    if (done[i] == Outcome.LATE) {
                        late++;
                    } else if (l.kind() == Kind.EXPRESS) {
                        stamps++;
                    }
                }
            }
            if (holdingGhost) {
                stamps += 2;
            }
            Medal m = undelivered > 0 ? Medal.NONE : medal(elapsed, day.parSeconds());
            return new Receipt(delivered, late, undelivered, holdingGhost, stamps, elapsed, day.parSeconds(), m);
        }
    }
}
