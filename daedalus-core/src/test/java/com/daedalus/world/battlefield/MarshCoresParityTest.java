// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Supplier;
import org.junit.jupiter.api.Test;

/**
 * Java = C++ golden vectors for the marsh-lane ecology cores: G570 (port of G202 DroughtOdds), G583 (G200
 * CraneSpread), G585 (G194 CraneCohorts), G589 (G251 TranslocationPlan), G591 (G504 ReedCeiling) and G593 (G507
 * ReedRelease); later ecology ports add a method here. Each engines/unreal/core-test/marsh_*_parity.txt is written
 * from this class (run with -Dmarsh.parity.write=true) and replayed by the matching marsh_*_core_test.cpp against its
 * DaedalusMarsh*Core.h. Doubles are printed with Double.toString (shortest round-trip form), so C++ can compare them
 * with a tolerance.
 */
class MarshCoresParityTest {

    private static final Path CORE_TEST = Path.of("..", "engines", "unreal", "core-test");

    static List<String> droughtOdds() {
        double[] mus = {-0.02, 0.0, Math.log(1.029), 0.03};
        double[] sigmas = {0.1, 0.2, 0.3};
        int[][] flocks = {{40, 10}, {30, 10}, {80, 20}, {12, 10}};
        List<String> out = new ArrayList<>();
        long seed = 1;
        for (double mu : mus) {
            for (double sigma : sigmas) {
                for (int[] f : flocks) {
                    DroughtOdds o = DroughtOdds.of(new DroughtOdds.Settings(mu, sigma, f[0], f[1]));
                    int runs = 300;
                    int years = 30;
                    int substeps = 4;
                    long hits = Math.round(o.simulate(runs, years, substeps, seed) * runs);
                    double t = 10 + 5 * (seed % 9);
                    out.add("mu=" + mu + " sigma=" + sigma + " start=" + f[0] + " threshold=" + f[1] + " within T=" + t
                            + " within=" + o.within(t) + " ultimate=" + o.ultimate() + " median=" + o.medianYears()
                            + " runs=" + runs + " years=" + years + " substeps=" + substeps + " seed=" + seed
                            + " hits=" + hits);
                    seed++;
                }
            }
        }
        return out;
    }

    static List<String> reedRelease() {
        // reed options, startCranes, startHawks, budget, perYear, releaseYears, horizon, threshold, sigma, runs
        Object[][] plans = {
            {List.of(10.0, 40.0, 80.0, 150.0), 6.0, 3.0, 6, 3, 3, 25, 4.0, 0.15, 40},
            {List.of(25.0, 55.0), 10.0, 2.0, 4, 2, 2, 20, 6.0, 0.25, 50},
            {List.of(5.0, 40.0, 110.0), 3.0, 4.0, 3, 3, 2, 15, 2.0, 0.0, 20},
            {List.of(30.0, 64.0, 90.0), 20.0, 5.0, 0, 1, 2, 30, 8.0, 0.3, 40}};
        List<String> out = new ArrayList<>();
        for (int c = 0; c < plans.length; c++) {
            Object[] q = plans[c];
            @SuppressWarnings("unchecked")
            List<Double> reed = (List<Double>) q[0];
            ReedRelease.Settings s = new ReedRelease.Settings(ReedCeiling.Settings.DEFAULT, reed, (double) q[1],
                    (double) q[2], (int) q[3], (int) q[4], (int) q[5], (int) q[6], (double) q[7], (double) q[8],
                    (int) q[9]);
            long seed = 23 + 19L * c;
            ReedRelease rr = ReedRelease.of(s, seed);
            ReedRelease.Plan best = rr.best();
            ReedRelease.Plan fast = rr.fast();
            StringBuilder line = new StringBuilder();
            line.append("reed=").append(csvD(reed)).append(" n0=").append(s.startCranes()).append(" p0=")
                    .append(s.startHawks()).append(" budget=").append(s.budget()).append(" perYear=")
                    .append(s.perYear()).append(" releaseYears=").append(s.releaseYears()).append(" horizon=")
                    .append(s.horizon()).append(" threshold=").append(s.threshold()).append(" sigma=")
                    .append(s.sigma()).append(" runs=").append(s.runs()).append(" seed=").append(seed);
            for (int i = 0; i < reed.size(); i++) {
                ReedRelease.Plan b = rr.bestSchedule(reed.get(i));
                line.append(" sched").append(i).append('=').append(csv(b.schedule())).append(" risk").append(i)
                        .append('=').append(b.risk());
            }
            line.append(" bestHa=").append(best.hectares()).append(" best=").append(csv(best.schedule()))
                    .append(" bestRisk=").append(best.risk()).append(" fastHa=").append(fast.hectares())
                    .append(" fast=").append(csv(fast.schedule())).append(" fastRisk=").append(fast.risk());
            out.add(line.toString());
        }
        return out;
    }

