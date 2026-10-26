// SPDX-License-Identifier: MIT

package com.daedalus.world.parcels;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.ParcelBounds;
import com.daedalus.world.district.DistrictOps;
import com.daedalus.world.parcels.MailRoute.Day;
import com.daedalus.world.parcels.MailRoute.Kind;
import com.daedalus.world.parcels.MailRoute.Letter;
import com.daedalus.world.parcels.MailRoute.Medal;
import com.daedalus.world.parcels.MailRoute.Outcome;
import com.daedalus.world.parcels.MailRoute.Receipt;
import com.daedalus.world.parcels.MailRoute.Session;
import com.daedalus.world.parcels.MailRoute.Stop;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * PAR01 mail route (G14): mailboxes stand on the street beside their plots, routes stay on road centre
 * lines, the par tour is the exact optimum, Express deadlines are met by it, and the host session
 * delivers once, from the street, within reach, and medals against par.
 */
class MailRouteTest {

    @Test
    void theHelipadIsOnGateZerosLineAndThePlaza() {
        Stop d = MailRoute.depot();
        assertThat(d.x()).isEqualTo(DistrictOps.padBerth().x());
        assertThat(d.z()).isEqualTo(DistrictOps.padBerth().z());
        assertThat(DistrictOps.plaza().contains(new BlockCoordinate(d.x(), 0, d.z()))).isTrue();
    }

    @Test
    void everyMailboxIsOnTheStreetBesideItsPlot() {
        for (int n = 0; n < 64; n++) {
            if (!DistrictOps.isPlot(n)) {
                continue;
            }
            Stop m = MailRoute.mailbox(n);
            ParcelBounds b = DistrictOps.plotBounds(n);
            assertThat(MailRoute.trespass(m.x(), m.z())).isFalse();
            assertThat(m.z()).isBetween(b.minZ(), b.maxZ());
            int gap = Math.min(Math.abs(m.x() - b.minX()), Math.abs(m.x() - b.maxX()));
            assertThat(gap).as("plot %d", n).isLessThanOrEqualTo(DistrictOps.ROAD / 2 + 1);
        }
    }

    @Test
    void streetDistanceIsAMetricAndMatchesItsWaypointsWhichNeverEnterAPlot() {
        List<Stop> stops = new ArrayList<>();
        stops.add(MailRoute.depot());
        for (int n = 0; n < 64; n += 3) {
            if (DistrictOps.isPlot(n)) {
                stops.add(MailRoute.mailbox(n));
            }
        }
        for (Stop a : stops) {
            for (Stop b : stops) {
                int d = MailRoute.streetCubes(a, b);
                assertThat(d).isEqualTo(MailRoute.streetCubes(b, a));
                assertThat(d).isGreaterThanOrEqualTo(Math.abs(a.x() - b.x()) + Math.abs(a.z() - b.z()));
                List<BlockCoordinate> w = MailRoute.waypoints(a, b);
                int len = 0;
                for (int i = 1; i < w.size(); i++) {
                    BlockCoordinate p = w.get(i - 1);
                    BlockCoordinate q = w.get(i);
                    assertThat(p.x() == q.x() || p.z() == q.z()).isTrue();
                    len += Math.abs(p.x() - q.x()) + Math.abs(p.z() - q.z());
                    int steps = Math.max(Math.abs(p.x() - q.x()), Math.abs(p.z() - q.z()));
                    for (int s = 0; s <= steps; s++) {
                        int x = p.x() + Integer.signum(q.x() - p.x()) * s;
                        int z = p.z() + Integer.signum(q.z() - p.z()) * s;
                        assertThat(MailRoute.trespass(x, z)).as("(%d,%d)", x, z).isFalse();
                    }
                }
                assertThat(len).isEqualTo(d);
                for (Stop c : stops.subList(0, 6)) {
                    assertThat(d).isLessThanOrEqualTo(MailRoute.streetCubes(a, c) + MailRoute.streetCubes(c, b));
                }
            }
        }
    }

    @Test
    void daysAreSeededWithDistinctRealPlots() {
        assertThat(MailRoute.day(4)).isEqualTo(MailRoute.day(4));
        assertThat(MailRoute.day(4).letters()).isNotEqualTo(MailRoute.day(5).letters());
        int ghosts = 0;
        for (long seed = 0; seed < 100; seed++) {
            Day d = MailRoute.day(seed);
            Set<Integer> plots = new HashSet<>();
            int ghost = 0;
            for (Letter l : d.letters()) {
                assertThat(DistrictOps.isPlot(l.plot())).isTrue();
                assertThat(plots.add(l.plot())).isTrue();
                assertThat(l.mailbox()).isEqualTo(MailRoute.mailbox(l.plot()));
                ghost += l.kind() == Kind.GHOST_PICKUP ? 1 : 0;
                assertThat(l.deadline() > 0).isEqualTo(l.kind() == Kind.EXPRESS);
            }
            assertThat(ghost).isLessThanOrEqualTo(1);
            ghosts += ghost;
            assertThat(d.letters().size() - ghost).isBetween(MailRoute.MIN_LETTERS, MailRoute.MAX_LETTERS);
            assertThat(d.parOrder()).hasSize(d.letters().size()).doesNotHaveDuplicates();
            assertThat(d.parSeconds()).isEqualTo(MailRoute.seconds(d.parCubes()));
        }
        assertThat(ghosts).isBetween(20, 80);
    }

