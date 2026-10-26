// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ForgeGrades.Material;
import com.daedalus.world.forge.ForgeGrades.Weapon;
import com.daedalus.world.forge.ForgeGrades.WeaponGrade;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.SplittableRandom;

/**
 * Forge Commissions (contest gap G87): the Great Forge's order board. Every forge day the island's people pin three
 * commissions. Each names a weapon, a metal, the lowest temper tier they will accept and a due shift. The smith
 * forges at the anvil (G19 {@link TemperForge}), grades the piece ({@link ForgeGrades}) and delivers it. Clean work
 * pays the full price plus a tip for every temper point above the minimum. Late work pays half. Wrong or
 * under-tempered work comes back with the patron's complaint. A ledger keeps each patron's regard for the smith,
 * and a patron who thinks well of you tips more.
 *
 * <p>Pure and deterministic: {@link #board(long)} draws the same day for the same seed, and {@link #deliver} judges
 * a delivery without side effects. Only {@link Ledger#record} changes state. The host owns the board and the ledger.
 */
public final class ForgeCommissions {

    /** Commissions pinned each forge day. */
    public static final int PER_DAY = 3;
    /** Regard starts here and is clamped to 0..100. */
    public static final int START_REGARD = 50;

    /** Who orders from the Great Forge. */
    public enum Patron {
        BRANNOC("Drydock Master Brannoc Slagg"),
        HESPER("Quartermaster Hesper Coalhand"),
        YSOLDE("Old Keeper Ysolde Anvilward"),
        OTTAR("Ottar Flintwick, Kennel Isle warden"),
        MIRA("Captain Mira Sootvane of Storm Anchorage");

        private final String title;

        Patron(String title) {
            this.title = title;
        }

        public String title() {
            return title;
        }
    }

    /** The lowest tier a patron accepts; ForgeGrades tier names, weakest first. */
    public enum MinTier {
        CRUDE(20), STANDARD(50), FINE(80), MASTERWORK(95);

        private final int temper;

        MinTier(int temper) {
            this.temper = temper;
        }

        /** The lowest temper that reaches this tier. */
        public int temper() {
            return temper;
        }
    }

    /** Why a delivery came back. */
    public enum Verdict { PAID, PAID_LATE, WRONG_WEAPON, WRONG_METAL, UNDER_TEMPERED }

    /** One pinned order. */
    public record Commission(int day, int slot, Patron patron, Weapon weapon, Material material, MinTier minTier,
                             int dueShifts, int priceCoins) {

        /** CMS 1 single-line encoding, the same text as Encode(Commission) in DaedalusForgeCommissionsCore.h. */
        public String encode() {
            return "CMS 1 day=" + day + " slot=" + slot + " " + patron + " " + weapon + " " + material + " min=" + minTier
                    + " due=" + dueShifts + " price=" + priceCoins;
        }
    }

    /** What handing the piece over did. */
    public record Delivery(Verdict verdict, int coins, int tipCoins, int regardDelta, String line) {

        public boolean paid() {
            return verdict == Verdict.PAID || verdict == Verdict.PAID_LATE;
        }

        /** CMD 1 single-line encoding, the same text as Encode(Delivery) in DaedalusForgeCommissionsCore.h. */
        public String encode() {
            return "CMD 1 " + verdict + " coins=" + coins + " tip=" + tipCoins + " regard" + (regardDelta >= 0 ? "+" : "")
                    + regardDelta + " | " + line;
        }
    }

    private static final Material[] METALS = {Material.COPPER, Material.BRONZE, Material.IRON, Material.STEEL,
        Material.STARMETAL};
    private static final int[] METAL_PRICE = {12, 18, 26, 40, 90};

    private ForgeCommissions() {
    }

    /** The order board for forge day {@code day}; the same day always pins the same three commissions. */
    public static List<Commission> board(long day) {
        SplittableRandom rng = new SplittableRandom(day ^ 0xC0331L);
        List<Commission> out = new ArrayList<>(PER_DAY);
        for (int slot = 0; slot < PER_DAY; slot++) {
            Patron patron = Patron.values()[rng.nextInt(Patron.values().length)];
            Weapon weapon = Weapon.values()[rng.nextInt(2)];
            int m = rng.nextInt(METALS.length);
            int roll = rng.nextInt(10);
            MinTier min = roll < 4 ? MinTier.STANDARD : roll < 8 ? MinTier.FINE : roll < 9 ? MinTier.CRUDE
                    : MinTier.MASTERWORK;
            int due = 1 + rng.nextInt(3);
            int price = METAL_PRICE[m] * tierFactorPct(min) / 100 + (due == 1 ? METAL_PRICE[m] / 4 : 0);
            out.add(new Commission((int) day, slot, patron, weapon, METALS[m], min, due, price));
        }
        return out;
    }

