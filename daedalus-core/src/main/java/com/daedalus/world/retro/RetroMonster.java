// SPDX-License-Identifier: MIT

package com.daedalus.world.retro;

import java.util.EnumSet;
import java.util.Set;

/**
 * The realm's bestiary (ADR-052): the shattered world's foes (ADR-037) in 8-bit form, their palette swaps, and the
 * realm's own. Original creatures and names.
 *
 * <p>{@code shape} picks one of the C++ core's drawings; {@code body} and {@code accent} recolour it, the way the
 * classics stretched one sprite into a family. A monster drops {@code drop} one time in {@code dropOneIn}.
 */
public enum RetroMonster {
    BLIGHT_SLIME("BLIGHT SLIME", 0, 0x58D840, 0x188C10, 6, 5, 2, 3, 2, 2, Rarity.COMMON, EnumSet.of(Trait.POISON), RetroItem.HERB, 8),
    BOG_SLIME("BOG SLIME", 0, 0x8C34C8, 0x4C1478, 14, 9, 5, 4, 6, 6, Rarity.UNCOMMON, EnumSet.of(Trait.POISON, Trait.CALL), RetroItem.ANTIDOTE, 6),
    LUCKY_DRIP("LUCKY DRIP", 0, 0xF8B800, 0xC87800, 4, 6, 99, 30, 120, 10, Rarity.RARE, EnumSet.of(Trait.HARD, Trait.FLEE), RetroItem.MIGHT_SEED, 4),
    DUST_WISP("DUST WISP", 1, 0xBCBCBC, 0x8C34C8, 8, 7, 3, 9, 3, 4, Rarity.COMMON, EnumSet.noneOf(Trait.class), RetroItem.TONIC, 10),
    EMBER_WISP("EMBER WISP", 1, 0xF87818, 0xD82800, 16, 11, 6, 12, 9, 9, Rarity.UNCOMMON, EnumSet.of(Trait.ZAP), RetroItem.TONIC, 6),
    SHARDBACK("SHARDBACK", 2, 0x9C9C9C, 0x3CE0E0, 16, 10, 9, 4, 6, 7, Rarity.COMMON, EnumSet.noneOf(Trait.class), RetroItem.HERB, 6),
    GLASSBACK("GLASSBACK", 2, 0xF0F0FC, 0xF878C8, 28, 15, 18, 6, 16, 14, Rarity.UNCOMMON, EnumSet.of(Trait.CALL), RetroItem.STAR_SHARD, 16),
    PUFFCAP("PUFFCAP", 3, 0xD82800, 0xF0D090, 10, 6, 4, 5, 4, 5, Rarity.COMMON, EnumSet.of(Trait.SLEEP), RetroItem.HERB, 8),
    SHADECAP("SHADECAP", 3, 0x8C34C8, 0x9C9C9C, 22, 12, 8, 8, 12, 12, Rarity.UNCOMMON, EnumSet.of(Trait.SLEEP, Trait.HEAL), RetroItem.LIFE_SEED, 12),
    GLOOMWING("GLOOMWING", 5, 0x3C3C3C, 0xD82800, 12, 9, 4, 14, 6, 6, Rarity.COMMON, EnumSet.of(Trait.FLEE), RetroItem.TORCH, 6),
    STARE_ORB("STARE ORB", 7, 0xF8F8F8, 0x0058F8, 20, 12, 7, 10, 14, 12, Rarity.UNCOMMON, EnumSet.of(Trait.ZAP, Trait.SLEEP), RetroItem.TONIC, 5),
    GNASHBOX("GNASHBOX", 6, 0xA0581C, 0xF8B800, 34, 18, 12, 9, 30, 60, Rarity.RARE, EnumSet.of(Trait.ZAP), RetroItem.STAR_SHARD, 3),
    MOSS_KNIGHT("MOSS KNIGHT", 4, 0x2C8C18, 0x80D010, 36, 17, 14, 7, 32, 25, Rarity.UNCOMMON, EnumSet.noneOf(Trait.class), RetroItem.CHAIN_MAIL, 12),
    STONE_KNIGHT("STONE KNIGHT", 4, 0x7C7C7C, 0xD82800, 50, 21, 18, 7, 55, 40, Rarity.RARE, EnumSet.of(Trait.DOUBLE), RetroItem.IRON_AXE, 10),
    SHARD_TYRANT("SHARD TYRANT", 4, 0xF8B800, 0x8C34C8, 160, 28, 20, 12, 400, 300, Rarity.LEGENDARY,
            EnumSet.of(Trait.DOUBLE, Trait.ZAP, Trait.HEAL, Trait.BOSS), RetroItem.STAR_SHARD, 1);

    /** How often a monster turns up, before a zone's own weights. */
    public enum Rarity { COMMON, UNCOMMON, RARE, LEGENDARY }

    /** What a monster does besides biting. */
    public enum Trait {
        /** Its bite can poison: a poisoned member loses health each step and each round. */
        POISON,
        /** Breathes spores: puts one member to sleep for a few rounds. */
        SLEEP,
        /** Casts a bolt that ignores armour. */
        ZAP,
        /** Mends a hurt ally (or itself). */
        HEAL,
        /** Calls another of its kind into the fight. */
        CALL,
        /** Runs away when it can. */
        FLEE,
        /** So hard that every hit does 1 and spells bounce off. */
        HARD,
        /** Acts twice a round. */
        DOUBLE,
        /** A guardian: met once, on its tile; the party cannot run. */
        BOSS
    }

    private final String title;
    private final int shape;
    private final int body;
    private final int accent;
    private final int hp;
    private final int atk;
    private final int def;
    private final int agi;
    private final int exp;
    private final int gold;
    private final Rarity rarity;
    private final EnumSet<Trait> traits;
    private final RetroItem drop;
    private final int dropOneIn;

    RetroMonster(String title, int shape, int body, int accent, int hp, int atk, int def, int agi, int exp, int gold,
                 Rarity rarity, EnumSet<Trait> traits, RetroItem drop, int dropOneIn) {
        this.title = title;
        this.shape = shape;
        this.body = body;
        this.accent = accent;
        this.hp = hp;
        this.atk = atk;
        this.def = def;
        this.agi = agi;
        this.exp = exp;
        this.gold = gold;
        this.rarity = rarity;
        this.traits = traits;
        this.drop = drop;
        this.dropOneIn = dropOneIn;
    }

    public String title() {
        return title;
    }

    public int shape() {
        return shape;
    }

    public int body() {
        return body;
    }

    public int accent() {
        return accent;
    }

    public int hp() {
        return hp;
    }

    public int atk() {
        return atk;
    }

    public int def() {
        return def;
    }

    public int agi() {
        return agi;
    }

    public int exp() {
        return exp;
    }

    public int gold() {
        return gold;
    }

    public Rarity rarity() {
        return rarity;
    }

    public boolean has(Trait t) {
        return traits.contains(t);
    }

    public Set<Trait> traits() {
        return EnumSet.copyOf(traits);
    }

    public RetroItem drop() {
        return drop;
    }

    public int dropOneIn() {
        return dropOneIn;
    }
}