    private static String csvD(List<Double> a) {
        StringBuilder s = new StringBuilder();
        for (int i = 0; i < a.size(); i++) {
            s.append(i == 0 ? "" : ",").append(a.get(i));
        }
        return s.toString();
    }

    @Test
    void reedReleaseMatchesCpp() throws IOException {
        check("marsh_reed_release_parity.txt", "G507 ReedRelease", MarshCoresParityTest::reedRelease);
    }

    static List<String> reedCeiling() {
        // r, reedHectares, cranesPerHectare, attack, handling, conversion, mortality
        double[][] marshes = {{0.4, 40, 2, 0.02, 0.5, 0.6, 0.15}, {0.4, 80, 2, 0.02, 0.5, 0.6, 0.15},
            {0.4, 10, 2, 0.02, 0.5, 0.6, 0.15}, {0.8, 30, 3, 0.05, 0.3, 0.4, 0.1}, {0.25, 60, 1.5, 0.01, 1.0, 0.5, 0.2},
            {1.2, 25, 4, 0.03, 0.2, 0.7, 0.3}, {0.4, 6, 2, 0.02, 0.5, 0.6, 0.15}};
        List<String> out = new ArrayList<>();
        for (int c = 0; c < marshes.length; c++) {
            double[] m = marshes[c];
            ReedCeiling rc = ReedCeiling.of(new ReedCeiling.Settings(m[0], m[1], m[2], m[3], m[4], m[5], m[6]));
            double n0 = rc.settings().capacity() * 0.6;
            double p0 = 5 + c;
            double[] rate = rc.rate(n0, p0);
            StringBuilder s = new StringBuilder();
            s.append("r=").append(m[0]).append(" reed=").append(m[1]).append(" perHa=").append(m[2]).append(" a=")
                    .append(m[3]).append(" h=").append(m[4]).append(" e=").append(m[5]).append(" m=").append(m[6])
                    .append(" nstar=").append(rc.cranesStar()).append(" pstar=").append(rc.hawksStar())
                    .append(" kh=").append(rc.hopfCapacity()).append(" cycleHa=").append(rc.cycleHectares())
                    .append(" hawkHa=").append(rc.hawkHectares()).append(" regime=").append(rc.regime().ordinal())
                    .append(" trace=").append(rc.trace()).append(" n0=").append(n0).append(" p0=").append(p0)
                    .append(" dn=").append(rate[0]).append(" dp=").append(rate[1]);
            out.add(s.toString());
            out.add(run("rk4", rc.integrate(n0, p0, 60, 0.02)));
            out.add(run("noisy seed=" + (17 + c), rc.noisy(n0, p0, 40, 17 + c)));
        }
        return out;
    }

    private static String run(String head, ReedCeiling.Run r) {
        StringBuilder s = new StringBuilder("run=" + head);
        s.append(" points=").append(r.points().size()).append(" min=").append(r.minCranes()).append(" max=")
                .append(r.maxCranes()).append(" finalHawks=").append(r.finalHawks());
        for (ReedCeiling.Point p : r.points()) {
            if (Math.round(p.year()) % 5 == 0) {
                s.append(" n").append(Math.round(p.year())).append('=').append(p.cranes()).append(" p")
                        .append(Math.round(p.year())).append('=').append(p.hawks());
            }
        }
        return s.toString();
    }

