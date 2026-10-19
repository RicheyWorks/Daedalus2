// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.tournament;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.fishing.AnglerSkill;
import com.daedalus.world.fishing.Conditions;
import com.daedalus.world.fishing.FishSpecies;
import com.daedalus.world.fishing.FishTable;
import com.daedalus.world.fishing.Rarity;
import com.daedalus.world.odds.OddsRng;
import java.util.List;
import java.util.stream.IntStream;
import org.junit.jupiter.api.Test;

class SquallCupTest {

    private static final FishTable LANE = new FishTable("oddsreaper", List.of(
            FishSpecies.of("Gust Minnow", Rarity.COMMON, 60, 1.2, 2),
            FishSpecies.of("Squall Perch", Rarity.UNCOMMON, 30, 0.6, 6),
            FishSpecies.of("Ark Eel", Rarity.RARE, 10, 0.35, 20)));

    private static final Heat HEAT = new Heat(LANE, Conditions.STORM, 8);

    private static List<Angler> field(int n) {
        AnglerSkill[] skills = {AnglerSkill.OLD_HAND, AnglerSkill.STEADY, AnglerSkill.NOVICE};
        return IntStream.range(0, n)
                .mapToObj(i -> new Angler("A" + i, skills[Math.min(i, 2)])).toList();
    }

    @Test
    void seedOrderKeepsTopSeedsApart() {
        assertThat(Bracket.seedOrder(4)).containsExactly(0, 3, 1, 2);
        assertThat(Bracket.seedOrder(8)).containsExactly(0, 7, 3, 4, 1, 6, 2, 5);
    }

    @Test
    void byesGoToTopSeeds() {
        Bracket b = new Bracket(field(5));
        assertThat(b.rounds()).isEqualTo(3);
        assertThat(b.byes()).isEqualTo(3);
        assertThat(b.firstRound()).containsExactly(0, -1, 3, 4, 1, -1, 2, -1);
        assertThat(b.anglers()).hasSize(5);
    }

    @Test
    void playIsSeededAndShrinksEachRound() {
        Bracket b = new Bracket(field(6));
        List<List<Integer>> one = b.play(HEAT, new OddsRng(42));
        assertThat(one).isEqualTo(b.play(HEAT, new OddsRng(42)));
        assertThat(one).hasSize(3);
        assertThat(one.get(0)).hasSize(4);
        assertThat(one.get(2)).hasSize(1);
        assertThat(one.get(1)).containsAnyElementsOf(one.get(2));
    }

    @Test
    void expectedScoreMatchesSimulation() {
        double exact = HEAT.expectedScore(AnglerSkill.STEADY);
        long sum = 0;
        int n = 20_000;
        for (int t = 0; t < n; t++) {
            sum += HEAT.score(AnglerSkill.STEADY, OddsRng.forTrial(7, t));
        }
        assertThat(sum / (double) n).isCloseTo(exact, within(exact * 0.03));
        assertThat(HEAT.casts()).isEqualTo(8);
    }

    @Test
    void oddsBoardSumsToOneAndFavoursTheOldHand() {
        CupOdds board = CupOdds.simulate(new Bracket(field(4)), HEAT, 99, 4000);
        double total = 0;
        for (int i = 0; i < 4; i++) {
            total += board.chance(i);
        }
        assertThat(total).isCloseTo(1.0, within(1e-9));
        assertThat(board.favourite()).isZero();
        assertThat(board.trials()).isEqualTo(4000);
        assertThat(board.fairOdds(0)).isCloseTo(4000.0 / board.titles(0), within(1e-9));
        assertThat(board.chance(0)).isGreaterThan(board.chance(3));
        assertThat(CupOdds.simulate(new Bracket(field(4)), HEAT, 99, 4000).titles(1)).isEqualTo(board.titles(1));
    }

    @Test
    void neverWinningAnglerHasInfiniteOdds() {
        Heat oneCast = new Heat(LANE, Conditions.DAY, 1);
        List<Angler> lopsided = List.of(new Angler("Pro", new AnglerSkill(0.01, 0.0)),
                new Angler("Asleep", new AnglerSkill(9.0, 0.0)));
        CupOdds board = CupOdds.simulate(new Bracket(lopsided), oneCast, 1, 50);
        assertThat(board.titles(0)).isEqualTo(50);
        assertThat(board.fairOdds(1)).isInfinite();
    }

    @Test
    void questPaysLongshotPurseOnlyToChampion() {
        SquallCupQuest q = new SquallCupQuest(field(4), HEAT, 5, 2000);
        assertThat(q.stage()).isEqualTo(SquallCupQuest.Stage.ODDS_POSTED);
        assertThat(q.keeperLine()).contains("Chalk says");
        int purse = q.purse();
        assertThat(purse).isBetween(SquallCupQuest.BASE_PURSE,
                SquallCupQuest.BASE_PURSE * SquallCupQuest.MAX_MULTIPLIER);
        int won = q.fish(12345);
        if (q.stage() == SquallCupQuest.Stage.CHAMPION) {
            assertThat(won).isEqualTo(purse);
            assertThat(q.roundsWon()).isEqualTo(2);
            assertThat(q.keeperLine()).contains("Champion");
        } else {
            assertThat(won).isZero();
            assertThat(q.keeperLine()).contains("squall took");
        }
        assertThat(q.board().trials()).isEqualTo(2000);
        assertThatThrownBy(() -> q.fish(1)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void championAndKnockoutBothReachable() {
        List<Angler> pro = List.of(new Angler("Player", new AnglerSkill(0.01, 0.0)),
                new Angler("Asleep", new AnglerSkill(9.0, 0.0)));
        SquallCupQuest win = new SquallCupQuest(pro, HEAT, 1, 10);
        assertThat(win.purse()).isEqualTo(SquallCupQuest.BASE_PURSE);
        assertThat(win.fish(3)).isEqualTo(SquallCupQuest.BASE_PURSE);
        assertThat(win.stage()).isEqualTo(SquallCupQuest.Stage.CHAMPION);

        List<Angler> hopeless = List.of(new Angler("Player", new AnglerSkill(9.0, 0.0)),
                new Angler("Pro", new AnglerSkill(0.01, 0.0)));
        SquallCupQuest lose = new SquallCupQuest(hopeless, HEAT, 1, 10);
        assertThat(lose.purse()).isEqualTo(SquallCupQuest.BASE_PURSE * SquallCupQuest.MAX_MULTIPLIER);
        assertThat(lose.fish(3)).isZero();
        assertThat(lose.stage()).isEqualTo(SquallCupQuest.Stage.KNOCKED_OUT);
        assertThat(lose.keeperLine()).contains("squall took");
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new Angler(" ", AnglerSkill.NOVICE)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Heat(LANE, Conditions.DAY, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Bracket(field(1))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CupOdds.simulate(new Bracket(field(2)), HEAT, 1, 0))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
