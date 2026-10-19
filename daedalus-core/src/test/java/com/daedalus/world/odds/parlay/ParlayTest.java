// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.parlay;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.fishing.AnglerSkill;
import com.daedalus.world.fishing.CastSession;
import com.daedalus.world.fishing.Conditions;
import com.daedalus.world.fishing.FishSpecies;
import com.daedalus.world.fishing.FishTable;
import com.daedalus.world.fishing.FishingOdds;
import com.daedalus.world.fishing.Rarity;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;

class ParlayTest {

    private static FishTable pond() throws IOException {
        return FishTable.fromJson(Files.readString(Path.of("..", "data", "rpg", "prism-fish.json"), StandardCharsets.UTF_8));
    }

    private static ParlayTicket ticket(double p, double offered, String... legs) {
        return new ParlayTicket("D1-T1", 1, Conditions.STORM, List.of(legs), p, offered);
    }

    @Test
    void boardIsSeededPricedHonestlyAndCappedOnEdge() throws IOException {
        FishTable pond = pond();
        List<ParlayTicket> a = ParlayBoard.daily(pond, 77L, 3, Conditions.STORM, AnglerSkill.STEADY, 8, 3);
        List<ParlayTicket> b = ParlayBoard.daily(pond, 77L, 3, Conditions.STORM, AnglerSkill.STEADY, 8, 3);
        assertThat(a).hasSize(8);
        assertThat(a).extracting(ParlayTicket::toString).isEqualTo(b.stream().map(ParlayTicket::toString).toList());
        FishingOdds.Breakdown odds = FishingOdds.exact(pond, Conditions.STORM, AnglerSkill.STEADY);
        for (ParlayTicket t : a) {
            assertThat(t.legCount()).isBetween(1, 3);
            assertThat(t.day()).isEqualTo(3);
            assertThat(t.conditions()).isEqualTo(Conditions.STORM);
            assertThat(t.probability()).isGreaterThanOrEqualTo(ParlayBoard.MIN_PROBABILITY);
            double p = 1;
            for (String leg : t.legs()) {
                p *= odds.catchShare(leg);
            }
            assertThat(t.probability()).isCloseTo(p, within(1e-15));
            assertThat(t.houseEdge()).isBetween(-1e-12, ParlayBoard.HOUSE_EDGE + 1e-12);
            assertThat(t.offeredMultiplier()).isLessThanOrEqualTo(t.fairMultiplier() + 1e-9);
            assertThat(t.expectedProfit(10)).isLessThanOrEqualTo(1e-9);
        }
        assertThat(a.get(0).id()).isEqualTo("D3-T1");
        List<ParlayTicket> other = ParlayBoard.daily(pond, 77L, 4, Conditions.STORM, AnglerSkill.STEADY, 8, 3);
        assertThat(other.stream().map(ParlayTicket::legs).toList()).isNotEqualTo(a.stream().map(ParlayTicket::legs).toList());
    }

    @Test
    void longShotsAreNeverChalked() {
        FishTable impossible = new FishTable("x", List.of(FishSpecies.of("ghost", Rarity.LEGENDARY, 1, 0.01, 1)));
        assertThat(ParlayBoard.daily(impossible, 1, 0, Conditions.DAY, new AnglerSkill(1.0, 0), 3, 2)).isEmpty();
        FishTable sure = new FishTable("x", List.of(FishSpecies.of("dace", Rarity.COMMON, 1, 5, 1)));
        ParlayTicket t = ParlayBoard.daily(sure, 1, 0, Conditions.DAY, AnglerSkill.NOVICE, 1, 1).get(0);
        assertThat(t.offeredMultiplier()).isEqualTo(1.0);
        assertThat(t.probability()).isCloseTo(1.0, within(1e-9));
    }

