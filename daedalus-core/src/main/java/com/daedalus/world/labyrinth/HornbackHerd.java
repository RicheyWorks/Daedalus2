// SPDX-License-Identifier: MIT

package com.daedalus.world.labyrinth;

import com.daedalus.world.battlefield.BattlefieldEcology;
import com.daedalus.world.companion.TroughBrew;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.SplittableRandom;

/**
 * LAB06 Calm the Hornbacks: a seeded, deterministic herd simulation in which water and space turn a stampede into a
 * guided passage.
 *
 * <p>The rules, in order of importance:
 * <ol>
 *   <li><b>Water calms.</b> A stampeding hornback stays stampeding until it drinks. It smells the next trough on the
 *       route within {@link Settings#lureCm} and veers to it. Drinking at a trough drops its
 *       stress by {@link Settings#drinkCalm}. Each trough has a limited number of drinks ({@link WaterSource}), so a
 *       Kennel {@link TroughBrew} can be used directly.</li>
 *   <li><b>Space keeps it calm.</b> Every neighbour inside {@link Settings#personalSpaceCm} beyond
 *       {@link Settings#crowdLimit} adds stress each step. A calm herd that bunches up stampedes again. Calm animals
 *       steer apart; stampeding animals do not. A calm animal with room around it settles by
 *       {@link Settings#spaceCalm} per step.</li>
 *   <li><b>Panic spreads, fire terrifies.</b> A stampeding neighbour adds stress, and so does a burning cell within
 *       {@link Settings#fireFearCm}. Animals steer away from fire, and one that walks into it is lost.</li>
 *   <li><b>The ground matters.</b> The {@link Terrain} is usually a {@link BattlefieldEcology} field. Dense cover slows
 *       the herd: speed is multiplied by {@code 1 - 0.5 * cover}.</li>
 * </ol>
 * Calm animals walk the player's trough route in order, then head for the exit. Stampeding animals charge toward the
 * exit with a seeded jitter. The passage is GUIDED when at least 80% of the herd arrives calm and none burn.
 *
 * <p>Pure {@code java.*}: no Unreal, no I/O. The host owns the actors, the trough props and persistence.
 */
public final class HornbackHerd {

    /** What the herd walks on. {@link #of(BattlefieldEcology)} adapts the battlefield ecology. */
    public interface Terrain {
        /** Cover 0..1 at a world point (cm). */
        double coverAt(double x, double y);

        /** True if the cell at a world point is burning. */
        boolean burningAt(double x, double y);

        /** True if the point is on the map. An animal that leaves the map is lost. */
        boolean inside(double x, double y);
    }

    /** One drink from a trough at game time {@code nowSec}. Returns false when it is empty or flat. */
    @FunctionalInterface
    public interface WaterSource {
        boolean drink(long nowSec);
    }

    /** A trough the player placed: a world point (cm) and its water. */
    public record Trough(double x, double y, WaterSource water) {
        public Trough {
            if (!Double.isFinite(x) || !Double.isFinite(y) || water == null) {
                throw new IllegalArgumentException("trough needs a finite point and a water source");
            }
        }
    }

    /** Tuning. {@link #DEFAULT} is the authored LAB06 feel. */
    public record Settings(double personalSpaceCm, int crowdLimit, double crowdStress, double panicSpread,
            double fireFearCm, double fireStress, double drinkCalm, double drinkRadiusCm, double lureCm, double calmSpeedCmS,
            double stampedeSpeedCmS, double stampedeAt, double spaceCalm, double exitRadiusCm, double startStress) {
        public static final Settings DEFAULT =
                new Settings(160, 2, 0.006, 0.004, 400, 0.08, 0.6, 220, 700, 150, 500, 0.7, 0.004, 350, 0.9);

        public Settings {
            if (!(personalSpaceCm > 0) || crowdLimit < 0 || !(drinkRadiusCm > 0) || !(calmSpeedCmS > 0)
                    || lureCm < 0 || !(stampedeSpeedCmS > 0) || !(stampedeAt > 0 && stampedeAt <= 1) || !(exitRadiusCm > 0)
                    || !(startStress >= 0 && startStress <= 1) || crowdStress < 0 || panicSpread < 0 || fireFearCm < 0
                    || fireStress < 0 || drinkCalm < 0 || spaceCalm < 0) {
                throw new IllegalArgumentException("invalid hornback settings");
            }
        }
    }

    public enum Outcome { GUIDED, STAMPEDE, TIMEOUT }