    @Test
    void reedCeilingMatchesCpp() throws IOException {
        check("marsh_reed_ceiling_parity.txt", "G504 ReedCeiling", MarshCoresParityTest::reedCeiling);
    }

    static List<String> translocationPlan() {
        double[][] flocks = {{0.5, 0.7, 0.85, 0.9, 0.15, 0.45}, {0.5, 0.7, 0.85, 0.8, 0.15, 0.45},
            {0.6, 0.8, 0.9, 0.95, 0.3, 1.2}};
        // start, budget, perYear, releaseYears, horizon, threshold, sigma, cohort, runs
        double[][] plans = {{12, 10, 6, 5, 30, 10, 0.2, 3, 120}, {8, 6, 3, 3, 20, 6, 0.3, 3, 100},
            {12, 8, 4, 4, 25, 10, 0.25, 2, 100}, {5, 4, 4, 2, 15, 4, 0.0, 0, 50}, {20, 0, 2, 3, 10, 12, 0.4, 1, 80},
            {10, 9, 5, 4, 30, 8, 0.35, 3, 90}, {12, 3, 3, 1, 1, 10, 0.2, 3, 60}, {5, 0, 0, 2, 10, 10, 0.2, 3, 40},
            {30, 6, 2, 3, 12, 5, 0.5, 0, 70}};
        List<String> out = new ArrayList<>();
        for (int c = 0; c < plans.length; c++) {
            double[] f = flocks[c % flocks.length];
            double[] p = plans[c];
            CraneCohorts flock = CraneCohorts.marsh(new CraneCohorts.Settings(f[0], f[1], f[2], f[3], f[4], f[5], 10),
                    1);
            TranslocationPlan.Settings s = new TranslocationPlan.Settings((int) p[0], (int) p[1], (int) p[2],
                    (int) p[3], (int) p[4], p[5], p[6], (int) p[7], (int) p[8]);
            long seed = 7 + 31L * c;
            TranslocationPlan plan = TranslocationPlan.of(flock, s, seed);
            TranslocationPlan.Plan best = plan.best();
            TranslocationPlan.Plan greedy = plan.greedy();
            int[] front = plan.frontLoaded();
            int[] even = plan.even();
            out.add("flock=" + (c % flocks.length) + " start=" + s.start() + " budget=" + s.budget() + " perYear="
                    + s.perYear() + " releaseYears=" + s.releaseYears() + " horizon=" + s.horizon() + " threshold="
                    + s.threshold() + " sigma=" + s.sigma() + " cohort=" + s.cohort() + " runs=" + s.runs() + " seed="
                    + seed + " front=" + csv(front) + " frontRisk=" + plan.risk(front) + " even=" + csv(even)
                    + " evenRisk=" + plan.risk(even) + " back=" + csv(plan.backLoaded()) + " backRisk="
                    + plan.risk(plan.backLoaded()) + " best=" + csv(best.schedule()) + " bestRisk=" + best.risk()
                    + " greedy=" + csv(greedy.schedule()) + " greedyRisk=" + greedy.risk() + " bestLo="
                    + plan.riskInterval(toArray(best.schedule()))[0] + " bestHi="
                    + plan.riskInterval(toArray(best.schedule()))[1] + " survival=" + csvD(survivalSample(plan,
                    toArray(best.schedule()))));
        }
        // start, budget, perYear, releaseYears, horizon, threshold, sigma, cohort, runs
        double[][] bad = {{-1, 0, 0, 1, 1, 10, 0.2, 3, 5}, {0, -1, 0, 1, 1, 10, 0.2, 3, 5},
            {0, 0, -1, 1, 1, 10, 0.2, 3, 5}, {0, 0, 0, 0, 1, 10, 0.2, 3, 5}, {0, 0, 1, 2, 1, 10, 0.2, 3, 5},
            {0, 0, 1, 1, 1, 0, 0.2, 3, 5}, {0, 0, 1, 1, 1, 10, -0.1, 3, 5},
            {0, 0, 1, 1, 1, 10, Double.POSITIVE_INFINITY, 3, 5}, {0, 0, 1, 1, 1, 10, 0.2, 4, 5},
            {0, 0, 1, 1, 1, 10, 0.2, 3, 0}, {0, 9, 2, 3, 5, 10, 0.2, 3, 5}, {5, 4, 2, 2, 5, 10, 0.2, 0, 5}};
        for (double[] q : bad) {
            String why = TranslocationPlan.Settings.problem((int) q[0], (int) q[1], (int) q[2], (int) q[3],
                    (int) q[4], q[5], q[6], (int) q[7], (int) q[8]);
            out.add("problem start=" + (int) q[0] + " budget=" + (int) q[1] + " perYear=" + (int) q[2]
                    + " releaseYears=" + (int) q[3] + " horizon=" + (int) q[4] + " threshold=" + q[5] + " sigma="
                    + q[6] + " cohort=" + (int) q[7] + " runs=" + (int) q[8] + " why="
                    + (why == null ? "ok" : why.replace(' ', '_')));
        }
        return out;
    }

