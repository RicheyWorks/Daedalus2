// SPDX-License-Identifier: MIT
package com.daedalus.world.labyrinth;

import com.daedalus.world.audio.Rng;
import java.util.Locale;
import java.util.Optional;

/**
 * LAB07 Twin Doors: the Labyrinth archive opens "through reasoning", not force.
 *
 * <p>Two doors, one safe. Two bell guards, one always tells the truth and one always lies. The
 * guards answer yes/no with a LOW or HIGH bell. At difficulty 0 the low bell means yes; at
 * difficulty 1 the seed hides which bell means yes, so the player must find a question whose
 * answer is safe to read either way. The player gets ONE question to ONE guard, then picks a door.
 *
 * <p>{@link #deduce} is the proof engine: it enumerates every world consistent with what the player
 * knows and returns a door only when all of them agree. Tests use it to prove the puzzle is always
 * solvable with the embedded question, at both difficulties, for every seed.
 *
 * <p>Ear rules: guard bells are D3 (146.832 Hz) and A3 (219.999 Hz), a soft fifth, at gain 0.5.
 * Pure data; the C++ core {@code DaedalusTwinDoorsCore.h} matches it (fixture
 * {@code docs/contracts/twin-doors-v1}).
 */
public final class TwinDoors {
    /** Low guard bell, D3. */
    public static final double LOW_HZ = 146.832;
    /** High guard bell, A3. */
    public static final double HIGH_HZ = 219.999;
    /** Bell gain for both tones. */
    public static final double GAIN = 0.5;
    /** Door / guard indices. */
    public static final int LEFT = 0;
    /** Door / guard indices. */
    public static final int RIGHT = 1;
    private static final long SALT = 0x5457_4431L; // "TWD1"

    /** The questions a player can put to a guard, each about one door. */
    public enum Question {
        /** "Is door d safe?" */
        DIRECT,
        /** "Would the other guard say door d is safe?" */
        OTHER_GUARD,
        /** "If I asked you whether door d is safe, would you ring the low bell?" */
        EMBEDDED,
        /** "Are you the truth guard?" (says nothing about doors). */
        SELF
    }

    /** A guard bell. */
    public enum Tone {
        /** Low bell. */
        LOW,
        /** High bell. */
        HIGH;

        /** Bell frequency in Hz. */
        public double hz() {
            return this == LOW ? LOW_HZ : HIGH_HZ;
        }
    }

    private final long seed;
    private final int difficulty;
    private final int safeDoor;
    private final int liar;
    private final boolean lowMeansYes;

    private TwinDoors(long seed, int difficulty, int safeDoor, int liar, boolean lowMeansYes) {
        this.seed = seed;
        this.difficulty = difficulty;
        this.safeDoor = safeDoor;
        this.liar = liar;
        this.lowMeansYes = lowMeansYes;
    }

    /** Seeded riddle; difficulty 0 (low bell = yes) or 1 (bell meaning hidden). */
    public static TwinDoors seeded(long seed, int difficulty) {
        if (difficulty < 0 || difficulty > 1) {
            throw new IllegalArgumentException("difficulty 0-1");
        }
        Rng rng = new Rng(seed ^ SALT);
        int safe = (int) Long.remainderUnsigned(rng.nextLong(), 2);
        int liarGuard = (int) Long.remainderUnsigned(rng.nextLong(), 2);
        boolean lowYes = difficulty == 0 || Long.remainderUnsigned(rng.nextLong(), 2) == 1;
        return new TwinDoors(seed, difficulty, safe, liarGuard, lowYes);
    }

    /** Which door is safe (host only; never show the player). */
    public int safeDoor() {
        return safeDoor;
    }

    /** Which guard lies (host only). */
    public int liar() {
        return liar;
    }

    /** Whether the low bell means yes (always true at difficulty 0). */
    public boolean lowMeansYes() {
        return lowMeansYes;
    }

    /** The difficulty this riddle was built with. */
    public int difficulty() {
        return difficulty;
    }

