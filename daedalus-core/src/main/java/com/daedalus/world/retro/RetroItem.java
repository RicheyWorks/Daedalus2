// SPDX-License-Identifier: MIT

package com.daedalus.world.retro;

/**
 * Everything the party can carry in the 8-bit realm (ADR-052).
 *
 * <p>{@code power} means: for USE items, how much it heals or restores (a torch's light radius, a seed's permanent
 * gain); for keys, the lock tier it opens (1 bronze, 2 silver, 3 star); for weapons and armour, attack or defence
 * added; for treasure, what a shop pays for it. A price of 0 means no shop sells it: it is only ever found.
 */
public enum RetroItem {
    HERB(Kind.USE, 10, 25, "HERB"),
    TONIC(Kind.USE, 30, 10, "TONIC"),
    ANTIDOTE(Kind.USE, 8, 0, "ANTIDOTE"),
    TORCH(Kind.USE, 8, 3, "TORCH"),
    WINGS(Kind.USE, 25, 0, "WINGS"),
    MIGHT_SEED(Kind.USE, 0, 2, "MIGHT SEED"),
    LIFE_SEED(Kind.USE, 0, 6, "LIFE SEED"),
    BRONZE_KEY(Kind.KEY, 45, 1, "BRONZE KEY"),
    SILVER_KEY(Kind.KEY, 0, 2, "SILVER KEY"),
    STAR_KEY(Kind.KEY, 0, 3, "STAR KEY"),
    CLUB(Kind.WEAPON, 25, 4, "CLUB"),
    COPPER_SWORD(Kind.WEAPON, 110, 9, "COPPER SWORD"),
    IRON_AXE(Kind.WEAPON, 280, 15, "IRON AXE"),
    EMBER_BLADE(Kind.WEAPON, 0, 22, "EMBER BLADE"),
    STAR_BLADE(Kind.WEAPON, 0, 30, "STAR BLADE"),
    CLOTHES(Kind.ARMOR, 15, 2, "CLOTHES"),
    LEATHER_VEST(Kind.ARMOR, 70, 6, "LEATHER VEST"),
    CHAIN_MAIL(Kind.ARMOR, 240, 12, "CHAIN MAIL"),
    SHARD_MAIL(Kind.ARMOR, 0, 18, "SHARD MAIL"),
    METEOR_MAIL(Kind.ARMOR, 0, 26, "METEOR MAIL"),
    STAR_SHARD(Kind.TREASURE, 0, 300, "STAR SHARD"),
    DRAGON_EGG(Kind.EGG, 0, 0, "DRAGON EGG");

    /** What an item is for. */
    public enum Kind { USE, KEY, WEAPON, ARMOR, TREASURE, EGG }

    private final Kind kind;
    private final int price;
    private final int power;
    private final String title;

    RetroItem(Kind kind, int price, int power, String title) {
        this.kind = kind;
        this.price = price;
        this.power = power;
        this.title = title;
    }

    public Kind kind() {
        return kind;
    }

    public int price() {
        return price;
    }

    public int power() {
        return power;
    }

    /** The name on screen: capitals, at most 12 characters, so it fits every menu. */
    public String title() {
        return title;
    }

    /** True when no shop sells it. */
    public boolean foundOnly() {
        return price == 0;
    }

    /** What a shop pays: half the price, or a treasure's worth. */
    public int sellValue() {
        return kind == Kind.TREASURE ? power : price / 2;
    }
}