    private static String csv(int[] a) {
        StringBuilder s = new StringBuilder();
        for (int i = 0; i < a.length; i++) {
            s.append(i == 0 ? "" : ",").append(a[i]);
        }
        return s.toString();
    }

    private static List<Double> survivalSample(TranslocationPlan plan, int[] schedule) {
        double[] s = plan.survival(schedule);
        List<Double> out = new ArrayList<>();
        for (int t = 0; t < s.length; t += 5) {
            out.add(s[t]);
        }
        out.add(s[s.length - 1]);
        return out;
    }

    private static int[] toArray(List<Integer> a) {
        return a.stream().mapToInt(Integer::intValue).toArray();
    }

    private static String csv(List<Integer> a) {
        return csv(a.stream().mapToInt(Integer::intValue).toArray());
    }

    @Test
    void translocationPlanMatchesCpp() throws IOException {
        check("marsh_translocation_plan_parity.txt", "G251 TranslocationPlan",
                MarshCoresParityTest::translocationPlan);
    }

    static List<String> craneCohorts() {
        double[][] rates = {{0.5, 0.7, 0.85, 0.9, 0.15, 0.45}, {0.5, 0.7, 0.85, 0.8, 0.15, 0.45},
            {0.5, 0.7, 0.85, 0.9, 0, 0}, {0.6, 0.8, 0.9, 0.95, 0.3, 1.2}, {0.3, 0.5, 0.6, 0, 1.5, 0},
            {0.4, 0.6, 0.7, 0.85, 0, 0.6}, {0.9, 0.9, 0.9, 0.97, 0.8, 2.5}};
        int[][] starts = {{20, 10, 8, 30}, {0, 0, 0, 12}, {40, 0, 0, 0}, {5, 5, 5, 5}, {0, 0, 50, 0},
            {100, 60, 40, 120}, {2, 1, 1, 3}};
        List<String> out = new ArrayList<>();
        for (int c = 0; c < rates.length; c++) {
            double[] r = rates[c];
            CraneCohorts m = CraneCohorts.marsh(new CraneCohorts.Settings(r[0], r[1], r[2], r[3], r[4], r[5], 25), 1);
            StringBuilder s = new StringBuilder();
            s.append("s0=").append(r[0]).append(" s1=").append(r[1]).append(" s2=").append(r[2]).append(" p=")
                    .append(r[3]).append(" fs=").append(r[4]).append(" fa=").append(r[5]).append(" years=25")
                    .append(" lambda=").append(m.lambda()).append(" trend=").append(m.trend().ordinal())
                    .append(" best=").append(m.bestRelease());
            for (int i = 0; i < CraneCohorts.COHORTS; i++) {
                s.append(" w").append(i).append('=').append(m.stableAges().get(i))
                        .append(" v").append(i).append('=').append(m.reproductiveValue().get(i));
            }
            for (int i = 0; i < CraneCohorts.COHORTS; i++) {
                for (int j = 0; j < CraneCohorts.COHORTS; j++) {
                    s.append(" e").append(i).append(j).append('=').append(m.elasticity(i, j));
                }
            }
            double[] stepped = m.step(new double[] {10, 20, 30, 40});
            for (int i = 0; i < CraneCohorts.COHORTS; i++) {
                s.append(" step").append(i).append('=').append(stepped[i]);
            }
            int[] st = starts[c];
            s.append(" start=").append(st[0]).append(',').append(st[1]).append(',').append(st[2]).append(',')
                    .append(st[3]).append(" ae=").append(m.adultEquivalents(st));
            out.add(s.toString());
            long seed = 101 + 13L * c;
            CraneCohorts.Report rep = m.project(st, seed);
            StringBuilder p = new StringBuilder("seed=" + seed + " outcome=" + rep.outcome().ordinal() + " flock="
                    + rep.flock() + " nyears=" + rep.years().size());
            for (CraneCohorts.Year y : rep.years()) {
                p.append(" y").append(y.index()).append('=').append(y.chicks()).append(',').append(y.juveniles())
                        .append(',').append(y.subadults()).append(',').append(y.adults());
            }
            out.add(p.toString());
        }
        return out;
    }

