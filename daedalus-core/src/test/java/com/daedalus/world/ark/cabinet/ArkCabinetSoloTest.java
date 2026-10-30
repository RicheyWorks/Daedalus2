// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.FerryWatch;
import com.daedalus.world.ark.FourMasts;
import com.daedalus.world.ark.SignalCube;
import org.junit.jupiter.api.Test;

class ArkCabinetSoloTest {

    private static <T extends ArkCabinetGame> T play(T g, String... moves) {
        for (String m : moves) {
            assertThat(g.play(m)).as("move %s", m).isTrue();
        }
        return g;
    }

    @Test
    void holdBlocksSlidesAndRejectsBlockedMoves() {
        HoldBlocksGame g = new HoldBlocksGame();
        assertThat(g.render()).isEqualTo("AAB.\nAAB.\nCC..\n...D\n");
        assertThat(g.play("AR")).isFalse();
        assertThat(g.play("ZZ")).isFalse();
        assertThat(g.legalMoves()).contains("BR", "DU");
        play(g, "br");
        assertThat(g.render()).startsWith("AA.B\n");
        assertThat(g.movesMade()).isEqualTo(1);
    }

    @Test
    void holdBlocksAutoplayFollowsShortestPlan() {
        HoldBlocksGame g = new HoldBlocksGame();
        int fewest = g.fewestLeft();
        assertThat(fewest).isPositive();
        assertThat(ArkCabinet.autoplay(g)).hasSize(fewest);
        assertThat(g.over()).isTrue();
        assertThat(g.winner()).isEqualTo(1);
        assertThat(g.render()).endsWith("AA\n");
    }

    @Test
    void ferryWatchUnsafeLoadsAreRefused() {
        FerryWatchGame g = new FerryWatchGame();
        assertThat(g.legalMoves()).containsExactlyInAnyOrder("0,1", "0,2", "1,1");
        assertThat(g.play("2,0")).isFalse();
        assertThat(g.play("3,0")).isFalse();
        play(g, "1,1");
        assertThat(g.render()).contains("near: CCRR").contains("ark:  CR [ferry]");
        assertThat(g.legalMoves()).contains("1,0");
    }

    @Test
    void ferryWatchMidGameHintSolvesInFewestCrossings() {
        FerryWatchGame g = play(new FerryWatchGame(), "0,2", "0,1");
        assertThat(ArkCabinet.autoplay(g).size() + 2).isEqualTo(FerryWatch.fewest(3, 3, 2));
        assertThat(g.over()).isTrue();
        assertThat(g.checked()).isTrue();
        assertThat(g.crossings()).isEqualTo(11);
        assertThatThrownBy(() -> new FerryWatchGame(1, 1, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void signalCubeTurnsAndOptimalHint() {
        SignalCubeGame g = new SignalCubeGame("R U");
        assertThat(g.distance()).isEqualTo(2);
        assertThat(g.play("X")).isFalse();
        play(g, "U'");
        assertThat(g.distance()).isEqualTo(1);
        assertThat(g.hint()).isEqualTo("R'");
        play(g, "R'");
        assertThat(g.over()).isTrue();
        assertThat(g.render()).contains("solved");
        assertThat(g.legalMoves()).isEmpty();
    }

    @Test
    void signalCubeAutoplayMatchesDistance() {
        SignalCubeGame g = new SignalCubeGame();
        int d = SignalCube.distance(SignalCube.apply(SignalCube.solvedState(), SignalCubeGame.STARTER), false);
        assertThat(g.legalMoves()).hasSize(9);
        assertThat(ArkCabinet.autoplay(g)).hasSize(d);
        assertThat(g.winner()).isEqualTo(1);
    }

    @Test
    void fourMastsBiggerOnSmallerIsRefused() {
        FourMastsGame g = new FourMastsGame(3, 3);
        assertThat(g.legalMoves()).containsExactly("1,2", "1,3");
        play(g, "1,3");
        assertThat(g.play("1,3")).isFalse();
        assertThat(g.play("2,1")).isFalse();
        assertThat(g.render()).isEqualTo("1 | 3 2\n2 |\n3 | 1\n");
        assertThatThrownBy(() -> new FourMastsGame(12, 4)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void fourMastsHintSolvesInFewestFromStartAndMidGame() {
        FourMastsGame g = new FourMastsGame();
        assertThat(ArkCabinet.autoplay(g)).hasSize(FourMasts.fewest(4, 4));
        assertThat(g.checked()).isTrue();
        FourMastsGame h = play(new FourMastsGame(3, 3), "1,2");
        ArkCabinet.autoplay(h);
        assertThat(h.over()).isTrue();
        assertThat(h.checked()).isTrue();
    }

    @Test
    void deckCrawlerStepsBackAndBudget() {
        DeckCrawlerGame g = new DeckCrawlerGame();
        assertThat(g.play("back")).isFalse();
        play(g, "10");
        assertThat(g.steps()).isEqualTo(10);
        int painted = g.painted();
        play(g, "1", "back");
        assertThat(g.painted()).isEqualTo(painted);
        assertThat(g.play("7")).isFalse();
        ArkCabinet.autoplay(g);
        assertThat(g.steps()).isEqualTo(300);
        assertThat(g.over()).isTrue();
        assertThat(g.render()).contains("steps 300");
    }

    @Test
    void deckCrawlerStopsAtTheDeckEdge() {
        DeckCrawlerGame g = new DeckCrawlerGame("RL", 3, 1000);
        play(g, "100");
        assertThat(g.over()).isTrue();
        assertThat(g.steps()).isLessThan(100);
    }

    @Test
    void bigBoardsWinOrBlockOnePly() {
        ChalkGridGame chalk = play(new ChalkGridGame(4, 4, 3), "1", "5", "2");
        assertThat(chalk.hint()).isEqualTo("3");
        HammockRowsGame rack = play(new HammockRowsGame(7, 6, 4), "1", "2", "1", "2", "1");
        assertThat(rack.hint()).isEqualTo("1");
        HammockRowsGame win = play(new HammockRowsGame(7, 6, 4), "1", "2", "1", "2", "1", "3");
        assertThat(win.hint()).isEqualTo("1");
        SignalWebGame web = play(new SignalWebGame(4), "1", "2", "5", "3", "9");
        assertThat(web.hint()).isEqualTo("13");
    }
}
