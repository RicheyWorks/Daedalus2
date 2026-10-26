// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ForgeCommissions.Commission;
import com.daedalus.world.forge.ForgeCommissions.Delivery;
import com.daedalus.world.forge.ForgeCommissions.Ledger;
import com.daedalus.world.forge.ForgeCommissions.MinTier;
import com.daedalus.world.forge.ForgeCommissions.Patron;
import com.daedalus.world.forge.ForgeCommissions.Verdict;
import com.daedalus.world.forge.ForgeGrades.Material;
import com.daedalus.world.forge.ForgeGrades.Weapon;
import com.daedalus.world.forge.TemperForge.Blank;
import com.daedalus.world.forge.TemperForge.Quench;
import com.daedalus.world.forge.TemperForge.Result;
import org.junit.jupiter.api.Test;

import java.util.EnumSet;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ForgeCommissionsTest {

    private static Commission order(Weapon w, Material m, MinTier t, int due, int price) {
        return new Commission(1, 0, Patron.BRANNOC, w, m, t, due, price);
    }

    @Test
    void theBoardIsSeededPerDay() {
        assertThat(ForgeCommissions.board(7)).isEqualTo(ForgeCommissions.board(7));
        assertThat(ForgeCommissions.board(7)).hasSize(ForgeCommissions.PER_DAY);
        assertThat(ForgeCommissions.board(7)).isNotEqualTo(ForgeCommissions.board(8));
        for (Commission c : ForgeCommissions.board(7)) {
            assertThat(c.day()).isEqualTo(7);
            assertThat(c.dueShifts()).isBetween(1, 3);
            assertThat(c.priceCoins()).isPositive();
        }
    }

    @Test
    void overManyDaysEveryPatronMetalAndTierTurnsUp() {
        Set<Patron> patrons = EnumSet.noneOf(Patron.class);
        Set<Material> metals = EnumSet.noneOf(Material.class);
        Set<MinTier> tiers = EnumSet.noneOf(MinTier.class);
        for (long day = 0; day < 60; day++) {
            for (Commission c : ForgeCommissions.board(day)) {
                patrons.add(c.patron());
                metals.add(c.material());
                tiers.add(c.minTier());
                assertThat(c.material()).isNotIn(Material.WOOD, Material.STONE, Material.OBSIDIAN);
            }
        }
        assertThat(patrons).containsExactlyInAnyOrder(Patron.values());
        assertThat(metals).containsExactlyInAnyOrder(Material.COPPER, Material.BRONZE, Material.IRON, Material.STEEL,
                Material.STARMETAL);
        assertThat(tiers).containsExactlyInAnyOrder(MinTier.values());
    }

    @Test
    void minimumTiersMatchForgeGradesTierNames() {
        for (MinTier t : MinTier.values()) {
            assertThat(ForgeGrades.tier(t.temper())).isEqualTo(t.name());
            assertThat(ForgeGrades.tier(t.temper() - 1)).isNotEqualTo(t.name());
        }
    }

    @Test
    void pricesFollowMetalTierAndRush() {
        assertThat(ForgeCommissions.tierFactorPct(MinTier.CRUDE)).isEqualTo(60);
        assertThat(ForgeCommissions.tierFactorPct(MinTier.MASTERWORK)).isEqualTo(250);
        for (long day = 0; day < 30; day++) {
            for (Commission c : ForgeCommissions.board(day)) {
                int base = switch (c.material()) {
                    case COPPER -> 12;
                    case BRONZE -> 18;
                    case IRON -> 26;
                    case STEEL -> 40;
                    default -> 90;
                };
                int expect = base * ForgeCommissions.tierFactorPct(c.minTier()) / 100 + (c.dueShifts() == 1 ? base / 4 : 0);
                assertThat(c.priceCoins()).isEqualTo(expect);
            }
        }
    }

    @Test
    void cleanWorkPaysInFullWithATipForExtraTemper() {
        Commission c = order(Weapon.SWORD, Material.STEEL, MinTier.STANDARD, 2, 40);
        Delivery d = ForgeCommissions.deliver(c, ForgeGrades.grade(Weapon.SWORD, Material.STEEL, 90), 2, 50);
        assertThat(d.verdict()).isEqualTo(Verdict.PAID);
        assertThat(d.coins()).isEqualTo(40);
        assertThat(d.tipCoins()).isEqualTo(40 * 40 * 100 / 10000);
        assertThat(d.regardDelta()).isEqualTo(5);
        assertThat(d.paid()).isTrue();
        assertThat(d.line()).isEqualTo("Rings true. That one goes on the ark.");
        Delivery exact = ForgeCommissions.deliver(c, ForgeGrades.grade(Weapon.SWORD, Material.STEEL, 50), 0, 50);
        assertThat(exact.tipCoins()).isZero();
    }

    @Test
    void lateWorkPaysHalfAndNoTip() {
        Commission c = order(Weapon.BLASTER, Material.IRON, MinTier.FINE, 1, 39);
        Delivery d = ForgeCommissions.deliver(c, ForgeGrades.grade(Weapon.BLASTER, Material.IRON, 100), 2, 90);
        assertThat(d.verdict()).isEqualTo(Verdict.PAID_LATE);
        assertThat(d.coins()).isEqualTo(19);
        assertThat(d.tipCoins()).isZero();
        assertThat(d.regardDelta()).isEqualTo(1);
        assertThat(d.paid()).isTrue();
    }

    @Test
    void wrongOrSoftWorkComesBack() {
        Commission c = order(Weapon.SWORD, Material.BRONZE, MinTier.FINE, 3, 27);
        Delivery w = ForgeCommissions.deliver(c, ForgeGrades.grade(Weapon.BLASTER, Material.BRONZE, 90), 1, 50);
        Delivery m = ForgeCommissions.deliver(c, ForgeGrades.grade(Weapon.SWORD, Material.IRON, 90), 1, 50);
        Delivery s = ForgeCommissions.deliver(c, ForgeGrades.grade(Weapon.SWORD, Material.BRONZE, 79), 1, 50);
        assertThat(List.of(w.verdict(), m.verdict(), s.verdict())).containsExactly(Verdict.WRONG_WEAPON,
                Verdict.WRONG_METAL, Verdict.UNDER_TEMPERED);
        for (Delivery d : List.of(w, m, s)) {
            assertThat(d.paid()).isFalse();
            assertThat(d.coins() + d.tipCoins()).isZero();
            assertThat(d.regardDelta()).isEqualTo(-3);
            assertThat(d.line()).startsWith("Drydock Master Brannoc Slagg: ");
        }
        assertThat(s.line()).endsWith("Take it back to the quench.");
        assertThatThrownBy(() -> ForgeCommissions.deliver(c, ForgeGrades.grade(Weapon.SWORD, Material.BRONZE, 90), -1, 50))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void regardRaisesTheTip() {
        Commission c = order(Weapon.SWORD, Material.STARMETAL, MinTier.STANDARD, 3, 90);
        var piece = ForgeGrades.grade(Weapon.SWORD, Material.STARMETAL, 100);
        int cold = ForgeCommissions.deliver(c, piece, 1, 0).tipCoins();
        int warm = ForgeCommissions.deliver(c, piece, 1, 100).tipCoins();
        assertThat(cold).isEqualTo(90 * 50 * 50 / 10000);
        assertThat(warm).isEqualTo(90 * 50 * 150 / 10000);
        assertThat(ForgeCommissions.deliver(c, piece, 1, 500).tipCoins()).isEqualTo(warm);
    }

    @Test
    void theLedgerBooksCoinsAndRegard() {
        Ledger l = new Ledger();
        Commission c = order(Weapon.SWORD, Material.COPPER, MinTier.CRUDE, 2, 7);
        assertThat(l.regard(Patron.BRANNOC)).isEqualTo(ForgeCommissions.START_REGARD);
        Delivery d = l.record(c, ForgeGrades.grade(Weapon.SWORD, Material.COPPER, 60), 1);
        assertThat(l.coins()).isEqualTo(d.coins() + d.tipCoins());
        assertThat(l.regard(Patron.BRANNOC)).isEqualTo(55);
        l.record(c, ForgeGrades.grade(Weapon.BLASTER, Material.COPPER, 60), 1);
        assertThat(l.regard(Patron.BRANNOC)).isEqualTo(52);
        assertThat(l.delivered()).isEqualTo(1);
        assertThat(l.regard(Patron.MIRA)).isEqualTo(50);
        for (int i = 0; i < 30; i++) {
            l.record(c, ForgeGrades.grade(Weapon.BLASTER, Material.COPPER, 60), 1);
        }
        assertThat(l.regard(Patron.BRANNOC)).isZero();
    }

    @Test
    void aMasterSmithAtTheAnvilFillsTheWholeBoard() {
        Ledger l = new Ledger();
        for (long day = 0; day < 10; day++) {
            for (Commission c : ForgeCommissions.board(day)) {
                Blank b = TemperForge.blank(c.material(), day * 10 + c.slot());
                Result r = TemperForge.judge(b, TemperForge.idealRun(b, Quench.DUAL));
                Delivery d = l.record(c, ForgeGrades.grade(c.weapon(), c.material(), r.temper()), c.dueShifts());
                assertThat(d.verdict()).as(c.toString() + " temper " + r.temper()).isEqualTo(Verdict.PAID);
            }
        }
        assertThat(l.delivered()).isEqualTo(30);
        assertThat(l.coins()).isPositive();
    }

    @Test
    void everyPatronHasThanksAndALateLine() {
        for (Patron p : Patron.values()) {
            assertThat(ForgeCommissions.thanks(p, false)).isNotBlank();
            assertThat(ForgeCommissions.thanks(p, true)).isNotBlank().isNotEqualTo(ForgeCommissions.thanks(p, false));
            assertThat(p.title()).isNotBlank();
        }
        assertThat(ForgeCommissions.complaint(Patron.MIRA, Verdict.WRONG_METAL)).isEqualTo(
                "Captain Mira Sootvane of Storm Anchorage: Wrong metal. Read the board.");
    }
}