    @Test
    void craneCohortsMatchesCpp() throws IOException {
        check("marsh_crane_cohorts_parity.txt", "G194 CraneCohorts", MarshCoresParityTest::craneCohorts);
    }

    static List<String> craneSpread() {
        double[][] tunings = {{1.5, 1.0, 0.25, 100}, {1.2, 0.8, 0.2, 60}, {2.0, 1.5, 0.5, 150}, {0.9, 1.0, 0.25, 100},
            {1.05, 2.0, 0.5, 80}, {3.0, 0.5, 0.25, 40}};
        List<String> out = new ArrayList<>();
        long seed = 11;
        for (double[] k : tunings) {
            CraneSpread m = CraneSpread.marsh(new CraneSpread.Settings(k[0], k[1], k[2], k[3], 40), 1);
            out.add("lambda=" + k[0] + " dispersal=" + k[1] + " cell=" + k[2] + " capacity=" + k[3] + " years=40"
                    + " mgf=" + m.mgf(0.3 / k[1]) + " cstar=" + m.spreadingSpeed());
            for (int noisy = 0; noisy < 2; noisy++) {
                CraneSpread.Report r = noisy == 0 ? m.run() : m.run(seed);
                StringBuilder s = new StringBuilder(noisy == 0 ? "run=det" : "run=noisy seed=" + seed);
                s.append(" speed=").append(r.speed()).append(" reach5=").append(r.yearReached(5.0));
                for (CraneSpread.Year y : r.years()) {
                    if (y.index() % 5 == 0) {
                        s.append(" front").append(y.index()).append('=').append(y.front())
                                .append(" birds").append(y.index()).append('=').append(y.birds());
                    }
                }
                out.add(s.toString());
            }
            seed += 7;
        }
        return out;
    }

    @Test
    void craneSpreadMatchesCpp() throws IOException {
        check("marsh_crane_spread_parity.txt", "G200 CraneSpread", MarshCoresParityTest::craneSpread);
    }

    @Test
    void droughtOddsMatchesCpp() throws IOException {
        check("marsh_drought_odds_parity.txt", "G202 DroughtOdds", MarshCoresParityTest::droughtOdds);
    }

    private static void check(String file, String game, Supplier<List<String>> lines) throws IOException {
        Path path = CORE_TEST.resolve(file);
        List<String> actual = lines.get();
        if (Boolean.getBoolean("marsh.parity.write")) {
            List<String> body = new ArrayList<>();
            body.add("# " + game + " golden vectors: written by MarshCoresParityTest.java, replayed by "
                    + file.replace("_parity.txt", "_core_test.cpp") + ".");
            body.addAll(actual);
            Files.write(path, body, StandardCharsets.UTF_8);
        }
        List<String> expected = Files.readAllLines(path, StandardCharsets.UTF_8).stream()
                .filter(l -> !l.startsWith("#") && !l.isBlank()).toList();
        assertEquals(actual.size(), expected.size(), file);
        for (int i = 0; i < actual.size(); i++) {
            assertEquals(expected.get(i), actual.get(i), file + " line " + i);
        }
    }
}
