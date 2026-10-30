// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.NetMending;
import org.junit.jupiter.api.Test;

class ArkCabinetMoreTest {

    private static <T extends ArkCabinetGame> T play(T g, String... moves) {
        for (String m : moves) {
            assertThat(g.play(m)).as("move %s", m).isTrue();
        }
        return g;
    }

    @Test
    void signalWebTopToBottomChainWins() {
        SignalWebGame g = new SignalWebGame();
        assertThat(g.legalMoves()).hasSize(9);
        assertThat(g.play("10")).isFalse();
        play(g, "1", "2", "4", "5");
        assertThat(g.play("4")).isFalse();
        play(g, "7");
        assertThat(g.over()).isTrue();
        assertThat(g.winner()).isEqualTo(1);
        assertThat(g.legalMoves()).isEmpty();
        assertThat(g.render()).isEqualTo("X O .\n X O .\n  X . .\n");
    }

    @Test
    void signalWebLeftToRightChainWinsForO() {
        SignalWebGame g = play(new SignalWebGame(), "1", "4", "2", "5", "7", "6");
        assertThat(g.winner()).isEqualTo(2);
        SignalWebGame fresh = new SignalWebGame();
        assertThat(fresh.hint()).isIn(fresh.legalMoves());
        assertThatThrownBy(() -> new SignalWebGame(0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void signalWebAutoplayFirstCrewWins() {
        SignalWebGame g = new SignalWebGame();
        ArkCabinet.autoplay(g);
        assertThat(g.winner()).isEqualTo(1);
    }

    @Test
    void netMendingClosingAMeshGivesAnotherTurn() {
        NetMendingGame g = new NetMendingGame(1, 1);
        assertThat(g.legalMoves()).containsExactly("1", "2", "3", "4");
        play(g, "1", "2", "3");
        assertThat(g.toMove()).isEqualTo(2);
        assertThat(g.play("3")).isFalse();
        play(g, "4");
        assertThat(g.over()).isTrue();
        assertThat(g.meshes(2)).isEqualTo(1);
        assertThat(g.winner()).isEqualTo(2);
        assertThat(g.render()).contains("+---+").contains("X 0 - O 1");
    }

    @Test
    void netMendingAutoplayMatchesPerfectMargin() {
        int m = new NetMending(2, 2).margin(new boolean[12]);
        NetMendingGame g = new NetMendingGame();
        ArkCabinet.autoplay(g);
        assertThat(g.meshes(1) - g.meshes(2)).isEqualTo(m);
        assertThat(g.meshes(1) + g.meshes(2)).isEqualTo(4);
        assertThat(g.hint()).isEmpty();
    }

    @Test
    void cargoShuffleScriptedSolve() {
        CargoShuffleGame g = new CargoShuffleGame();
        assertThat(g.fewestLeft()).isEqualTo(3);
        assertThat(g.play("A5")).isFalse();
        assertThat(g.play("Z1")).isFalse();
        play(g, "B4", "c4");
        assertThat(g.over()).isFalse();
        assertThat(g.legalMoves()).contains("A5");
        play(g, "A5");
        assertThat(g.over()).isTrue();
        assertThat(g.winner()).isEqualTo(1);
        assertThat(g.movesMade()).isEqualTo(3);
        assertThat(g.render()).contains("....AA>");
    }

    @Test
    void cargoShuffleAutoplayUsesShortestPlanAndRejectsBadLayouts() {
        CargoShuffleGame g = new CargoShuffleGame();
        assertThat(g.render()).startsWith("..B...|\n..B.C.|\nAAB.C.>\n");
        assertThat(ArkCabinet.autoplay(g)).hasSize(3);
        assertThat(g.over()).isTrue();
        assertThatThrownBy(() -> new CargoShuffleGame(6, new boolean[] {true, false}, new int[] {2, 3},
            new int[] {2, 0}, new int[] {0, 1})).isInstanceOf(IllegalArgumentException.class);
    }
}