    /**
     * What happened. {@code drinks} counts successful drinks, {@code stampedeSteps} counts steps in which at least half of
     * the herd was stampeding, and {@code peakStress} is the highest mean stress seen.
     */
    public record Report(Outcome outcome, int herd, int arrived, int calmArrived, int burned, int lost, int drinks,
            int stampedeSteps, int steps, double peakStress) {}

    /** Simulation step in seconds: four steps per game second, so a charging animal cannot jump past a trough. */
    public static final double STEP_S = 0.25;

    public static final int MAX_HERD = 64;

    private HornbackHerd() {}

    /** The battlefield ecology as hornback terrain: cover from vegetation, fire from burning cells, the grid as bounds. */
    public static Terrain of(BattlefieldEcology e) {
        double w = e.width() * e.cellCm();
        double h = e.height() * e.cellCm();
        return new Terrain() {
            @Override public double coverAt(double x, double y) { return e.coverAt(x, y); }
            @Override public boolean burningAt(double x, double y) { return e.burningAt(x, y); }
            @Override public boolean inside(double x, double y) {
                return x >= e.originX() && y >= e.originY() && x < e.originX() + w && y < e.originY() + h;
            }
        };
    }

    /** A Kennel trough brew as water: each hornback drink spends one of its drinks. */
    public static WaterSource of(TroughBrew brew) {
        return brew::drink;
    }

    /** Plain water with a fixed number of drinks. */
    public static WaterSource water(int drinks) {
        if (drinks < 0) {
            throw new IllegalArgumentException("drinks must be >= 0");
        }
        int[] left = {drinks};
        return now -> left[0] > 0 && left[0]-- > 0;
    }

