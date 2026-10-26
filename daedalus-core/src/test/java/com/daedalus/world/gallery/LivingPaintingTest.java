// SPDX-License-Identifier: MIT
package com.daedalus.world.gallery;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class LivingPaintingTest {

    /** Pigment ground or mixed for a colour, using only realm chemistry. */
    static void stock(PigmentPalette pal, Pigment p, ColourKnowledge k) {
        if (!p.sources().isEmpty()) {
            assertThat(pal.grind(p.sources().get(0))).isEqualTo(PigmentPalette.Result.OK);
            return;
        }
        for (Pigment c : p.components()) pal.grind(c.sources().get(0));
        assertThat(pal.mix(p, k)).isEqualTo(PigmentPalette.Result.OK);
    }

    /** A knowledge that already knows every primary (so violet can be mixed). */
    static ColourKnowledge primed() {
        ColourKnowledge k = new ColourKnowledge();
        for (Pigment p : new Pigment[] {Pigment.RED, Pigment.YELLOW, Pigment.BLUE})
            for (int i = 0; i < ColourKnowledge.KNOW_AT; i++) k.learn(p);
        return k;
    }

    @Test
    void sameSeedSameMuralAndSubject() {
        LivingPainting a = new LivingPainting(424_242, 6, 4), b = new LivingPainting(424_242, 6, 4);
        for (int y = 0; y < 4; y++) for (int x = 0; x < 6; x++)
            assertThat(a.reveal(x, y, primed())).isEqualTo(b.reveal(x, y, primed()));
        assertThat(a.subject()).isEqualTo(b.subject()).isIn(LivingPainting.SUBJECTS);
        assertThat(a.colours()).hasSizeBetween(1, 4);
        assertThat(a.state()).isEqualTo(LivingPainting.State.DRAINED);
    }

    @Test
    void restoringEveryCellWakesThePainting() {
        LivingPainting m = new LivingPainting(7_001, 4, 3);
        ColourKnowledge k = primed();
        PigmentPalette pal = new PigmentPalette();
        for (int y = 0; y < 3; y++) for (int x = 0; x < 4; x++) {
            Pigment need = m.reveal(x, y, k);
            stock(pal, need, k);
            assertThat(m.paint(x, y, need, pal, k)).isEqualTo(LivingPainting.Result.RESTORED);
            if (x == 0 && y == 0) assertThat(m.state()).isEqualTo(LivingPainting.State.RESTORING);
        }
        assertThat(m.state()).isEqualTo(LivingPainting.State.LIVING);
        assertThat(m.progressPm()).isEqualTo(1000);
        assertThat(m.paint(0, 0, Pigment.RED, pal, k)).isEqualTo(LivingPainting.Result.ALREADY_RESTORED);
    }

    @Test
    void wrongColourSmudgesAndNeedsAWash() {
        LivingPainting m = new LivingPainting(99, 2, 2);
        ColourKnowledge k = primed();
        Pigment need = m.reveal(0, 0, k);
        Pigment wrong = need == Pigment.RED ? Pigment.BLUE : Pigment.RED;
        PigmentPalette pal = new PigmentPalette();
        stock(pal, wrong, k);
        assertThat(m.paint(0, 0, wrong, pal, k)).isEqualTo(LivingPainting.Result.SMUDGED);
        assertThat(pal.count(wrong)).isZero(); // pigment is spent either way
        assertThat(m.smudges()).isEqualTo(1);
        stock(pal, need, k);
        assertThat(m.paint(0, 0, need, pal, k)).isEqualTo(LivingPainting.Result.NEEDS_WASH);
        assertThat(m.wash(0, 0)).isEqualTo(LivingPainting.Result.WASHED);
        assertThat(m.wash(0, 0)).isEqualTo(LivingPainting.Result.NOTHING_TO_WASH);
        assertThat(m.paint(0, 0, need, pal, k)).isEqualTo(LivingPainting.Result.RESTORED);
    }

    @Test
    void noPigmentNoStrokeAndPrismSightIsGated() {
        LivingPainting m = new LivingPainting(5, 2, 2);
        ColourKnowledge novice = new ColourKnowledge();
        assertThat(m.paint(0, 0, Pigment.RED, new PigmentPalette(), novice)).isEqualTo(LivingPainting.Result.NO_PIGMENT);
        assertThat(m.cell(0, 0)).isEqualTo(LivingPainting.Cell.GREY);
        assertThatThrownBy(() -> m.reveal(0, 0, novice)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void forFrameUsesTheFrameSeedAndSizeAndRejectsBadInput() {
        GalleryOps.Frame f = new GalleryOps.Frame(0, 1, 0, GalleryOps.Facing.NORTH, 3, 2, 123_456);
        LivingPainting m = LivingPainting.forFrame(f);
        assertThat(m.seed()).isEqualTo(123_456);
        assertThat(m.width()).isEqualTo(6);
        assertThat(m.height()).isEqualTo(4);
        GalleryOps.Frame big = new GalleryOps.Frame(0, 1, 0, GalleryOps.Facing.NORTH, 6, 6, 1);
        assertThat(LivingPainting.forFrame(big).cellCount()).isEqualTo(144);
        assertThatThrownBy(() -> new LivingPainting(-1, 2, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LivingPainting(1, 13, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> m.cell(6, 0)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void seedsSpreadAcrossColoursAndSubjects() {
        java.util.Set<String> subjects = new java.util.HashSet<>();
        java.util.EnumSet<Pigment> used = java.util.EnumSet.noneOf(Pigment.class);
        for (long s = 0; s < 60; s++) {
            LivingPainting m = new LivingPainting(s, 4, 4);
            subjects.add(m.subject());
            used.addAll(m.colours());
        }
        assertThat(subjects).hasSize(LivingPainting.SUBJECTS.size());
        assertThat(used).containsExactlyInAnyOrder(Pigment.values());
    }
}
