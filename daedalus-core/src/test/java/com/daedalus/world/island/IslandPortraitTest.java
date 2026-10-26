// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

import org.junit.jupiter.api.Test;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The deed portrait (ADR-027): a pure function of the seed, a valid PNG that says exactly what the
 * pixels say, and a picture of an island rather than of the sky.
 */
class IslandPortraitTest {

    /** Seed 11 at the default radius. A change to the generator or the renderer moves this. */
    static final String GOLDEN_11 = "58c947553aeb7f16a2aa6d6014ec30c3cff3efc2174606780966014febdee71f";

    @Test
    void theSameSeedPaintsTheSamePicture() {
        IslandPortrait a = IslandPortrait.of(IslandGenerator.generate(11));
        IslandPortrait b = IslandPortrait.of(IslandGenerator.generate(11));
        assertThat(a.digest()).isEqualTo(b.digest());
        assertThat(a.digest()).isEqualTo(GOLDEN_11);
        assertThat(IslandPortrait.of(IslandGenerator.generate(12)).digest()).isNotEqualTo(a.digest());
    }

    @Test
    void thePngDecodesToExactlyThePixels() throws Exception {
        IslandPortrait p = IslandPortrait.of(IslandGenerator.generate(42));
        BufferedImage img = ImageIO.read(new ByteArrayInputStream(p.png()));
        assertThat(img.getWidth()).isEqualTo(IslandPortrait.SIZE);
        assertThat(img.getHeight()).isEqualTo(IslandPortrait.SIZE);
        int[] px = p.pixels();
        for (int y = 0; y < img.getHeight(); y += 7) {
            for (int x = 0; x < img.getWidth(); x += 7) {
                assertThat(img.getRGB(x, y) & 0xFFFFFF).as("%d,%d", x, y).isEqualTo(px[y * IslandPortrait.SIZE + x] & 0xFFFFFF);
            }
        }
    }

    @Test
    void theIslandFillsTheFrameAndTheCornersAreSky() {
        // Clouds are not framed and may crop, so judge the frame on the island without them.
        IslandPlan full = IslandGenerator.generate(11);
        java.util.TreeMap<com.daedalus.world.BlockCoordinate, com.daedalus.world.BlockType> ground = new java.util.TreeMap<>(IslandGenerator.ORDER);
        full.blocks().forEach((c, t) -> {
            if (t != com.daedalus.world.BlockType.CLOUD) {
                ground.put(c, t);
            }
        });
        int[] px = IslandPortrait.of(new IslandPlan(full.traits(), ground)).pixels();
        int s = IslandPortrait.SIZE;
        int corner = px[0];
        assertThat(px[s - 1]).isEqualTo(corner); // the gradient is vertical: a row is one colour
        int island = 0;
        int minX = s;
        int maxX = 0;
        for (int y = 0; y < s; y++) {
            int sky = px[y * s];
            for (int x = 0; x < s; x++) {
                if (px[y * s + x] != sky) {
                    island++;
                    minX = Math.min(minX, x);
                    maxX = Math.max(maxX, x);
                }
            }
        }
        assertThat(island).as("pixels that are not sky").isGreaterThan(s * s / 6);
        assertThat(maxX - minX).as("island width").isGreaterThan(s / 2);
        assertThat(minX).as("left margin").isGreaterThanOrEqualTo(8);
        assertThat(s - 1 - maxX).as("right margin").isGreaterThanOrEqualTo(8);
    }

    @Test
    void theCubeSpriteIsAHexagonOfThreeFaces() {
        byte[] m = IslandPortrait.sprite(8);
        int[] count = new int[4];
        for (byte b : m) {
            count[b]++;
        }
        // A 16×16 box: rhombus 64 px, each side 64 px, the rest empty corners.
        assertThat(count[1]).isBetween(56, 72);
        assertThat(count[2]).isBetween(56, 72);
        assertThat(count[2]).isEqualTo(count[3]);
        assertThat(m[0]).isZero();
        assertThat(m[4 * 16 + 8]).as("centre of the top face").isEqualTo((byte) 1);
        assertThat(m[12 * 16 + 4]).as("lower left is the +Z side").isEqualTo((byte) 2);
        assertThat(m[12 * 16 + 12]).as("lower right is the +X side").isEqualTo((byte) 3);
        assertThat(m[15 * 16 + 0]).as("the bottom corners are empty").isZero();
    }
}
