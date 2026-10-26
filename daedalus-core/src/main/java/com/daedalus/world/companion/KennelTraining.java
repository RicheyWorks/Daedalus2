// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * Kennel Isle pup training (contest gap G61). The G37 {@link KennelBond} tiers say which commands a pet will take;
 * training is how it learns them. Each cue drill succeeds with odds {@code clamp(40 + bond / 2 - difficulty, 5, 95)}
 * percent (seeded). Three successes in a row teach the command and add {@link #LEARN_BONUS} bond; a miss resets the
 * streak. A command the pet's tier doesn't unlock can't be drilled yet. Pure and deterministic.
 *
 * <p>Quest "First Words" ({@link #firstWords}): teach a pup "come" and "stay" within {@link #QUEST_SESSIONS} sessions of
 * {@link #DRILLS_PER_SESSION} drills.
 */
public final class KennelTraining {
    public static final int STREAK_TO_LEARN = 3;
    public static final int LEARN_BONUS = 2;
    public static final int QUEST_SESSIONS = 5;
    public static final int DRILLS_PER_SESSION = 4;
    private static final Map<String, Integer> DIFFICULTY = Map.of("come", 0, "stay", 10, "fetch", 20, "guard", 35,
        "rescue", 50);

    public record Trainee(String name, int bond, Map<String, Integer> streak, Set<String> learned) {
        public Trainee {
            streak = Collections.unmodifiableMap(new TreeMap<>(streak));
            learned = Collections.unmodifiableSet(new TreeSet<>(learned));
        }

        public static Trainee fresh(String name, int bond) {
            return new Trainee(name, bond, Map.of(), Set.of());
        }
    }

    public record Drill(Trainee after, boolean success, boolean learnedNow, String blockedReason) { }

    public record QuestResult(boolean complete, int sessionsUsed, Trainee after, String failReason) { }

    private KennelTraining() {
    }

    public static int difficulty(String command) {
        Integer d = DIFFICULTY.get(command);
        if (d == null) {
            throw new IllegalArgumentException("unknown command " + command);
        }
        return d;
    }

    public static int successPct(int bond, String command) {
        return Math.max(5, Math.min(95, 40 + bond / 2 - difficulty(command)));
    }

    /** One drill with a seeded roll. */
    public static Drill drill(Trainee t, String command, long seed) {
        return drill(t, command, new SplittableRandom(seed).nextDouble() * 100);
    }

    /** One drill with an explicit roll in [0, 100); success when the roll is under the odds. */
    static Drill drill(Trainee t, String command, double roll) {
        difficulty(command);
        if (t.learned().contains(command)) {
            return new Drill(t, false, false, "already learned");
        }
        if (!KennelBond.obeys(t.bond(), command)) {
            return new Drill(t, false, false, "bond too low");
        }
        boolean ok = roll < successPct(t.bond(), command);
        Map<String, Integer> streak = new TreeMap<>(t.streak());
        Set<String> learned = new TreeSet<>(t.learned());
        int bond = t.bond();
        boolean learnedNow = false;
        if (ok) {
            int s = streak.merge(command, 1, Integer::sum);
            if (s >= STREAK_TO_LEARN) {
                streak.remove(command);
                learned.add(command);
                bond = Math.min(100, bond + LEARN_BONUS);
                learnedNow = true;
            }
        } else {
            streak.remove(command);
        }
        return new Drill(new Trainee(t.name(), bond, streak, learned), ok, learnedNow, null);
    }

    /** Quest "First Words": each drill works on the first of come/stay not yet learned. */
    public static QuestResult firstWords(Trainee pup, long seed) {
        List<String> words = List.of("come", "stay");
        if (!KennelBond.obeys(pup.bond(), "stay")) {
            return new QuestResult(false, 0, pup, "bond too low: raise it to Loyal first");
        }
        Trainee t = pup;
        SplittableRandom r = new SplittableRandom(seed);
        for (int s = 1; s <= QUEST_SESSIONS; s++) {
            for (int d = 0; d < DRILLS_PER_SESSION; d++) {
                String next = null;
                for (String w : words) {
                    if (!t.learned().contains(w)) {
                        next = w;
                        break;
                    }
                }
                if (next == null) {
                    return new QuestResult(true, s, t, null);
                }
                t = drill(t, next, r.nextDouble() * 100).after();
            }
            if (t.learned().containsAll(words)) {
                return new QuestResult(true, s, t, null);
            }
        }
        return new QuestResult(false, QUEST_SESSIONS, t, "not learned in " + QUEST_SESSIONS + " sessions");
    }
}