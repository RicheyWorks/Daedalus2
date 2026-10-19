// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ArkDrydock.ArkClass;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Rivet Line (contest gap G104): head the hull rivets for an ark on the drydock slip. G24 {@link ArkDrydock} counts
 * rivets per seam, and every missing rivet costs a seam {@value ArkDrydock#MISSING_RIVET_COST} strength. This is
 * where those rivets come from.
 *
 * <p>The forge tray heats one rivet per hole, {@value ArkDrydock#RIVETS_PER_SEAM} per seam. Each rivet reaches
 * setting heat at its own seeded moment and stays workable for {@value #WINDOW_MS} ms. Set it before then and it
 * won't upset (SPOILED). Set it after and it seats LOOSE. Inside the window, the strikes decide: three or more
 * make it TIGHT, two make it SNUG, fewer leave it LOOSE. Each seam counts its TIGHT and SNUG rivets, and that list
 * goes straight into an {@link ArkDrydock.Ark}.
 *
 * <p>Pure and deterministic: {@link #tray} gives the same heats for the same seed, and {@link #judge} gives the same
 * {@link Result} for the same sets.
 */
public final class RivetLine {

    /** How long a rivet stays at setting heat. */
    public static final int WINDOW_MS = 800;
    /** Strikes that make a hot rivet tight. */
    public static final int TIGHT_STRIKES = 3;

    /** How a rivet seated. */
    public enum Seat { TIGHT, SNUG, LOOSE, SPOILED }

    /** One rivet's moment at setting heat, ms after the tray goes in. */
    public record Tray(ArkClass arkClass, List<Integer> readyMs) {

        public Tray {
            readyMs = List.copyOf(readyMs);
        }

        public int holes() {
            return readyMs.size();
        }
    }

    /** The smith's work on one rivet: when it was set and how many strikes it took. */
    public record Set(int atMs, int strikes) {
    }

    /** The line: every rivet's seat, the good rivets per seam (ArkDrydock order) and Brannoc's verdict. */
    public record Result(List<Seat> seats, List<Integer> rivetsPerSeam, int tight, int snug, int loose, int spoiled,
                         String line) {

        public Result {
            seats = List.copyOf(seats);
            rivetsPerSeam = List.copyOf(rivetsPerSeam);
        }
    }

    private RivetLine() {
    }

    /** The tray for an ark of class {@code c}: one rivet per hole, ready 1.5–2.45 s after the tray goes in. */
    public static Tray tray(ArkClass c, long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x51E7L);
        int holes = c.plates() * ArkDrydock.RIVETS_PER_SEAM;
        List<Integer> ready = new ArrayList<>(holes);
        for (int i = 0; i < holes; i++) {
            ready.add(1500 + 50 * rng.nextInt(20));
        }
        return new Tray(c, ready);
    }

    /** How one rivet seated. */
    public static Seat seat(int readyMs, Set s) {
        if (s == null || s.atMs() < readyMs) {
            return Seat.SPOILED;
        }
        if (s.atMs() > readyMs + WINDOW_MS || s.strikes() < 2) {
            return Seat.LOOSE;
        }
        return s.strikes() >= TIGHT_STRIKES ? Seat.TIGHT : Seat.SNUG;
    }

    /** Judge the line. A missing set (fewer sets than holes) spoils that rivet. */
    public static Result judge(Tray t, List<Set> sets) {
        List<Seat> seats = new ArrayList<>(t.holes());
        int[] n = new int[Seat.values().length];
        for (int i = 0; i < t.holes(); i++) {
            Seat s = seat(t.readyMs().get(i), i < sets.size() ? sets.get(i) : null);
            seats.add(s);
            n[s.ordinal()]++;
        }
        List<Integer> perSeam = new ArrayList<>(t.arkClass().plates());
        for (int seam = 0; seam < t.arkClass().plates(); seam++) {
            int good = 0;
            for (int k = 0; k < ArkDrydock.RIVETS_PER_SEAM; k++) {
                Seat s = seats.get(seam * ArkDrydock.RIVETS_PER_SEAM + k);
                good += s == Seat.TIGHT || s == Seat.SNUG ? 1 : 0;
            }
            perSeam.add(good);
        }
        int good = n[Seat.TIGHT.ordinal()] + n[Seat.SNUG.ordinal()];
        return new Result(seats, perSeam, n[Seat.TIGHT.ordinal()], n[Seat.SNUG.ordinal()], n[Seat.LOOSE.ordinal()],
                n[Seat.SPOILED.ordinal()], line(good, t.holes(), n[Seat.SPOILED.ordinal()]));
    }

    /** The riveter's run: every rivet set the moment it's ready, three strikes each. */
    public static List<Set> master(Tray t) {
        List<Set> sets = new ArrayList<>(t.holes());
        for (int r : t.readyMs()) {
            sets.add(new Set(r, TIGHT_STRIKES));
        }
        return sets;
    }

    /** Drydock Master Brannoc Slagg on the rivet line. */
    static String line(int good, int holes, int spoiled) {
        if (good == holes) {
            return "Every hole filled hot. She'll hold the void.";
        }
        if (spoiled * 4 >= holes) {
            return "You're hitting them before they glow. Wait for the colour.";
        }
        if (good * 4 >= holes * 3) {
            return "A few loose heads. Drill them out or the seams pay for it.";
        }
        return "Hull wants tempered rivets, not soft iron.";
    }
}