    /**
     * Runs the passage. The herd starts bunched within 300 cm of the start, already stampeding at
     * {@link Settings#startStress}.
     *
     * @param troughs the player's route, walked in list order
     * @param maxSeconds game seconds before TIMEOUT
     */
    public static Report run(long seed, int herd, double startX, double startY, double exitX, double exitY,
            List<Trough> troughs, Terrain terrain, Settings s, int maxSeconds) {
        if (herd < 1 || herd > MAX_HERD || maxSeconds < 1 || maxSeconds > 3600 || terrain == null || s == null) {
            throw new IllegalArgumentException("herd 1.." + MAX_HERD + ", maxSeconds 1..3600, terrain and settings required");
        }
        List<Trough> route = Collections.unmodifiableList(new ArrayList<>(troughs));
        SplittableRandom rng = new SplittableRandom(seed);
        double[] x = new double[herd], y = new double[herd], stress = new double[herd], jitter = new double[herd];
        int[] next = new int[herd];
        int[] state = new int[herd]; // 0 moving, 1 arrived calm, 2 arrived stampeding, 3 burned, 4 lost
        for (int i = 0; i < herd; i++) {
            double a = rng.nextDouble() * 2 * Math.PI, r = 300 * Math.sqrt(rng.nextDouble());
            x[i] = startX + r * Math.cos(a);
            y[i] = startY + r * Math.sin(a);
            stress[i] = s.startStress();
            jitter[i] = (rng.nextDouble() - 0.5) * (Math.PI / 3);
        }
        int drinks = 0, stampedeSteps = 0, steps = 0;
        double peak = 0;
        double ps2 = s.personalSpaceCm() * s.personalSpaceCm();
        int total = (int) Math.round(maxSeconds / STEP_S);
        for (; steps < total; steps++) {
            long now = (long) Math.floor(steps * STEP_S);
            double[] nx = x.clone(), ny = y.clone(), ns = stress.clone();
            int moving = 0, stampeding = 0;
            double sum = 0;
            for (int i = 0; i < herd; i++) {
                if (state[i] != 0) {
                    continue;
                }
                moving++;
                boolean wild = stress[i] >= s.stampedeAt();
                int crowd = 0, wildNear = 0;
                double sepX = 0, sepY = 0;
                for (int j = 0; j < herd; j++) {
                    if (j == i || state[j] != 0) {
                        continue;
                    }
                    double dx = x[i] - x[j], dy = y[i] - y[j], d2 = dx * dx + dy * dy;
                    if (d2 < ps2) {
                        crowd++;
                        if (stress[j] >= s.stampedeAt()) {
                            wildNear++;
                        }
                        double d = Math.max(1, Math.sqrt(d2));
                        sepX += dx / d;
                        sepY += dy / d;
                    }
                }
                double fearX = 0, fearY = 0;
                boolean fire = false;
                if (s.fireFearCm() > 0) {
                    for (int k = 0; k < 16; k++) {
                        double a = k * Math.PI / 8, rr = (k % 2 == 0 ? 0.5 : 1.0) * s.fireFearCm();
                        double fx = x[i] + rr * Math.cos(a), fy = y[i] + rr * Math.sin(a);
                        if (terrain.inside(fx, fy) && terrain.burningAt(fx, fy)) {
                            fire = true;
                            fearX -= Math.cos(a);
                            fearY -= Math.sin(a);
                        }
                    }
                }
                double st = stress[i] + s.crowdStress() * Math.max(0, crowd - s.crowdLimit()) + s.panicSpread() * wildNear
                        + (fire ? s.fireStress() : 0);
                if (!wild && crowd <= s.crowdLimit() && !fire) {
                    st -= s.spaceCalm(); // room to breathe settles a calm animal further
                }
                // Water: drink at the next trough on the route (one try per trough per animal).
                if (next[i] < route.size()) {
                    Trough t = route.get(next[i]);
                    if (Math.hypot(t.x() - x[i], t.y() - y[i]) <= s.drinkRadiusCm()) {
                        if (t.water().drink(now)) {
                            drinks++;
                            st -= s.drinkCalm();
                        }
                        next[i]++;
                    }
                }
                while (next[i] < route.size()) {
                    Trough t = route.get(next[i]);
                    boolean passed = Math.hypot(exitX - x[i], exitY - y[i]) + s.lureCm() < Math.hypot(exitX - t.x(), exitY - t.y());
                    if (!passed) {
                        break;
                    }
                    next[i]++; // ran past it: that water is behind this animal now
                }
                ns[i] = Math.max(0, Math.min(1, st));
                double tx, ty;
                Trough lure = next[i] < route.size() ? route.get(next[i]) : null;
                double lureD = lure == null ? Double.MAX_VALUE : Math.hypot(lure.x() - x[i], lure.y() - y[i]);
                if (wild && lure != null && lureD <= s.lureCm()) {
                    // Even a stampeding hornback smells water: it veers to the trough.
                    tx = (lure.x() - x[i]) / Math.max(1, lureD);
                    ty = (lure.y() - y[i]) / Math.max(1, lureD);
                    stampeding++;
                } else if (wild) {
                    double a = Math.atan2(exitY - y[i], exitX - x[i]) + jitter[i];
                    tx = Math.cos(a);
                    ty = Math.sin(a);
                    stampeding++;
                } else {
                    double gx = next[i] < route.size() ? route.get(next[i]).x() : exitX;
                    double gy = next[i] < route.size() ? route.get(next[i]).y() : exitY;
                    double d = Math.max(1, Math.hypot(gx - x[i], gy - y[i]));
                    tx = (gx - x[i]) / d + 0.8 * sepX;
                    ty = (gy - y[i]) / d + 0.8 * sepY;
                }
                tx += 2.0 * fearX;
                ty += 2.0 * fearY;
                double n = Math.hypot(tx, ty);
                if (n > 1e-9) {
                    double v = (wild ? s.stampedeSpeedCmS() : s.calmSpeedCmS())
                            * (1 - 0.5 * Math.max(0, Math.min(1, terrain.coverAt(x[i], y[i])))) * STEP_S;
                    nx[i] = x[i] + v * tx / n;
                    ny[i] = y[i] + v * ty / n;
                }
                sum += ns[i];
            }
            x = nx;
            y = ny;
            stress = ns;
            for (int i = 0; i < herd; i++) {
                if (state[i] != 0) {
                    continue;
                }
                if (!terrain.inside(x[i], y[i])) {
                    state[i] = 4;
                } else if (terrain.burningAt(x[i], y[i])) {
                    state[i] = 3;
                } else if (Math.hypot(exitX - x[i], exitY - y[i]) <= s.exitRadiusCm()) {
                    state[i] = stress[i] < s.stampedeAt() ? 1 : 2;
                }
            }
            if (moving > 0) {
                peak = Math.max(peak, sum / moving);
                if (stampeding * 2 >= moving) {
                    stampedeSteps++;
                }
            } else {
                break;
            }
        }
        int calm = 0, wildArr = 0, burned = 0, lost = 0, still = 0;
        for (int st : state) {
            switch (st) {
                case 1 -> calm++;
                case 2 -> wildArr++;
                case 3 -> burned++;
                case 4 -> lost++;
                default -> still++;
            }
        }
        Outcome o = calm * 10 >= herd * 8 && burned == 0 ? Outcome.GUIDED
                : still > 0 && stampedeSteps == 0 ? Outcome.TIMEOUT : Outcome.STAMPEDE;
        return new Report(o, herd, calm + wildArr, calm, burned, lost, drinks, stampedeSteps, steps, peak);
    }
}