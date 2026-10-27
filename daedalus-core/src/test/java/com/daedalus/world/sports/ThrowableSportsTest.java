// SPDX-License-Identifier: MIT

package com.daedalus.world.sports;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.sports.ThrowableSports.Player;
import com.daedalus.world.sports.ThrowableSports.Swing;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class ThrowableSportsTest {
    private static final Player KID = new Player("kid", 0.5, false);
    private static final Player DOG = new Player("corso", 0.5, true);
    private static ThrowableSports g;

    @BeforeAll
    static void load() throws Exception {
        Path p = Path.of("..", "data", "sports", "throwables-v1.json");
        g = ThrowableSports.load(Files.exists(p) ? p : Path.of("data", "sports", "throwables-v1.json"));
    }

    @Test
    void catalogCoversPropsIncludingCaseMissedBalls() {
        assertThat(g.balls()).hasSize(16).containsKeys("Prop_Sport_Basketball", "Prop_Sport_Volleyball",
            "Prop_Sport_Dodgeball_Red", "Prop_Sport_Frisbee", "Prop_Sport_Softball");
        assertThat(g.balls()).doesNotContainKeys("Prop_Sport_Baseball_Bat", "Prop_Sport_Basketball_Hoop");
        assertThatThrownBy(() -> g.ball("Prop_Sport_Trophy")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void catchChanceFallsWithRangeAndDifficulty() {
        var frisbee = g.ball("Prop_Sport_Frisbee");
        var beach = g.ball("Prop_Sport_Beach_Ball");
        assertThat(g.catchChance(KID, beach, 5)).isGreaterThan(g.catchChance(KID, frisbee, 5));
        assertThat(g.catchChance(KID, beach, 5)).isGreaterThan(g.catchChance(KID, beach, 20));
        assertThat(g.catchChance(KID, beach, 31)).isZero();
        assertThat(g.catchChance(KID, beach, -1)).isZero();
    }

    @Test
    void petsGetFetchBonusOnlyOnFetchBalls() {
        assertThat(g.catchChance(DOG, g.ball("Prop_Sport_Frisbee"), 10))
            .isCloseTo(g.catchChance(KID, g.ball("Prop_Sport_Frisbee"), 10) + 0.15, org.assertj.core.data.Offset.offset(1e-9));
        assertThat(g.catchChance(DOG, g.ball("Prop_Sport_Football"), 10))
            .isEqualTo(g.catchChance(KID, g.ball("Prop_Sport_Football"), 10));
    }

    @Test
    void catchStreakBonusScoring() {
        Player pro = new Player("pro", 1.0, true);
        var r = g.playCatch(pro, "Prop_Sport_Beach_Ball", Collections.nCopies(9, 1.0), 4);
        assertThat(r.caught()).isEqualTo(9);
        assertThat(r.bestStreak()).isEqualTo(9);
        assertThat(r.score()).isEqualTo(9 + 3);
    }

    @Test
    void catchIsDeterministicAndRateMatchesChance() {
        List<Double> t = Collections.nCopies(20_000, 10.0);
        var a = g.playCatch(KID, "Prop_Sport_Tennis_Ball", t, 77);
        assertThat(a).isEqualTo(g.playCatch(KID, "Prop_Sport_Tennis_Ball", t, 77));
        double p = g.catchChance(KID, g.ball("Prop_Sport_Tennis_Ball"), 10);
        assertThat(a.caught() / 20_000.0).isBetween(p - 0.02, p + 0.02);
    }

    @Test
    void hoopsValuesAndRange() {
        assertThat(g.shotValue(6.74)).isEqualTo(2);
        assertThat(g.shotValue(6.75)).isEqualTo(3);
        assertThat(g.shotChance(KID, 1)).isGreaterThan(g.shotChance(KID, 8));
        assertThat(g.shotChance(KID, 12.1)).isZero();
        Player pro = new Player("pro", 1.0, false);
        int pts = g.playHoops(pro, "Prop_Sport_Basketball", Collections.nCopies(1000, 0.0), 1);
        assertThat(pts % 2).isZero();
        assertThat(pts / 2 / 1000.0).isBetween(0.82, 0.88);
    }

    @Test
    void wrongBallForGameRejected() {
        assertThatThrownBy(() -> g.playHoops(KID, "Prop_Sport_Frisbee", List.of(1.0), 0))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> g.playInning("Prop_Sport_Basketball", List.of(0)))
            .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void swingTimingWindows() {
        assertThat(g.swing(0)).isEqualTo(Swing.HOME_RUN);
        assertThat(g.swing(-25)).isEqualTo(Swing.HOME_RUN);
        assertThat(g.swing(-40)).isEqualTo(Swing.DOUBLE);
        assertThat(g.swing(40)).isEqualTo(Swing.SINGLE);
        assertThat(g.swing(100)).isEqualTo(Swing.FOUL);
        assertThat(g.swing(200)).isEqualTo(Swing.STRIKE);
        assertThat(g.swing(null)).isEqualTo(Swing.STRIKE);
    }

    @Test
    void swingWindowsCoverIntegerLimitsAndExactBoundaries() {
        int[] offsets = {Integer.MIN_VALUE, Integer.MIN_VALUE + 1, -111, -110, -61, -60, -26, -25,
            0, 25, 26, 60, 61, 110, 111, Integer.MAX_VALUE - 1, Integer.MAX_VALUE};
        Swing[] expected = {Swing.STRIKE, Swing.STRIKE, Swing.STRIKE, Swing.FOUL, Swing.FOUL, Swing.DOUBLE,
            Swing.DOUBLE, Swing.HOME_RUN, Swing.HOME_RUN, Swing.HOME_RUN, Swing.SINGLE, Swing.SINGLE, Swing.FOUL,
            Swing.FOUL, Swing.STRIKE, Swing.STRIKE, Swing.STRIKE};
        for (int i = 0; i < offsets.length; i++) {
            assertThat(g.swing(offsets[i])).as("swing offset %d", offsets[i]).isEqualTo(expected[i]);
        }
        assertThat(g.swing(null)).isEqualTo(Swing.STRIKE);
    }

    @Test
    void extremeMissesFinishAnInningWithoutAwardingHits() {
        List<Integer> swings = new ArrayList<>(Collections.nCopies(9, Integer.MIN_VALUE));
        swings.add(0); // This perfect swing is never pitched after three outs.
        for (String prop : List.of("Prop_Sport_Baseball", "Prop_Sport_Softball")) {
            assertThat(g.playInning(prop, swings)).as(prop).isEqualTo(new ThrowableSports.Inning(0, 3, 0, 9));
        }
    }

    @Test
    void inningScoresRunnersAndEndsAtThreeOuts() {
        // single, single, double (scores 1 from 2nd... runners on 1st+2nd -> 2nd runner scores, 1st to 3rd), HR (3 runs)
        List<Integer> s = new ArrayList<>(Arrays.asList(40, 40, -40, 0));
        s.addAll(Collections.nCopies(9, 500)); // 9 strikes = 3 outs
        s.add(0); // never pitched
        var in = g.playInning("Prop_Sport_Softball", s);
        assertThat(in.hits()).isEqualTo(4);
        assertThat(in.runs()).isEqualTo(1 + 3);
        assertThat(in.outs()).isEqualTo(3);
        assertThat(in.pitches()).isEqualTo(13);
    }

    @Test
    void foulsCannotStrikeOut() {
        var in = g.playInning("Prop_Sport_Baseball", Collections.nCopies(50, 100));
        assertThat(in.outs()).isZero();
        assertThat(in.pitches()).isEqualTo(50);
    }

    @Test
    void basesLoadedGrandSlam() {
        boolean[] b = {true, true, true};
        assertThat(ThrowableSports.advance(b, 4)).isEqualTo(4);
        assertThat(b).containsExactly(false, false, false);
    }

    @Test
    void rejectsBadData() {
        assertThatThrownBy(() -> ThrowableSports.parse("{\"version\":2}")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Player("x", 1.5, false)).isInstanceOf(IllegalArgumentException.class);
    }
}
