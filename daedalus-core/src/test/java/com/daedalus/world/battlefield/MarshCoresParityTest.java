// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;
import org.junit.jupiter.api.Test;

/**
 * Java = C++ golden vectors for the marsh-lane ecology cores: G570 (port of G202 DroughtOdds), G583 (G200
 * CraneSpread), G585 (G194 CraneCohorts), G589 (G251 TranslocationPlan), G591 (G504 ReedCeiling), G593 (G507
 * ReedRelease), G610 (G188 HawkDove), G611 (G183 Metapopulation), G612 (G176 ShoalHarvest), G613 (G172
 * HerdOutbreak), G614 (G163 FounderDrift), G615 (G156 MarkRecapture) and G616 (G142 AlleeRelease); later ecology
 * ports add a method here.
 * Each engines/unreal/core-test/marsh_*_parity.txt is written from this class (run with -Dmarsh.parity.write=true) and
 * replayed by the matching marsh_*_core_test.cpp against its DaedalusMarsh*Core.h. Doubles are printed with
 * Double.toString (shortest round-trip form), so C++ can compare them with a tolerance.
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
                    toArray(best.schedule()))) + " polished=" + csv(plan.greedyPolished().schedule())
                    + " polishedRisk=" + plan.greedyPolished().risk() + " cohortRisks="
                    + csvD(java.util.Arrays.stream(plan.cohortRisks()).boxed().toList()) + " calendar="
                    + String.join(";", plan.releaseCalendar(toArray(best.schedule()))).replace(' ', '_'));
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

    static List<String> metapopulation() {
        double[][] tunings = {{100, 0.5, 0.1, 200, 80}, {60, 0.3, 0.2, 120, 30}, {40, 1.2, 0.05, 90, 5},
            {80, 0.15, 0.2, 100, 60}, {50, 0.0, 0.3, 40, 50}, {30, 2.0, 1.0, 30, 30}, {2, 0.8, 0.1, 25, 1},
            {120, 0.6, 0.12, 1, 60}};
        int[][] plans = {{}, {10, 20}, {5, 10, 30, 15}};
        List<String> out = new ArrayList<>();
        long seed = 1;
        for (double[] t : tunings) {
            Metapopulation.Settings s = new Metapopulation.Settings((int) t[0], t[1], t[2], (int) t[3], (int) t[4]);
            for (int[] plan : plans) {
                Metapopulation v = Metapopulation.valley(s, seed);
                StringBuilder p = new StringBuilder();
                for (int k = 0; k + 1 < plan.length; k += 2) {
                    boolean ok = v.plough(plan[k], plan[k + 1]);
                    p.append(p.length() == 0 ? "" : ",").append(plan[k]).append(':').append(plan[k + 1]).append(':')
                            .append(ok ? 1 : 0);
                }
                Metapopulation.Report r = v.run();
                long sum = 0;
                for (Metapopulation.Year y : r.years()) {
                    sum += (long) y.occupied() * (y.index() + 1);
                }
                Metapopulation.Year last = r.years().get(r.years().size() - 1);
                Metapopulation.Year mid = r.years().get(r.years().size() / 2);
                out.add("patches=" + s.patches() + " colonize=" + s.colonize() + " extinction=" + s.extinction()
                        + " years=" + s.years() + " start=" + s.start() + " seed=" + seed + " plough="
                        + (p.length() == 0 ? "-" : p) + " eq20=" + v.equilibrium(0.2) + " threshold="
                        + v.ploughThreshold() + " outcome=" + r.outcome() + " occupancy=" + r.occupancy() + " late="
                        + r.lateMean() + " band=" + r.band() + " first=" + r.years().get(0).occupied() + " midIndex="
                        + mid.index() + " mid=" + mid.occupied() + " last=" + last.occupied() + " ploughed="
                        + last.ploughed() + " weighted=" + sum);
                seed++;
            }
        }
        return out;
    }

    @Test
    void metapopulationMatchesCpp() throws IOException {
        check("marsh_metapopulation_parity.txt", "G183 Metapopulation", MarshCoresParityTest::metapopulation);
    }

    static List<String> shoalHarvest() {
        double[][] tunings = {{1000, 0.6, 0.5, 50, 0.05}, {1000, 0.6, 0.0, 50, 0.05}, {500, 0.3, 0.2, 80, 0.1},
            {2000, 1.0, 0.9, 40, 0.0}, {800, 0.8, 0.3, 60, 0.2}, {1, 0.05, 0.1, 30, 0.05}, {300, 0.45, 0.6, 1, 0.05},
            {1200, 0.9, 0.4, 100, 0.08}};
        List<String> out = new ArrayList<>();
        long seed = 1;
        for (double[] t : tunings) {
            ShoalHarvest.Settings s = new ShoalHarvest.Settings(t[0], t[1], t[2], (int) t[3], t[4]);
            ShoalHarvest h = ShoalHarvest.shoal(s, seed);
            Object[][] plays = {{ShoalHarvest.Rule.QUOTA, h.msy()}, {ShoalHarvest.Rule.EFFORT, h.msyEffort()},
                {ShoalHarvest.Rule.QUOTA, h.msy() / 2}, {ShoalHarvest.Rule.EFFORT, 1.0}};
            for (Object[] p : plays) {
                ShoalHarvest.Rule rule = (ShoalHarvest.Rule) p[0];
                double level = (double) p[1];
                ShoalHarvest.Report r = ShoalHarvest.shoal(s, seed).run(rule, level);
                double weighted = 0;
                for (ShoalHarvest.Year y : r.years()) {
                    weighted += (y.shoal() + y.catchTonnes()) * (y.index() + 1);
                }
                ShoalHarvest.Year mid = r.years().get(r.years().size() / 2);
                ShoalHarvest.Year last = r.years().get(r.years().size() - 1);
                out.add("capacity=" + s.capacity() + " growth=" + s.growth() + " noise=" + s.noise() + " years="
                        + s.years() + " collapse=" + s.collapse() + " seed=" + seed + " rule=" + rule + " level="
                        + level + " msy=" + h.msy() + " msyEffort=" + h.msyEffort() + " outcome=" + r.outcome()
                        + " shoal=" + r.shoal() + " total=" + r.total() + " mean=" + r.meanCatch() + " band="
                        + r.band() + " b0=" + r.years().get(0).shoal() + " c0=" + r.years().get(0).catchTonnes()
                        + " midIndex=" + mid.index() + " bm=" + mid.shoal() + " cm=" + mid.catchTonnes() + " bl="
                        + last.shoal() + " cl=" + last.catchTonnes() + " weighted=" + weighted);
            }
            seed++;
        }
        return out;
    }

    @Test
    void shoalHarvestMatchesCpp() throws IOException {
        check("marsh_shoal_harvest_parity.txt", "G176 ShoalHarvest", MarshCoresParityTest::shoalHarvest);
    }

    static List<String> herdOutbreak() {
        double[][] tunings = {{200, 2.5, 150, 60}, {200, 2.5, 50, 60}, {120, 4.0, 200, 40}, {300, 1.5, 100, 80},
            {80, 0.8, 10, 30}, {50, 6.0, 49, 20}, {2, 1.0, 1, 5}, {150, 3.0, 90, 1}};
        List<String> out = new ArrayList<>();
        long seed = 1;
        for (double[] t : tunings) {
            HerdOutbreak.Settings s = new HerdOutbreak.Settings((int) t[0], t[1], (int) t[2], (int) t[3]);
            for (int plan = 0; plan < 3; plan++) {
                HerdOutbreak h = HerdOutbreak.herd(s, seed);
                int vacc = plan == 0 ? 0 : (int) Math.ceil(h.threshold() * s.herd() * (plan == 1 ? 0.5 : 1.2));
                boolean vaccOk = h.vaccinate(vacc);
                boolean fenceOk = plan == 2 ? h.fence(3, 0.4) : h.fence(-1, 0.5);
                HerdOutbreak.Report r = h.run();
                long weighted = 0;
                for (HerdOutbreak.Generation g : r.generations()) {
                    weighted += (long) (g.sick() * 1000 + g.susceptible()) * g.index();
                }
                int gens = r.generations().size();
                HerdOutbreak.Generation first = gens == 0 ? null : r.generations().get(0);
                HerdOutbreak.Generation last = gens == 0 ? null : r.generations().get(gens - 1);
                out.add("herd=" + s.herd() + " r0=" + s.r0() + " doses=" + s.doses() + " generations="
                        + s.generations() + " seed=" + seed + " plan=" + plan + " vacc=" + vacc + " vaccOk="
                        + (vaccOk ? 1 : 0) + " fenceOk=" + (fenceOk ? 1 : 0) + " threshold=" + h.threshold()
                        + " final=" + HerdOutbreak.finalSize(s.r0()) + " outcome=" + r.outcome() + " sick=" + r.sick()
                        + " share=" + r.share() + " vaccinated=" + r.vaccinated() + " band=" + r.band() + " gens="
                        + gens + " firstSick=" + (first == null ? 0 : first.sick()) + " lastIndex="
                        + (last == null ? 0 : last.index()) + " lastLeft=" + (last == null ? 0 : last.susceptible())
                        + " weighted=" + weighted);
                seed++;
            }
        }
        return out;
    }

    @Test
    void herdOutbreakMatchesCpp() throws IOException {
        check("marsh_herd_outbreak_parity.txt", "G172 HerdOutbreak", MarshCoresParityTest::herdOutbreak);
    }

    static List<String> founderDrift() {
        double[][] tunings = {{20, 20, 20, 40, 40, 0.2}, {10, 30, 15, 20, 30, 1.5}, {40, 24, 12, 30, 0, 0.0},
            {6, 6, 30, 10, 60, 3.0}, {2, 2, 8, 5, 8, 0.5}, {16, 40, 10, 25, 5, 0.8}, {30, 30, 1, 12, 3, 2.0},
            {12, 12, 25, 16, 100, 1.0}};
        List<String> out = new ArrayList<>();
        long seed = 1;
        for (double[] t : tunings) {
            FounderDrift.Settings s = new FounderDrift.Settings((int) t[0], (int) t[1], (int) t[2], (int) t[3],
                    (int) t[4], t[5]);
            for (int plan = 0; plan < 3; plan++) {
                FounderDrift d = FounderDrift.aviary(s, seed);
                int mid = (s.generations() + 1) / 2;
                boolean breedOk = plan == 0 || d.breed(mid, plan == 1 ? 1 : 2, plan == 1 ? 1 : 3);
                boolean migOk = d.migrants(plan == 2 ? 2 : 0);
                boolean badOk = d.breed(s.generations() + 1, 1, 1) || d.breed(1, 0, 1) || d.migrants(-1);
                FounderDrift.Report r = d.run();
                long weighted = 0;
                for (FounderDrift.Generation g : r.generations()) {
                    weighted += ((long) g.alleles() * 1000 + g.migrants() * 100 + g.males() * 10 + g.females())
                            * g.index();
                }
                FounderDrift.Generation first = r.generations().get(0);
                FounderDrift.Generation last = r.generations().get(r.generations().size() - 1);
                out.add("founders=" + s.founders() + " capacity=" + s.capacity() + " generations=" + s.generations()
                        + " loci=" + s.loci() + " migrantPool=" + s.migrantPool() + " lethal=" + s.lethal() + " seed="
                        + seed + " plan=" + plan + " breedOk=" + (breedOk ? 1 : 0) + " migOk=" + (migOk ? 1 : 0)
                        + " badOk=" + (badOk ? 1 : 0) + " ne=" + FounderDrift.effectiveSize(3, 7) + " hm="
                        + FounderDrift.harmonicMean(List.of(20.0, 2.0, 20.0)) + " expected=" + r.expected()
                        + " outcome=" + r.outcome() + " h0=" + r.founderDiversity() + " retained=" + r.retained()
                        + " survival=" + r.survival(0.8) + " d1=" + first.diversity() + " a1=" + first.alleles()
                        + " dl=" + last.diversity() + " al=" + last.alleles() + " weighted=" + weighted);
                seed++;
            }
        }
        return out;
    }

    @Test
    void founderDriftMatchesCpp() throws IOException {
        check("marsh_founder_drift_parity.txt", "G163 FounderDrift", MarshCoresParityTest::founderDrift);
    }

    static List<String> markRecapture() {
        double[][] tunings = {{240, 60, 0.012, 0, 1, 0}, {240, 60, 0.012, 0.3, 1, 0}, {500, 80, 0.01, 0, 0.5, 0.1},
            {150, 40, 0.03, 0.1, 1.8, 0.2}, {80, 20, 0.05, 1, 1, 0}, {1, 2, 0.5, 0, 1, 0}, {300, 100, 0.002, 0, 3, 0},
            {1000, 50, 0.02, 0.05, 0.8, 0.3}};
        List<String> out = new ArrayList<>();
        long seed = 1;
        for (double[] t : tunings) {
            MarkRecapture.Settings s = new MarkRecapture.Settings((int) t[0], (int) t[1], t[2], t[3], t[4], t[5]);
            int[][] plans = {{0, 0}, {s.traps() / 4, s.traps() - s.traps() / 4}, {s.traps(), 1}};
            for (int[] p : plans) {
                MarkRecapture refuge = MarkRecapture.refuge(s, seed);
                boolean ok = p[0] == 0 || refuge.plan(p[0], p[1]);
                MarkRecapture.Census c = refuge.run();
                out.add("population=" + s.population() + " traps=" + s.traps() + " perTrap=" + s.perTrap()
                        + " tagLoss=" + s.tagLoss() + " trapResponse=" + s.trapResponse() + " turnover="
                        + s.turnover() + " seed=" + seed + " first=" + p[0] + " second=" + p[1] + " planOk="
                        + (ok ? 1 : 0) + " chance10=" + refuge.catchChance(10) + " marked=" + c.marked() + " caught="
                        + c.caught() + " recaptured=" + c.recaptured() + " lp=" + c.lincolnPetersen() + " chapman="
                        + c.chapman() + " variance=" + c.variance() + " low=" + c.low() + " high=" + c.high()
                        + " verdict=" + c.verdict() + " quota=" + c.quota(0.2) + " greedy=" + c.greedyQuota(0.2)
                        + " band=" + c.band(0.2));
                seed++;
            }
        }
        return out;
    }

    @Test
    void markRecaptureMatchesCpp() throws IOException {
        check("marsh_mark_recapture_parity.txt", "G156 MarkRecapture", MarshCoresParityTest::markRecapture);
    }

    static List<String> alleeRelease() {
        double[][] tunings = {{40, 40, 0.75, 30, 1.0, 150, 50}, {120, 40, 0.75, 30, 1.0, 150, 50},
            {60, 30, 0.9, 10, 0.6, 200, 80}, {30, 25, 0.5, 40, 1.0, 100, 20}, {0, 10, 0.8, 0, 0.5, 50, 5},
            {200, 50, 0.85, 60, 0.9, 400.5, 150}, {10, 1, 1.0, 5, 1.0, 20, 10}, {80, 35, 0.7, 20, 0.8, 120, 60}};
        List<String> out = new ArrayList<>();
        long seed = 1;
        for (double[] t : tunings) {
            AlleeRelease.Settings s = new AlleeRelease.Settings((int) t[0], (int) t[1], t[2], t[3], t[4], t[5],
                    (int) t[6]);
            int[][] plans = {{0, s.budget()}, {0, s.budget() / 4, 1, s.budget() / 4, 2, s.budget() / 4, 3,
                s.budget() / 4}, {0, s.budget() / 2, s.years(), 1, 0, s.budget() + 1, 1, 0}};
            for (int plan = 0; plan < plans.length; plan++) {
                AlleeRelease m = AlleeRelease.marsh(s, seed);
                StringBuilder p = new StringBuilder();
                for (int k = 0; k + 1 < plans[plan].length; k += 2) {
                    boolean ok = m.release(plans[plan][k], plans[plan][k + 1]);
                    p.append(p.length() == 0 ? "" : ",").append(ok ? 1 : 0);
                }
                AlleeRelease.Report r = m.run();
                long weighted = 0;
                for (AlleeRelease.Year y : r.years()) {
                    weighted += ((long) y.flock() * 10000 + y.released() * 1000 + y.nests() * 10 + y.fledged())
                            * (y.index() + 1);
                }
                AlleeRelease.Year last = r.years().get(r.years().size() - 1);
                out.add("budget=" + s.budget() + " years=" + s.years() + " survival=" + s.survival() + " mateHalf="
                        + s.mateHalf() + " fledge=" + s.fledge() + " capacity=" + s.capacity() + " goal=" + s.goal()
                        + " seed=" + seed + " plan=" + plan + " oks=" + p + " left=" + m.left() + " threshold="
                        + m.threshold() + " g10=" + m.growth(10) + " g40=" + m.growth(40) + " outcome=" + r.outcome()
                        + " flock=" + r.flock() + " peak=" + r.peak() + " band=" + r.band() + " lastNests="
                        + last.nests() + " weighted=" + weighted);
                seed++;
            }
        }
        return out;
    }

    @Test
    void alleeReleaseMatchesCpp() throws IOException {
        check("marsh_allee_release_parity.txt", "G142 AlleeRelease", MarshCoresParityTest::alleeRelease);
    }

    static List<String> hawkDove() {
        double[][] tunings = {{40, 4, 10, 10, 6, 60}, {60, 4, 10, 10, 10, 80}, {50, 6, 4, 10, 8, 70},
            {30, 2, 12, 5, 5, 60}, {80, 5, 5, 8, 6, 55}, {40, 3, 0, 4, 4, 50}, {2, 4, 10, 10, 3, 20},
            {25, 4, 10, 10, 6, 1}};
        List<String> out = new ArrayList<>();
        long seed = 1;
        for (double[] t : tunings) {
            HawkDove.Settings s = new HawkDove.Settings((int) t[0], t[1], t[2], t[3], (int) t[4], (int) t[5]);
            int n = s.herd();
            for (int start : new int[] {0, n / 4, n / 2, n}) {
                HawkDove ridge = HawkDove.ridge(s, seed);
                HawkDove.Report r = ridge.run(start);
                StringBuilder b = new StringBuilder("herd=" + n + " value=" + s.value() + " cost=" + s.cost()
                        + " base=" + s.base() + " rounds=" + s.rounds() + " seasons=" + s.seasons() + " seed=" + seed
                        + " start=" + start + " ess=" + ridge.ess() + " payHawk=" + ridge.expectedPayoff(true, 0.3)
                        + " payDove=" + ridge.expectedPayoff(false, 0.3) + " outcome=" + r.outcome() + " hawks="
                        + r.hawks() + " late=" + r.lateHawks() + " band=" + r.band());
                int[] picks = {1, (s.seasons() + 1) / 2, s.seasons()};
                for (int k = 0; k < picks.length; k++) {
                    HawkDove.Season q = r.seasons().get(picks[k] - 1);
                    b.append(" s").append(k).append('=').append(q.index()).append(" h").append(k).append('=')
                            .append(q.hawks()).append(" hp").append(k).append('=').append(q.hawkPayoff())
                            .append(" dp").append(k).append('=').append(q.dovePayoff());
                }
                out.add(b.toString());
                seed++;
            }
        }
        return out;
    }

    @Test
    void hawkDoveMatchesCpp() throws IOException {
        check("marsh_hawk_dove_parity.txt", "G188 HawkDove", MarshCoresParityTest::hawkDove);
    }

    @Test
    void droughtOddsMatchesCpp() throws IOException {
        check("marsh_drought_odds_parity.txt", "G202 DroughtOdds", MarshCoresParityTest::droughtOdds);
    }

    static List<String> fairPar() {
        List<String> out = new ArrayList<>();
        double[][] fixed = {{0.5}, {0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0}, {0.3, 0.3, 0.3, 0.3},
            {0.9, 0.2, 0.55, 0.7, 0.2, 0.35, 0.8}, {0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0}};
        double[] perfect = {0.5, 0.95, 0.3, 0.75, 2.0};
        for (int c = 0; c < fixed.length; c++) {
            out.add("case=fixed" + c + " " + pars(FairPar.calibrate(fixed[c], perfect[c])));
        }
        for (int run = 0; run < 6; run++) {
            out.add("bot run=" + run + " sched=" + csv(FairPar.botSchedule(41, run, 10, 6, 5)) + " u="
                    + FairPar.uniform(41, run, 2, 3) + " pick=" + FairPar.pick(41, run, 1, 0, 6));
        }
        double[][] flocks = {{0.5, 0.7, 0.85, 0.9, 0.15, 0.45}, {0.5, 0.7, 0.85, 0.8, 0.15, 0.45}};
        // start, budget, perYear, releaseYears, horizon, threshold, sigma, cohort, plan runs, bot runs, flock
        double[][] plans = {{12, 10, 6, 5, 30, 10, 0.2, 3, 400, 200, 0}, {8, 6, 3, 3, 20, 6, 0.3, 3, 100, 60, 1},
            {12, 8, 4, 4, 25, 10, 0.25, 2, 100, 50, 0}};
        for (int c = 0; c < plans.length; c++) {
            double[] p = plans[c];
            double[] f = flocks[(int) p[10]];
            int years = c == 0 ? 30 : 10;
            CraneCohorts flock = CraneCohorts.marsh(new CraneCohorts.Settings(f[0], f[1], f[2], f[3], f[4], f[5],
                    years), 1);
            TranslocationPlan.Settings s = new TranslocationPlan.Settings((int) p[0], (int) p[1], (int) p[2],
                    (int) p[3], (int) p[4], p[5], p[6], (int) p[7], (int) p[8]);
            long seed = c == 0 ? 7 : 7 + 31L * c;
            TranslocationPlan plan = TranslocationPlan.of(flock, s, seed);
            out.add("case=trans" + c + " years=" + years + " seed=" + seed + " botRuns=" + (int) p[9] + " "
                    + pars(FairPar.translocation(plan, (int) p[9], 600 + c)));
        }
        Object[][] reeds = {
            {List.of(10.0, 25.0, 40.0, 55.0, 80.0, 110.0, 150.0), 6.0, 3.0, 8, 4, 4, 40, 4.0, 0.15, 150},
            {List.of(10.0, 40.0, 80.0, 150.0), 6.0, 3.0, 6, 3, 3, 25, 4.0, 0.15, 40}};
        for (int c = 0; c < reeds.length; c++) {
            Object[] q = reeds[c];
            @SuppressWarnings("unchecked")
            List<Double> reed = (List<Double>) q[0];
            ReedRelease.Settings s = new ReedRelease.Settings(ReedCeiling.Settings.DEFAULT, reed, (double) q[1],
                    (double) q[2], (int) q[3], (int) q[4], (int) q[5], (int) q[6], (double) q[7], (double) q[8],
                    (int) q[9]);
            long seed = 23 + 19L * c;
            int botRuns = c == 0 ? 120 : 60;
            out.add("case=reed" + c + " seed=" + seed + " botRuns=" + botRuns + " "
                    + pars(FairPar.reedRelease(ReedRelease.of(s, seed), botRuns, 700 + c)));
        }
        double[][] droughts = {{-0.02, 0.2, 30, 10, 10}, {0.03, 0.1, 40, 10, 50}};
        for (int c = 0; c < droughts.length; c++) {
            double[] d = droughts[c];
            out.add("case=drought" + c + " " + pars(FairPar.droughtOdds(DroughtOdds.of(new DroughtOdds.Settings(d[0],
                    d[1], (int) d[2], (int) d[3])), d[4], 90, 810 + c)));
        }
        out.add("case=spread0 " + pars(FairPar.craneSpread(CraneSpread.marsh(new CraneSpread.Settings(1.2, 0.8, 0.2,
                60, 30), 1), 3, 5, 70, 820)));
        out.add("case=cohorts0 " + pars(FairPar.cohorts(CraneCohorts.marsh(new CraneCohorts.Settings(0.6, 0.8, 0.9,
                0.95, 0.3, 1.2, 10), 1), 7, 80, 830)));
        out.add("case=ceiling0 " + pars(FairPar.reedCeiling(new ReedCeiling.Settings(0.8, 30, 3, 0.05, 0.3, 0.4,
                0.1), new double[] {6, 20, 45}, 3, 25, 9, 50, 840)));
        for (Map.Entry<String, FairPar.Pars> e : FairPar.marshTable().entrySet()) {
            out.add("table=" + e.getKey() + " " + pars(e.getValue()));
        }
        return out;
    }

    private static String pars(FairPar.Pars p) {
        return "runs=" + p.runs() + " bronze=" + p.bronze() + " silver=" + p.silver() + " gold=" + p.gold()
                + " perfect=" + p.perfect() + " bronzeHit=" + p.bronzeHit() + " silverHit=" + p.silverHit()
                + " goldHit=" + p.goldHit() + " median=" + p.median() + " separated=" + p.separated();
    }

    @Test
    void fairParMatchesCpp() throws IOException {
        check("marsh_fair_par_parity.txt", "G600 FairPar", MarshCoresParityTest::fairPar);
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