    @Test
    void boardRejectsBadArguments() throws IOException {
        FishTable pond = pond();
        assertThatThrownBy(() -> ParlayBoard.daily(pond, 1, -1, Conditions.DAY, AnglerSkill.STEADY, 1, 1)).hasMessageContaining("day");
        assertThatThrownBy(() -> ParlayBoard.daily(pond, 1, 0, Conditions.DAY, AnglerSkill.STEADY, 0, 1)).hasMessageContaining("tickets");
        assertThatThrownBy(() -> ParlayBoard.daily(pond, 1, 0, Conditions.DAY, AnglerSkill.STEADY, 13, 1)).hasMessageContaining("tickets");
        assertThatThrownBy(() -> ParlayBoard.daily(pond, 1, 0, Conditions.DAY, AnglerSkill.STEADY, 1, 0)).hasMessageContaining("maxLegs");
        assertThatThrownBy(() -> ParlayBoard.daily(pond, 1, 0, Conditions.DAY, AnglerSkill.STEADY, 1, 5)).hasMessageContaining("maxLegs");
    }

    @Test
    void ticketWinsOnlyWhenEveryLegLandsInOrder() {
        ParlayTicket t = ticket(0.25, 3.8, "Reedling", "Pond Perch");
        assertThat(t.wins(List.of("Reedling", "Pond Perch", "x"))).isTrue();
        assertThat(t.wins(List.of("Pond Perch", "Reedling"))).isFalse();
        assertThat(t.wins(Arrays.asList("Reedling", null))).isFalse();
        assertThat(t.fairMultiplier()).isEqualTo(4.0);
        assertThat(t.houseEdge()).isCloseTo(0.05, within(1e-12));
        assertThat(t.payout(10)).isEqualTo(38);
        assertThat(t.expectedProfit(10)).isCloseTo(-0.5, within(1e-12));
        assertThat(t.toString()).isEqualTo("D1-T1 storm [Reedling, Pond Perch]: 1 in 4, pays 3.8x");
        List<String> copy = t.legs();
        copy.clear();
        assertThat(t.legCount()).isEqualTo(2);
        assertThatThrownBy(() -> t.wins(List.of("Reedling"))).hasMessageContaining("needs 2");
        assertThatThrownBy(() -> t.wins(null)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void ticketRejectsNonsense() {
        assertThatThrownBy(() -> new ParlayTicket(" ", 0, Conditions.DAY, List.of("a"), 0.5, 1.5)).hasMessageContaining("id");
        assertThatThrownBy(() -> new ParlayTicket(null, 0, Conditions.DAY, List.of("a"), 0.5, 1.5)).hasMessageContaining("id");
        assertThatThrownBy(() -> new ParlayTicket("t", 0, null, List.of("a"), 0.5, 1.5)).hasMessageContaining("conditions");
        assertThatThrownBy(() -> new ParlayTicket("t", 0, Conditions.DAY, List.of(), 0.5, 1.5)).hasMessageContaining("leg");
        assertThatThrownBy(() -> new ParlayTicket("t", 0, Conditions.DAY, null, 0.5, 1.5)).hasMessageContaining("leg");
        assertThatThrownBy(() -> new ParlayTicket("t", 0, Conditions.DAY, List.of("a"), 0, 1.5)).hasMessageContaining("probability");
        assertThatThrownBy(() -> new ParlayTicket("t", 0, Conditions.DAY, List.of("a"), 1.1, 1.5)).hasMessageContaining("probability");
        assertThatThrownBy(() -> new ParlayTicket("t", 0, Conditions.DAY, List.of("a"), 0.5, 0.9)).hasMessageContaining("multiplier");
        assertThatThrownBy(() -> new ParlayTicket("t", 0, Conditions.DAY, List.of("a"), 0.5, Double.POSITIVE_INFINITY))
                .hasMessageContaining("multiplier");
    }

    @Test
    void bookPaysEachTicketExactlyOnceAndTracksTheLedgerQuest() {
        ParlayBook book = new ParlayBook(100);
        ParlayTicket win = ticket(0.25, 3.8, "Reedling");
        ParlayTicket lose = new ParlayTicket("D1-T2", 1, Conditions.DAY, List.of("Prismscale Koi"), 0.01, 95);
        book.stake(win, 10);
        book.stake(lose, 20);
        assertThat(book.herbs()).isEqualTo(70);
        assertThat(book.atRisk()).isEqualTo(30);
        assertThat(book.status("D1-T1")).isEqualTo(ParlayBook.Status.OPEN);
        assertThat(OddsKeeper.ledger(book)).contains("Settle 3 more tickets");
        assertThat(book.settle("D1-T1", List.of("Reedling"))).isEqualTo(38);
        assertThat(book.herbs()).isEqualTo(108);
        assertThat(book.status("D1-T1")).isEqualTo(ParlayBook.Status.WON);
        assertThatThrownBy(() -> book.settle("D1-T1", List.of("Reedling"))).isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("already settled");
        assertThat(book.herbs()).isEqualTo(108);
        assertThat(book.settle("D1-T2", List.of(""))).isZero();
        assertThat(book.status("D1-T2")).isEqualTo(ParlayBook.Status.LOST);
        assertThat(book.atRisk()).isZero();
        assertThat(book.settled()).isEqualTo(2);
        assertThat(book.ledgerEarned()).isFalse();
        assertThat(OddsKeeper.ledger(book)).contains("Settle 1 more ticket,");
        ParlayTicket third = new ParlayTicket("D2-T1", 2, Conditions.DAY, List.of("Reedling"), 0.4, 2.4);
        book.stake(third, 5);
        book.settle("D2-T1", List.of("Pond Perch"));
        assertThat(book.ledgerEarned()).isTrue();
        assertThat(OddsKeeper.ledger(book)).contains("Storm Ledger");
    }

    @Test
    void bookSettlesFromRealCasts() throws IOException {
        FishTable pond = pond();
        List<CastSession> casts = new ArrayList<>();
        CastSession landed = new CastSession(pond, Conditions.DAY, 5, 0);
        landed.tick(landed.waitSeconds());
        landed.strike();
        CastSession early = new CastSession(pond, Conditions.DAY, 5, 1);
        early.strike();
        casts.add(landed);
        casts.add(early);
        String first = landed.fish().orElseThrow().name();
        ParlayBook book = new ParlayBook(10);
        book.stake(new ParlayTicket("A", 0, Conditions.DAY, List.of(first), 0.5, 1.9), 10);
        assertThat(book.settleCasts("A", casts)).isEqualTo(19);
        book.stake(new ParlayTicket("B", 0, Conditions.DAY, List.of(first, first), 0.25, 3.8), 10);
        assertThat(book.settleCasts("B", casts)).isZero();
    }

    @Test
    void bookRefusesBadStakes() {
        ParlayBook book = new ParlayBook(30);
        ParlayTicket t = ticket(0.5, 1.9, "Reedling");
        assertThatThrownBy(() -> book.stake(null, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> book.stake(t, 0)).hasMessageContaining("stake");
        assertThatThrownBy(() -> book.stake(t, ParlayBook.MAX_STAKE + 1)).hasMessageContaining("stake");
        assertThatThrownBy(() -> book.stake(t, 31)).isInstanceOf(IllegalStateException.class);
        book.stake(t, 30);
        assertThatThrownBy(() -> book.stake(t, 1)).isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> book.settle("nope", List.of())).hasMessageContaining("not staked");
        assertThatThrownBy(() -> book.status("nope")).hasMessageContaining("not staked");
        assertThatThrownBy(() -> new ParlayBook(-1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void keeperSpeaksPlainly() {
        ParlayTicket storm = ticket(0.0004, 2400, "Reedling", "Prismscale Koi");
        assertThat(OddsKeeper.pitch(storm)).startsWith("Storm's up").contains("Reedling, then Prismscale Koi: one in 2,500")
                .contains("I pay 2,400").contains("my cut is 4.0%");
        ParlayTicket calm = new ParlayTicket("C", 0, Conditions.DAY, List.of("Reedling"), 0.5, 2);
        assertThat(OddsKeeper.pitch(calm)).startsWith("Calm water today.").contains("my cut is 0.0%");
        assertThat(OddsKeeper.settle(calm, 4)).contains("4 storm herbs").contains("Ticket C is closed");
        assertThat(OddsKeeper.settle(calm, 0)).startsWith("Not this time");
    }
}