    private static int bestByBruteForce(List<Letter> letters, List<Integer> prefix, boolean[] used) {
        if (prefix.size() == letters.size()) {
            return MailRoute.tourCubes(letters, prefix);
        }
        int best = Integer.MAX_VALUE;
        for (int i = 0; i < letters.size(); i++) {
            if (!used[i]) {
                used[i] = true;
                prefix.add(i);
                best = Math.min(best, bestByBruteForce(letters, prefix, used));
                prefix.remove(prefix.size() - 1);
                used[i] = false;
            }
        }
        return best;
    }

    @Test
    void theParTourIsTheExactOptimum() {
        int checked = 0;
        for (long seed = 0; seed < 200 && checked < 12; seed++) {
            Day d = MailRoute.day(seed);
            if (d.letters().size() > 8) {
                continue;
            }
            checked++;
            assertThat(MailRoute.tourCubes(d.letters(), d.parOrder())).isEqualTo(d.parCubes());
            assertThat(d.parCubes()).as("seed %d", seed)
                    .isEqualTo(bestByBruteForce(d.letters(), new ArrayList<>(), new boolean[d.letters().size()]));
        }
        assertThat(checked).isEqualTo(12);
    }

    /** Walk the par tour, delivering at each mailbox; returns the session after finishing. */
    private static Receipt walkPar(Day d, int slowdownPercent) {
        Session s = new Session(d);
        Stop at = MailRoute.depot();
        int cubes = 0;
        for (int i : d.parOrder()) {
            Letter l = d.letters().get(i);
            cubes += MailRoute.streetCubes(at, l.mailbox());
            at = l.mailbox();
            int t = MailRoute.seconds(cubes) * slowdownPercent / 100;
            Outcome o = s.deliver(l.id(), l.mailbox().at(), t);
            if (l.kind() == Kind.GHOST_PICKUP) {
                assertThat(o).isEqualTo(Outcome.PICKED_UP);
            } else if (slowdownPercent == 100) {
                assertThat(o).as("seed %d letter %d", d.seed(), i).isEqualTo(Outcome.ON_TIME);
            }
        }
        BlockCoordinate pad = MailRoute.depot().at();
        return s.finish(pad, d.parSeconds() * slowdownPercent / 100);
    }

    @Test
    void everyDayIsSolvableOnTimeForGold() {
        for (long seed = 0; seed < 200; seed++) {
            Day d = MailRoute.day(seed);
            Receipt r = walkPar(d, 100);
            boolean ghost = d.letters().stream().anyMatch(l -> l.kind() == Kind.GHOST_PICKUP);
            assertThat(r.undelivered()).isZero();
            assertThat(r.late()).isZero();
            assertThat(r.medal()).isEqualTo(Medal.GOLD);
            assertThat(r.ghostReturned()).isEqualTo(ghost);
            long express = d.letters().stream().filter(l -> l.kind() == Kind.EXPRESS).count();
            assertThat(r.stamps()).isEqualTo(r.delivered() + (int) express + (ghost ? 2 : 0));
        }
    }

    @Test
    void medalsFollowParBands() {
        assertThat(MailRoute.medal(110, 100)).isEqualTo(Medal.GOLD);
        assertThat(MailRoute.medal(111, 100)).isEqualTo(Medal.SILVER);
        assertThat(MailRoute.medal(135, 100)).isEqualTo(Medal.SILVER);
        assertThat(MailRoute.medal(136, 100)).isEqualTo(Medal.BRONZE);
        assertThat(MailRoute.medal(175, 100)).isEqualTo(Medal.BRONZE);
        assertThat(MailRoute.medal(176, 100)).isEqualTo(Medal.NONE);
    }

    @Test
    void aSlowRoundGoesLateOnExpressAndLosesTheMedal() {
        for (long seed = 0; seed < 100; seed++) {
            Day d = MailRoute.day(seed);
            if (d.letters().stream().noneMatch(l -> l.kind() == Kind.EXPRESS)) {
                continue;
            }
            Receipt r = walkPar(d, 300);
            assertThat(r.late()).isPositive();
            assertThat(r.medal()).isEqualTo(Medal.NONE);
            return;
        }
        throw new AssertionError("no express day in 100 seeds");
    }

    @Test
    void deliveriesAreFromTheStreetWithinReachAndOnce() {
        Day d = MailRoute.day(9);
        Session s = new Session(d);
        Letter l = d.letters().stream().filter(x -> x.kind() != Kind.GHOST_PICKUP).findFirst().orElseThrow();
        BlockCoordinate box = l.mailbox().at();
        assertThat(s.deliver(99, box, 0)).isEqualTo(Outcome.UNKNOWN_LETTER);
        assertThat(s.deliver(l.id(), new BlockCoordinate(box.x(), box.y(), box.z() + 3), 0)).isEqualTo(Outcome.TOO_FAR);
        ParcelBounds plot = DistrictOps.plotBounds(l.plot());
        int inside = box.x() < plot.minX() ? plot.minX() : plot.maxX();
        assertThat(s.deliver(l.id(), new BlockCoordinate(inside, box.y(), box.z()), 0)).isEqualTo(Outcome.TRESPASS);
        assertThat(s.deliver(l.id(), box, 0)).isEqualTo(Outcome.ON_TIME);
        assertThat(s.deliver(l.id(), box, 0)).isEqualTo(Outcome.ALREADY_DONE);
        assertThat(s.finish(box, 10)).isNull();
        Receipt r = s.finish(MailRoute.depot().at(), 10);
        assertThat(r.delivered()).isEqualTo(1);
        assertThat(r.undelivered()).isPositive();
        assertThat(r.medal()).isEqualTo(Medal.NONE);
    }
}
