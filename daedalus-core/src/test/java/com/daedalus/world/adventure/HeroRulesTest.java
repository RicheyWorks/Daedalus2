// SPDX-License-Identifier: MIT

package com.daedalus.world.adventure;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The hero rules (ADR-037): high and low decide every exchange; experience is spent on the level the
 * player chooses and resets to zero; a fall costs unspent experience; each level does what it says.
 */
class HeroRulesTest {

    @Test
    void highAndLowDecideEveryExchange() {
        assertThat(Duel.thrust(Height.HIGH, FoeKind.BLIGHT_SLIME, Height.HIGH)).isEqualTo(Duel.Thrust.HIT);
        assertThat(Duel.thrust(Height.LOW, FoeKind.BLIGHT_SLIME, Height.HIGH)).isEqualTo(Duel.Thrust.HIT);
        assertThat(Duel.thrust(Height.HIGH, FoeKind.SHARDBACK, Height.LOW)).as("its shell guards high").isEqualTo(Duel.Thrust.GUARDED);
        assertThat(Duel.thrust(Height.LOW, FoeKind.SHARDBACK, Height.LOW)).isEqualTo(Duel.Thrust.HIT);
        assertThat(Duel.thrust(Height.LOW, FoeKind.DUST_WISP, Height.LOW)).as("too high to reach crouching").isEqualTo(Duel.Thrust.OUT_OF_REACH);
        assertThat(Duel.thrust(Height.HIGH, FoeKind.DUST_WISP, Height.LOW)).isEqualTo(Duel.Thrust.HIT);
        // The stone knight: wherever its shield is, thrust at the other height; it strikes where it is not guarding.
        for (Height shield : Height.values()) {
            assertThat(Duel.thrust(shield, FoeKind.STONE_KNIGHT, shield)).isEqualTo(Duel.Thrust.GUARDED);
            assertThat(Duel.thrust(shield.other(), FoeKind.STONE_KNIGHT, shield)).isEqualTo(Duel.Thrust.HIT);
            assertThat(Duel.strikeOf(FoeKind.STONE_KNIGHT, shield)).isEqualTo(shield.other());
        }
        assertThat(Duel.blocks(Height.HIGH, Duel.strikeOf(FoeKind.SHARDBACK, Height.HIGH))).as("stand to block a bite").isTrue();
        assertThat(Duel.blocks(Height.HIGH, Duel.strikeOf(FoeKind.BLIGHT_SLIME, Height.HIGH))).as("crouch for a slime").isFalse();
    }

    @Test
    void experienceIsSpentOnTheLevelYouChooseAndResets() {
        Hero h = Hero.fresh("link");
        assertThat(h.canRaise(HeroRules.Stat.LIFE)).isFalse();
        h = h.beat(FoeKind.STONE_KNIGHT);
        assertThat(h.exp()).isEqualTo(50);
        assertThat(h.canRaise(HeroRules.Stat.LIFE)).as("Life 2 costs 50").isTrue();
        assertThat(h.canRaise(HeroRules.Stat.MAGIC)).as("Magic 2 costs 100").isFalse();
        assertThat(h.raise(HeroRules.Stat.MAGIC)).as("not enough: unchanged").isEqualTo(h);
        Hero up = h.raise(HeroRules.Stat.LIFE);
        assertThat(up.life()).isEqualTo(2);
        assertThat(up.exp()).as("back to zero").isZero();
        assertThat(up.beaten()).isEqualTo(1);
        Hero twice = up.beat(FoeKind.STONE_KNIGHT).beat(FoeKind.STONE_KNIGHT).beat(FoeKind.SHARDBACK);
        assertThat(twice.exp()).isEqualTo(105);
        assertThat(twice.fall().exp()).as("a fall costs unspent experience").isZero();
        assertThat(twice.fall().life()).as("levels stay").isEqualTo(2);
        assertThat(twice.raise(HeroRules.Stat.MAGIC).magic()).isEqualTo(2);
    }

    @Test
    void theCostsFollowTheTableAndTheLevelsDoWhatTheySay() {
        assertThat(HeroRules.cost(HeroRules.Stat.LIFE, 1)).isEqualTo(50);
        assertThat(HeroRules.cost(HeroRules.Stat.MAGIC, 1)).isEqualTo(100);
        assertThat(HeroRules.cost(HeroRules.Stat.ATTACK, 1)).isEqualTo(200);
        assertThat(HeroRules.cost(HeroRules.Stat.ATTACK, 7)).isEqualTo(8000);
        assertThat(HeroRules.cost(HeroRules.Stat.ATTACK, 8)).as("no top: half again past the cost table").isEqualTo(12000);
        assertThat(HeroRules.cost(HeroRules.Stat.LIFE, 9)).isEqualTo(9000);
        assertThat(HeroRules.cost(HeroRules.Stat.ATTACK, 500)).as("never overflows").isEqualTo(HeroRules.COST_CEILING);
        for (int l = 1; l < 40; l++) {
            for (HeroRules.Stat s : HeroRules.Stat.values()) {
                int next = HeroRules.cost(s, l + 1);
                assertThat(next == HeroRules.COST_CEILING || next > HeroRules.cost(s, l)).isTrue();
            }
            assertThat(HeroRules.damage(l + 1)).isGreaterThan(HeroRules.damage(l));
            assertThat(HeroRules.maxLife(l + 1)).isEqualTo(HeroRules.maxLife(l) + 2);
            assertThat(HeroRules.maxMagic(l + 1)).isGreaterThan(HeroRules.maxMagic(l));
            assertThat(HeroRules.hurt(FoeKind.STONE_KNIGHT, l + 1)).isLessThanOrEqualTo(HeroRules.hurt(FoeKind.STONE_KNIGHT, l));
        }
        assertThat(HeroRules.maxLife(1)).as("three hearts").isEqualTo(6);
        assertThat(HeroRules.damage(1)).isEqualTo(1);
        assertThat(FoeKind.STONE_KNIGHT.life() / HeroRules.damage(1)).as("six honest hits to a knight at Attack 1").isEqualTo(6);
        assertThat(HeroRules.hurt(FoeKind.BLIGHT_SLIME, 8)).as("never free").isEqualTo(1);
        assertThatThrownBy(() -> new Hero("x", -1, 1, 1, 1, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Hero("x", 0, 0, 1, 1, 0)).isInstanceOf(IllegalArgumentException.class);
        Hero grinder = new Hero("x", 20_000, 30, 1, 1, 0);
        assertThat(grinder.attack()).as("no max level").isEqualTo(30);
        assertThat(new Hero("y", 12_000, 8, 1, 1, 0).raise(HeroRules.Stat.ATTACK).attack()).isEqualTo(9);
    }
}
