// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.ark.HammockRows;
import com.daedalus.world.ark.SeedTrays;
import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.junit.jupiter.api.Test;

class ArkCabinetTest {

    private static <T extends ArkCabinetGame> T play(T g, String... moves) {
        for (String m : moves) {
            assertThat(g.play(m)).as("move %s", m).isTrue();
        }
        return g;
    }

    @Test
    void menuListsEveryGameAndRejectsUnknownOrDuplicate() {
        ArkCabinet cab = ArkCabinet.standard();
        assertThat(cab.slots()).extracting(ArkCabinet.Slot::id).containsExactly("chalk", "hammock", "seeds",
            "hardtack", "signal", "net", "cargo");
        assertThat(cab.menu()).contains("1) chalk").contains("4) hardtack").contains("7) cargo");
        assertThat(cab.arcadeDescription()).contains(ArkCabinet.QUEST_ID).contains("7 crew games");
        assertThatThrownBy(() -> cab.open("nope")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> cab.register("chalk", "x", "y", ChalkGridGame::new))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> cab.slots().clear()).isInstanceOf(UnsupportedOperationException.class);
        for (ArkCabinet.Slot s : cab.slots()) {
            ArkCabinetGame g = s.open();
            assertThat(g.id()).isEqualTo(s.id());
            assertThat(g.over()).isFalse();
            assertThat(g.toMove()).isEqualTo(1);
            assertThat(g.legalMoves()).isNotEmpty();
            assertThat(ArkCabinet.quest(g)).isFalse();
        }
    }

    @Test
    void autoplayMatchesEachPiecesPerfectPlayValue() {
        ArkCabinet cab = ArkCabinet.standard();
        ArkCabinetGame chalk = cab.open("chalk");
        ArkCabinet.autoplay(chalk);
        assertThat(chalk.winner()).isZero();
        int hv = new HammockRows(4, 4, 3).value(new int[16], 1);
        ArkCabinetGame hammock = cab.open("hammock");
        ArkCabinet.autoplay(hammock);
        assertThat(hammock.winner()).isEqualTo(hv > 0 ? 1 : hv < 0 ? 2 : 0);
        int sm = new SeedTrays().margin(SeedTrays.start(3, 3), 0);
        SeedTraysGame seeds = new SeedTraysGame();
        ArkCabinet.autoplay(seeds);
        assertThat(seeds.store(1) - seeds.store(2)).isEqualTo(sm);
        ArkCabinetGame bar = cab.open("hardtack");
        ArkCabinet.autoplay(bar);
        assertThat(bar.winner()).isEqualTo(1);
        assertThat(ArkCabinet.quest(bar)).isTrue();
    }

    @Test
    void chalkGridScriptedWinAndIllegalMoves() {
        ChalkGridGame g = new ChalkGridGame();
        assertThat(g.legalMoves()).hasSize(9);
        assertThat(g.play("0")).isFalse();
        assertThat(g.play("x")).isFalse();
        play(g, "1", "4", "2", "5");
        assertThat(g.play("1")).isFalse();
        play(g, "3");
        assertThat(g.over()).isTrue();
        assertThat(g.winner()).isEqualTo(1);
        assertThat(g.toMove()).isZero();
        assertThat(g.legalMoves()).isEmpty();
        assertThat(g.hint()).isEmpty();
        assertThat(g.render()).isEqualTo("XXX\nOO.\n...\n");
    }

    @Test
    void chalkGridHintBlocksALine() {
        ChalkGridGame g = play(new ChalkGridGame(), "1", "5", "2");
        assertThat(g.hint()).isEqualTo("3");
        ChalkGridGame full = play(new ChalkGridGame(), "1", "2", "3", "5", "4", "6", "8", "7", "9");
        assertThat(full.over()).isTrue();
        assertThat(full.winner()).isZero();
    }

    @Test
    void hammockRowsGravityAndVerticalWin() {
        HammockRowsGame g = new HammockRowsGame();
        assertThat(g.legalMoves()).containsExactly("1", "2", "3", "4");
        assertThat(g.play("5")).isFalse();
        play(g, "1", "2", "1", "2");
        assertThat(g.render()).isEqualTo("....\n....\nXO..\nXO..\n1234\n");
        play(g, "1");
        assertThat(g.winner()).isEqualTo(1);
        assertThat(g.over()).isTrue();
        assertThat(g.play("3")).isFalse();
    }

    @Test
    void hammockRowsFullColumnIsNotLegal() {
        HammockRowsGame g = play(new HammockRowsGame(), "1", "1", "1", "1");
        assertThat(g.legalMoves()).containsExactly("2", "3", "4");
        assertThat(g.play("1")).isFalse();
        assertThat(g.hint()).isIn(g.legalMoves());
    }

    @Test
    void seedTraysExtraTurnAndEndOfGame() {
        SeedTraysGame g = new SeedTraysGame();
        assertThat(g.legalMoves()).containsExactly("1", "2", "3");
        play(g, "1");
        assertThat(g.toMove()).isEqualTo(1);
        assertThat(g.store(1)).isEqualTo(1);
        assertThat(g.play("1")).isFalse();
        play(g, "2");
        assertThat(g.toMove()).isEqualTo(2);
        assertThat(g.render()).contains("\n");
        List<String> rest = ArkCabinet.autoplay(g);
        assertThat(rest).isNotEmpty();
        assertThat(g.over()).isTrue();
        assertThat(g.store(1) + g.store(2)).isEqualTo(18);
    }

    @Test
    void hardtackBarBitingTheCornerLoses() {
        HardtackBarGame g = new HardtackBarGame(2, 3);
        assertThat(g.legalMoves()).hasSize(6);
        assertThat(g.play("3,1")).isFalse();
        assertThat(g.play("garbage")).isFalse();
        play(g, "2,2");
        assertThat(g.render()).isEqualTo("*##\n#\n");
        play(g, "1,1");
        assertThat(g.over()).isTrue();
        assertThat(g.winner()).isEqualTo(1);
    }

    @Test
    void hardtackBarHintIsAWinningBite() {
        HardtackBarGame g = new HardtackBarGame(2, 2);
        assertThat(g.hint()).isEqualTo("2,2");
        play(g, g.hint());
        assertThat(g.hint()).isNotEqualTo("1,1");
        HardtackBarGame last = play(new HardtackBarGame(1, 2), "1,2");
        assertThat(last.hint()).isEqualTo("1,1");
    }

    @Test
    void demoRunsScriptedAndKeyboardSessions() throws IOException {
        ByteArrayOutputStream buf = new ByteArrayOutputStream();
        PrintStream out = new PrintStream(buf, true, StandardCharsets.UTF_8);
        ArkCabinetDemo.demo(ArkCabinet.standard(), out);
        String text = buf.toString(StandardCharsets.UTF_8);
        assertThat(text).contains("== The Chalk Grid ==").contains("== The Hardtack Bar ==").contains("result:");
        buf.reset();
        ArkCabinetDemo.play(ArkCabinet.standard(),
            new BufferedReader(new StringReader("hardtack\nhint\n9,9\n2,2\n2,1\n1,2\n1,3\n1,4\n1,5\n")), out);
        assertThat(buf.toString(StandardCharsets.UTF_8)).contains("Not a legal move.").contains("Cabinet plays");
    }
}