    /** CRUDE 60%, STANDARD 100%, FINE 150%, MASTERWORK 250% of the metal's price. */
    static int tierFactorPct(MinTier t) {
        return switch (t) {
            case CRUDE -> 60;
            case STANDARD -> 100;
            case FINE -> 150;
            case MASTERWORK -> 250;
        };
    }

    /** Judge a delivery of {@code piece} after {@code shiftsTaken} shifts, given the patron's {@code regard}. */
    public static Delivery deliver(Commission c, WeaponGrade piece, int shiftsTaken, int regard) {
        Objects.requireNonNull(c, "commission");
        Objects.requireNonNull(piece, "piece");
        if (shiftsTaken < 0) {
            throw new IllegalArgumentException("shifts taken must be >= 0: " + shiftsTaken);
        }
        if (piece.weapon() != c.weapon()) {
            return new Delivery(Verdict.WRONG_WEAPON, 0, 0, -3, complaint(c.patron(), Verdict.WRONG_WEAPON));
        }
        if (piece.material() != c.material()) {
            return new Delivery(Verdict.WRONG_METAL, 0, 0, -3, complaint(c.patron(), Verdict.WRONG_METAL));
        }
        if (piece.temper() < c.minTier().temper()) {
            return new Delivery(Verdict.UNDER_TEMPERED, 0, 0, -3, complaint(c.patron(), Verdict.UNDER_TEMPERED));
        }
        int over = piece.temper() - c.minTier().temper();
        int tip = c.priceCoins() * over * (50 + clamp(regard)) / 10000;
        if (shiftsTaken > c.dueShifts()) {
            return new Delivery(Verdict.PAID_LATE, c.priceCoins() / 2, 0, 1, thanks(c.patron(), true));
        }
        return new Delivery(Verdict.PAID, c.priceCoins(), tip, 5, thanks(c.patron(), false));
    }

    /** Each patron's regard for the smith. */
    public static final class Ledger {

        private final Map<Patron, Integer> regard = new EnumMap<>(Patron.class);
        private int coins;
        private int delivered;

        public int regard(Patron p) {
            return regard.getOrDefault(p, START_REGARD);
        }

        public int coins() {
            return coins;
        }

        public int delivered() {
            return delivered;
        }

        /** Deliver and book it: coins and tip in the purse, the patron's regard moved. */
        public Delivery record(Commission c, WeaponGrade piece, int shiftsTaken) {
            Delivery d = deliver(c, piece, shiftsTaken, regard(c.patron()));
            regard.put(c.patron(), clamp(regard(c.patron()) + d.regardDelta()));
            coins += d.coins() + d.tipCoins();
            if (d.paid()) {
                delivered++;
            }
            return d;
        }
    }

    static int clamp(int r) {
        return Math.max(0, Math.min(100, r));
    }

    static String thanks(Patron p, boolean late) {
        if (late) {
            return switch (p) {
                case BRANNOC -> "The tide doesn't wait and neither did I. Half, for half the patience.";
                case HESPER -> "Logged late. The manifest has a long memory.";
                case YSOLDE -> "Late is still tempered. Half, and a lesson.";
                case OTTAR -> "The pups went a day unguarded. Here's half.";
                case MIRA -> "We sailed short a blade. Half pay, smith.";
            };
        }
        return switch (p) {
            case BRANNOC -> "Rings true. That one goes on the ark.";
            case HESPER -> "Weighed, logged, paid. Clean work.";
            case YSOLDE -> "Heat and water both. You listened.";
            case OTTAR -> "Good steel for the Kennel walls. The dogs thank you.";
            case MIRA -> "It'll hold in a storm. Pleasure, smith.";
        };
    }

    static String complaint(Patron p, Verdict v) {
        String what = switch (v) {
            case WRONG_WEAPON -> "That's not what I pinned.";
            case WRONG_METAL -> "Wrong metal. Read the board.";
            default -> "Soft. Take it back to the quench.";
        };
        return p.title() + ": " + what;
    }
}