    /** The bell guard {@code guard} rings for {@code question} about {@code door}. */
    public Tone answer(int guard, Question question, int door) {
        checkSide(guard, "guard");
        checkSide(door, "door");
        return tone(safeDoor, liar, lowMeansYes, guard, question, door);
    }

    /** True if {@code door} is the safe door. */
    public boolean choose(int door) {
        checkSide(door, "door");
        return door == safeDoor;
    }

    /**
     * What a careful player can conclude after hearing {@code heard} from {@code guard}: the safe door
     * if every world consistent with the answer (liar position, and bell meaning at difficulty 1)
     * agrees on it, else empty.
     */
    public static Optional<Integer> deduce(int difficulty, int guard, Question question, int door, Tone heard) {
        Integer agreed = null;
        for (int safe = 0; safe < 2; safe++) {
            for (int liarGuard = 0; liarGuard < 2; liarGuard++) {
                for (int y = 0; y < 2; y++) {
                    boolean lowYes = y == 1;
                    if (difficulty == 0 && !lowYes) {
                        continue;
                    }
                    if (tone(safe, liarGuard, lowYes, guard, question, door) != heard) {
                        continue;
                    }
                    if (agreed == null) {
                        agreed = safe;
                    } else if (agreed != safe) {
                        return Optional.empty();
                    }
                }
            }
        }
        return Optional.ofNullable(agreed);
    }

    /** One player session: exactly one question, then exactly one door. */
    public static final class Session {
        private final TwinDoors doors;
        private Tone heard;
        private Boolean result;

        /** Starts a session on a riddle. */
        public Session(TwinDoors doors) {
            this.doors = doors;
        }

        /** Asks the single allowed question. */
        public Tone ask(int guard, Question question, int door) {
            if (heard != null) {
                throw new IllegalStateException("only one question");
            }
            heard = doors.answer(guard, question, door);
            return heard;
        }

        /** Picks a door; true opens the archive. Allowed once, after the question. */
        public boolean choose(int door) {
            if (heard == null) {
                throw new IllegalStateException("ask first");
            }
            if (result != null) {
                throw new IllegalStateException("already chosen");
            }
            result = doors.choose(door);
            return result;
        }
    }

    /** TWD 1 text form used by the C++ parity fixture. */
    public String toWire() {
        StringBuilder sb = new StringBuilder("TWD 1\n");
        sb.append(String.format(Locale.ROOT, "doors %d %d %d %d %d%n", seed, difficulty, safeDoor, liar,
                lowMeansYes ? 1 : 0));
        for (Question q : Question.values()) {
            for (int g = 0; g < 2; g++) {
                for (int d = 0; d < 2; d++) {
                    Tone t = answer(g, q, d);
                    Optional<Integer> k = deduce(difficulty, g, q, d, t);
                    sb.append(String.format(Locale.ROOT, "ask %d %s %d %s %s%n", g, q.name(), d, t.name(),
                            k.map(String::valueOf).orElse("-")));
                }
            }
        }
        return sb.append("end\n").toString().replace(System.lineSeparator(), "\n");
    }

    private static Tone tone(int safe, int liarGuard, boolean lowYes, int guard, Question q, int door) {
        boolean lies = guard == liarGuard;
        boolean doorSafe = safe == door;
        boolean saysYes = switch (q) {
            case DIRECT -> doorSafe ^ lies;
            case OTHER_GUARD -> (doorSafe ^ !lies) ^ lies; // the other guard lies iff this one does not
            case EMBEDDED -> ((doorSafe ^ lies) == lowYes) ^ lies;
            case SELF -> true; // truth guard: "yes"; liar denies being the liar: "yes"
        };
        return saysYes == lowYes ? Tone.LOW : Tone.HIGH;
    }

    private static void checkSide(int v, String what) {
        if (v != LEFT && v != RIGHT) {
            throw new IllegalArgumentException(what + " must be 0 or 1");
        }
    }
}
