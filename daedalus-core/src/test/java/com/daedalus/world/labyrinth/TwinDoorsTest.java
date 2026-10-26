// SPDX-License-Identifier: MIT
package com.daedalus.world.labyrinth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.labyrinth.TwinDoors.Question;
import com.daedalus.world.labyrinth.TwinDoors.Session;
import com.daedalus.world.labyrinth.TwinDoors.Tone;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.Test;

class TwinDoorsTest {
    static final long[] SEEDS = {1L, 42L, -7L, 0x5EED_CAFEL, Long.MIN_VALUE};

    static String fixtureText() {
        StringBuilder sb = new StringBuilder();
        for (long s : SEEDS) {
            for (int d = 0; d <= 1; d++) {
                sb.append(TwinDoors.seeded(s, d).toWire());
            }
        }
        return sb.toString();
    }

    @Test void fixtureMatchesAndLocaleDoesNotChangeIt() throws Exception {
        Path fixture = Path.of("..", "docs", "contracts", "twin-doors-v1", "riddles.twd");
        Locale old = Locale.getDefault();
        String actual;
        try {
            Locale.setDefault(Locale.GERMANY);
            actual = fixtureText();
        } finally {
            Locale.setDefault(old);
        }
        if (!Files.exists(fixture) || !Files.readString(fixture).equals(actual)) {
            Files.createDirectories(Path.of("target"));
            Files.writeString(Path.of("target", "riddles-actual.twd"), actual);
        }
        assertThat(actual).isEqualTo(Files.readString(fixture));
    }

    @Test void embeddedQuestionAlwaysSolvesAtBothDifficulties() {
        for (long s = -1000; s < 1000; s++) {
            for (int d = 0; d <= 1; d++) {
                TwinDoors t = TwinDoors.seeded(s, d);
                for (int g = 0; g < 2; g++) {
                    for (int door = 0; door < 2; door++) {
                        Tone heard = t.answer(g, Question.EMBEDDED, door);
                        assertThat(TwinDoors.deduce(d, g, Question.EMBEDDED, door, heard)).contains(t.safeDoor());
                        assertThat(heard == Tone.LOW).isEqualTo(door == t.safeDoor());
                    }
                }
            }
        }
    }

    @Test void otherGuardSolvesOnlyWhenBellMeaningIsKnown() {
        for (long s = 0; s < 200; s++) {
            TwinDoors easy = TwinDoors.seeded(s, 0);
            Tone heard = easy.answer(RIGHT, Question.OTHER_GUARD, LEFT);
            assertThat(TwinDoors.deduce(0, RIGHT, Question.OTHER_GUARD, LEFT, heard)).contains(easy.safeDoor());
            TwinDoors hard = TwinDoors.seeded(s, 1);
            heard = hard.answer(RIGHT, Question.OTHER_GUARD, LEFT);
            assertThat(TwinDoors.deduce(1, RIGHT, Question.OTHER_GUARD, LEFT, heard)).isEmpty();
        }
    }

    @Test void directAndSelfQuestionsNeverSolve() {
        for (Tone t : Tone.values()) {
            for (int d = 0; d <= 1; d++) {
                for (int g = 0; g < 2; g++) {
                    assertThat(TwinDoors.deduce(d, g, Question.DIRECT, LEFT, t)).isEmpty();
                    assertThat(TwinDoors.deduce(d, g, Question.SELF, RIGHT, t)).isEmpty();
                }
            }
        }
        TwinDoors t = TwinDoors.seeded(5, 1);
        Tone yes = t.lowMeansYes() ? Tone.LOW : Tone.HIGH;
        assertThat(t.answer(0, Question.SELF, 0)).isEqualTo(yes);
        assertThat(t.answer(1, Question.SELF, 0)).isEqualTo(yes);
    }

    @Test void seedsCoverEveryWorldAndEarRules() {
        Set<String> worlds = new HashSet<>();
        for (long s = 0; s < 400; s++) {
            TwinDoors t = TwinDoors.seeded(s, 1);
            worlds.add(t.safeDoor() + "/" + t.liar() + "/" + t.lowMeansYes());
            assertThat(TwinDoors.seeded(s, 0).lowMeansYes()).isTrue();
            assertThat(TwinDoors.seeded(s, 1).toWire()).isEqualTo(t.toWire());
        }
        assertThat(worlds).hasSize(8);
        assertThat(Tone.LOW.hz()).isLessThan(Tone.HIGH.hz());
        assertThat(Tone.HIGH.hz()).isLessThan(360.0);
        assertThat(TwinDoors.GAIN).isLessThanOrEqualTo(0.6);
    }

    @Test void sessionAllowsOneQuestionThenOneDoor() {
        TwinDoors t = TwinDoors.seeded(42, 1);
        Session s = new Session(t);
        assertThatThrownBy(() -> s.choose(0)).isInstanceOf(IllegalStateException.class);
        Tone heard = s.ask(0, Question.EMBEDDED, LEFT);
        assertThatThrownBy(() -> s.ask(1, Question.DIRECT, LEFT)).isInstanceOf(IllegalStateException.class);
        int pick = heard == Tone.LOW ? LEFT : RIGHT;
        assertThat(s.choose(pick)).isTrue();
        assertThatThrownBy(() -> s.choose(pick)).isInstanceOf(IllegalStateException.class);
        assertThat(t.choose(1 - pick)).isFalse();
        assertThat(t.difficulty()).isEqualTo(1);
        assertThat(Optional.of(t.safeDoor())).contains(pick);
    }

    @Test void rejectsBadInput() {
        TwinDoors t = TwinDoors.seeded(1, 0);
        assertThatThrownBy(() -> TwinDoors.seeded(1, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> TwinDoors.seeded(1, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> t.answer(2, Question.DIRECT, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> t.answer(0, Question.DIRECT, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> t.choose(3)).isInstanceOf(IllegalArgumentException.class);
    }

    private static final int LEFT = TwinDoors.LEFT;
    private static final int RIGHT = TwinDoors.RIGHT;
}
