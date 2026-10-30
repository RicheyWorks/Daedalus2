// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;
import java.util.TreeSet;

/**
 * Kennel Isle pup growth stages (contest gap G65). A pup ages one day per day, but it only grows on care-days: a day
 * it was fed and watered (G37 {@link KennelBond.Care}). A bonded care-day (tonic or fetch) can trigger a seeded growth
 * spurt worth one extra care-day. Neglect stalls growth and costs bond. The {@link Stage} caps which commands the pup
 * can be trained on (G61 {@link KennelTraining}), on top of the bond tier. Pure and deterministic.
 *
 * <p>Quest "Growing Up" ({@link #growingUp}): raise a newborn to {@link Stage#JUVENILE} within {@link #QUEST_DAYS}
 * days with at most {@link #QUEST_NEGLECT_LIMIT} neglect days.
 */
public final class KennelGrowth {
    public static final int QUEST_DAYS = 14;
    public static final int QUEST_NEGLECT_LIMIT = 2;
    public static final int SPURT_PCT = 15;

    /** Growth stages, youngest first, with the care-days needed, model scale, stamina and trainable commands. */
    public enum Stage {
        NEWBORN(0, 0.35, 20, Set.of()),
        PUP(3, 0.55, 45, Set.of("come")),
        JUVENILE(10, 0.80, 75, Set.of("come", "stay", "fetch")),
        ADULT(21, 1.00, 100, Set.of("come", "stay", "fetch", "guard", "rescue")),
        ELDER(60, 0.95, 70, Set.of("come", "stay", "fetch", "guard"));

        private final int careDays;
        private final double scale;
        private final int stamina;
        private final Set<String> commands;

        Stage(int careDays, double scale, int stamina, Set<String> commands) {
            this.careDays = careDays;
            this.scale = scale;
            this.stamina = stamina;
            this.commands = commands;
        }

        public int careDays() {
            return careDays;
        }

        public double scale() {
            return scale;
        }

        public int stamina() {
            return stamina;
        }

        public Set<String> commands() {
            return Collections.unmodifiableSet(new TreeSet<>(commands));
        }

        public static Stage of(int careDays) {
            Stage s = NEWBORN;
            for (Stage x : values()) {
                if (careDays >= x.careDays) {
                    s = x;
                }
            }
            return s;
        }
    }

    public record Pup(String name, int ageDays, int careDays, int bond, int neglectDays) {
        public Pup {
            if (ageDays < 0 || careDays < 0 || bond < 0 || neglectDays < 0) {
                throw new IllegalArgumentException("bad pup");
            }
        }

        public static Pup newborn(String name, int bond) {
            return new Pup(name, 0, 0, bond, 0);
        }

        public Stage stage() {
            return Stage.of(careDays);
        }
    }

    public record Day(Pup after, boolean grew, boolean spurt, Stage stageBefore, Stage stageAfter) {
        public boolean stagedUp() {
            return stageAfter != stageBefore;
        }
    }

    public record QuestResult(boolean complete, int dayReached, List<Stage> trail, String failReason) {
        public QuestResult {
            trail = List.copyOf(trail);
        }
    }

    private KennelGrowth() {
    }

    /** One day with a seeded spurt roll. */
    public static Day day(Pup p, KennelBond.Care c, long seed) {
        return day(p, c, new SplittableRandom(seed).nextInt(100));
    }

    /** One day with an explicit spurt roll in [0, 100); a spurt happens on a bonded care-day when roll < SPURT_PCT. */
    static Day day(Pup p, KennelBond.Care c, int roll) {
        Stage before = p.stage();
        int bond = KennelBond.step(p.bond(), c, KennelBond.Rules.defaults());
        if (c.neglected()) {
            Pup n = new Pup(p.name(), p.ageDays() + 1, p.careDays(), bond, p.neglectDays() + 1);
            return new Day(n, false, false, before, before);
        }
        boolean bonded = c.tonic() || c.fetchCatches() > 0;
        boolean spurt = bonded && roll < SPURT_PCT;
        int care = p.careDays() + 1 + (spurt ? 1 : 0);
        Pup n = new Pup(p.name(), p.ageDays() + 1, care, bond, p.neglectDays());
        return new Day(n, true, spurt, before, n.stage());
    }

    /** G61 gate: the pup's stage and its G37 bond tier must both allow the command. */
    public static boolean canTrain(Pup p, String command) {
        KennelTraining.difficulty(command);
        return p.stage().commands().contains(command) && KennelBond.obeys(p.bond(), command);
    }

    /** G61 adapter: a drill that is refused while the pup is too young. */
    public static KennelTraining.Drill drill(Pup p, KennelTraining.Trainee t, String command, long seed) {
        if (!p.stage().commands().contains(command)) {
            KennelTraining.difficulty(command);
            return new KennelTraining.Drill(t, false, false, "too young");
        }
        return KennelTraining.drill(t, command, seed);
    }

    /** Quest "Growing Up": newborn to Juvenile within QUEST_DAYS, at most QUEST_NEGLECT_LIMIT neglect days. */
    public static QuestResult growingUp(Pup start, List<KennelBond.Care> days, long seed) {
        List<Stage> trail = new ArrayList<>();
        Pup p = start;
        trail.add(p.stage());
        SplittableRandom r = new SplittableRandom(seed);
        for (int d = 0; d < Math.min(days.size(), QUEST_DAYS); d++) {
            p = day(p, days.get(d), r.nextInt(100)).after();
            trail.add(p.stage());
            if (p.neglectDays() > QUEST_NEGLECT_LIMIT) {
                return new QuestResult(false, -1, trail, "too many neglect days");
            }
            if (p.stage().compareTo(Stage.JUVENILE) >= 0) {
                return new QuestResult(true, d + 1, trail, null);
            }
        }
        return new QuestResult(false, -1, trail, "not juvenile after " + QUEST_DAYS + " days");
    }
}