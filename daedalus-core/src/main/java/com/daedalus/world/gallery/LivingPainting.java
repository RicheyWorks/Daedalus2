// SPDX-License-Identifier: MIT
package com.daedalus.world.gallery;

import java.util.ArrayList;
import java.util.EnumSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * GAL01 living painting: a Gallery City mural drained grey by the Grey Wash. Each cell of the mural remembers the
 * colour it should be; the seed (the same number a {@link GalleryOps.Frame} carries) decides the picture, so every
 * client restores the same mural. Painting a cell with the right pigment restores it and teaches that colour;
 * the wrong pigment smudges it (a Smudgeling stirs) and the cell needs a turpentine wash before repainting.
 * When every cell is restored the painting comes alive and its subject steps out as a friendly Gallery creature.
 *
 * <p>Deterministic and portable: no clock, no global random. The host owns identity, inventory and persistence.
 */
public final class LivingPainting {

    public static final int MAX_SIDE = 12;

    /** Friendly Gallery creature kit ids a living painting can wake (data/art/gallery/creature-manifest.json). */
    public static final List<String> SUBJECTS = List.of("Mob_Gallery_PaperCrane", "Mob_Gallery_PrismFinch",
            "Mob_Gallery_CrayonGecko", "Mob_Gallery_Inkpup", "Mob_Gallery_LampMoth", "Mob_Gallery_BrushtailSquirrel");

    public enum State { DRAINED, RESTORING, LIVING }

    public enum Cell { GREY, SMUDGED, RESTORED }

    public enum Result { RESTORED, SMUDGED, NEEDS_WASH, ALREADY_RESTORED, NO_PIGMENT, WASHED, NOTHING_TO_WASH }

    private final long seed;
    private final int width;
    private final int height;
    private final Pigment[] target;
    private final Cell[] cells;
    private int smudges;
    private int restored;
    private final Object lock = new Object();

    /** A mural of {@code width x height} cells (1..12 each) whose colours come from {@code seed}. */
    public LivingPainting(long seed, int width, int height) {
        if (seed < 0 || seed >= GalleryOps.MAX_SEED) throw new IllegalArgumentException("seed out of range");
        if (width < 1 || width > MAX_SIDE || height < 1 || height > MAX_SIDE)
            throw new IllegalArgumentException("mural side must be 1.." + MAX_SIDE);
        this.seed = seed;
        this.width = width;
        this.height = height;
        this.target = new Pigment[width * height];
        this.cells = new Cell[width * height];
        SplittableRandom rng = new SplittableRandom(seed);
        Pigment[] all = Pigment.values();
        // a mural uses a seeded palette of 2..4 colours, so small murals stay learnable
        int paletteSize = 2 + rng.nextInt(3);
        List<Pigment> palette = new ArrayList<>(List.of(all));
        for (int i = palette.size() - 1; i > 0; i--) {
            int j = rng.nextInt(i + 1);
            Pigment t = palette.get(i); palette.set(i, palette.get(j)); palette.set(j, t);
        }
        palette = palette.subList(0, paletteSize);
        for (int i = 0; i < target.length; i++) {
            target[i] = palette.get(rng.nextInt(paletteSize));
            cells[i] = Cell.GREY;
        }
    }

    /** One mural cell per wall cube of the frame, with 2x2 cells per cube (capped at {@link #MAX_SIDE}). */
    public static LivingPainting forFrame(GalleryOps.Frame frame) {
        return new LivingPainting(frame.seed(), Math.min(MAX_SIDE, frame.w() * 2), Math.min(MAX_SIDE, frame.h() * 2));
    }

    /**
     * Paints one cell. The right pigment (spent from the palette) restores it and teaches the colour; the wrong
     * pigment is spent too and smudges the cell. A smudged cell must be washed first.
     */
    public Result paint(int x, int y, Pigment p, PigmentPalette palette, ColourKnowledge knowledge) {
        synchronized (lock) {
            int i = index(x, y);
            if (p == null || palette == null || knowledge == null) throw new IllegalArgumentException("pigment, palette, knowledge required");
            if (cells[i] == Cell.RESTORED) return Result.ALREADY_RESTORED;
            if (cells[i] == Cell.SMUDGED) return Result.NEEDS_WASH;
            if (!palette.spend(p)) return Result.NO_PIGMENT;
            if (p != target[i]) {
                cells[i] = Cell.SMUDGED;
                smudges++;
                return Result.SMUDGED;
            }
            cells[i] = Cell.RESTORED;
            restored++;
            knowledge.learn(p);
            return Result.RESTORED;
        }
    }

    /** Turpentine wash: a smudged cell goes back to grey. */
    public Result wash(int x, int y) {
        synchronized (lock) {
            int i = index(x, y);
            if (cells[i] != Cell.SMUDGED) return Result.NOTHING_TO_WASH;
            cells[i] = Cell.GREY;
            return Result.WASHED;
        }
    }

    /**
     * PRISM_SIGHT hint: the colour a grey cell needs. Only painters who know all three primaries may ask; others
     * get an exception, so a host cannot leak the answer by accident.
     */
    public Pigment reveal(int x, int y, ColourKnowledge knowledge) {
        synchronized (lock) {
            if (!knowledge.abilities().contains(ColourKnowledge.Ability.PRISM_SIGHT))
                throw new IllegalStateException("PRISM_SIGHT not unlocked");
            return target[index(x, y)];
        }
    }

    public State state() {
        synchronized (lock) {
            if (restored == cells.length) return State.LIVING;
            return restored == 0 ? State.DRAINED : State.RESTORING;
        }
    }

    /** Restoration progress per mille. */
    public int progressPm() {
        synchronized (lock) { return restored * 1000 / cells.length; }
    }

    public Cell cell(int x, int y) {
        synchronized (lock) { return cells[index(x, y)]; }
    }

    public int restoredCells() {
        synchronized (lock) { return restored; }
    }

    public int smudges() {
        synchronized (lock) { return smudges; }
    }

    public int cellCount() { return cells.length; }

    public int width() { return width; }

    public int height() { return height; }

    public long seed() { return seed; }

    /** Distinct colours this mural needs. */
    public Set<Pigment> colours() {
        EnumSet<Pigment> s = EnumSet.noneOf(Pigment.class);
        for (Pigment p : target) s.add(p);
        return s;
    }

    /** The friendly creature this mural wakes, fixed by its seed. */
    public String subject() { return SUBJECTS.get((int) (seed % SUBJECTS.size())); }

    private int index(int x, int y) {
        if (x < 0 || x >= width || y < 0 || y >= height) throw new IllegalArgumentException("cell outside mural");
        return y * width + x;
    }
}
