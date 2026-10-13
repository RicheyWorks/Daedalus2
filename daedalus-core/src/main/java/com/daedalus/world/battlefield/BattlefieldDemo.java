// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import com.daedalus.world.battlefield.BattlefieldEcology.EventKind;

import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import javax.imageio.ImageIO;

/**
 * A runnable encounter (ADR-061): a squad in a meadow takes fire from the east and picks cover in the wood; a blast
 * sets the wood alight, the wind drives the fire, and the squad's cover choice moves away from the flames; years
 * later the crater has regrown. Prints text frames and optionally writes a PNG strip.
 *
 * <p>Usage: {@code BattlefieldDemo [out.png]}.
 */
public final class BattlefieldDemo {

    /** Unit and threat positions in centimetres. */
    public static final double UNIT_X = 900;
    public static final double UNIT_Y = 1500;
    public static final double THREAT_X = 3900;
    public static final double THREAT_Y = 1500;
    private static final double SEARCH_CM = 1400;

    /** One captured moment of the encounter. */
    public record Frame(String title, char[][] map, double[] cover) {
    }

    private BattlefieldDemo() {
    }

    /** The demo map: meadow, an oak/pine wood north-east of the squad, a scrub belt and a wetland stream. */
    public static BattlefieldEcology scene(long seed) {
        BattlefieldEcology e = new BattlefieldEcology(40, 30, 100, 0, 0, seed).wind(1, 0);
        for (int j = 0; j < 30; j++) {
            for (int i = 0; i < 40; i++) {
                Vegetation v = Vegetation.MEADOW;
                if (i >= 12 && i <= 22 && j >= 6 && j <= 16) {
                    v = (i + j) % 3 == 0 ? Vegetation.PINE : Vegetation.OAK;
                } else if (j >= 20 && j <= 23 && i < 26) {
                    v = Vegetation.SCRUB;
                } else if (i == 28 || i == 29) {
                    v = Vegetation.WETLAND;
                }
                e.set(i, j, v);
            }
        }
        return e;
    }

    /** Runs the encounter deterministically and returns its frames. */
    public static List<Frame> run(long seed) {
        BattlefieldEcology e = scene(seed);
        List<Frame> frames = new ArrayList<>();
        frames.add(capture(e, "1 contact: squad picks cover"));
        e.apply(EventKind.BLAST, 1350, 1550, 200);
        frames.add(capture(e, "2 blast on the cover"));
        for (int t = 0; t < 3; t++) {
            e.tick();
        }
        frames.add(capture(e, "3 fire spreads: cover moves"));
        for (int t = 0; t < 300; t++) {
            e.tick();
        }
        e.grow(20);
        frames.add(capture(e, "4 twenty years later"));
        return frames;
    }

    private static Frame capture(BattlefieldEcology e, String title) {
        double[] c = e.bestCover(UNIT_X, UNIT_Y, THREAT_X, THREAT_Y, SEARCH_CM);
        char[][] m = new char[e.height()][e.width()];
        for (int j = 0; j < e.height(); j++) {
            for (int i = 0; i < e.width(); i++) {
                m[j][i] = e.burning(i, j) > 0 ? '*' : e.vegetation(i, j).code();
            }
        }
        m[e.cellJ(UNIT_Y)][e.cellI(UNIT_X)] = 'U';
        m[e.cellJ(THREAT_Y)][e.cellI(THREAT_X)] = 'T';
        if (c != null) {
            m[e.cellJ(c[1])][e.cellI(c[0])] = 'C';
        }
        return new Frame(title, m, c);
    }

    /** Text rendering of one frame. */
    public static String text(Frame f) {
        StringBuilder b = new StringBuilder("== ").append(f.title());
        if (f.cover() != null) {
            b.append(String.format(" | cover at (%.0f, %.0f) score %.2f", f.cover()[0], f.cover()[1], f.cover()[2]));
        }
        b.append('\n');
        for (char[] row : f.map()) {
            b.append(row).append('\n');
        }
        return b.toString();
    }

    /** Writes the frames side by side as a PNG, 8 px per cell. */
    public static void png(List<Frame> frames, Path out) throws IOException {
        int px = 8;
        int w = frames.get(0).map()[0].length;
        int h = frames.get(0).map().length;
        BufferedImage img = new BufferedImage(frames.size() * (w * px + px), h * px + 16, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = img.createGraphics();
        g.setColor(Color.DARK_GRAY);
        g.fillRect(0, 0, img.getWidth(), img.getHeight());
        for (int f = 0; f < frames.size(); f++) {
            int ox = f * (w * px + px);
            g.setColor(Color.WHITE);
            g.drawString(frames.get(f).title(), ox + 2, 12);
            for (int j = 0; j < h; j++) {
                for (int i = 0; i < w; i++) {
                    g.setColor(colour(frames.get(f).map()[j][i]));
                    g.fillRect(ox + i * px, 16 + j * px, px, px);
                }
            }
        }
        g.dispose();
        ImageIO.write(img, "png", out.toFile());
    }

    private static Color colour(char c) {
        return switch (c) {
            case 'm' -> new Color(160, 200, 90);
            case 's' -> new Color(110, 150, 60);
            case 'p' -> new Color(40, 110, 60);
            case 'o' -> new Color(30, 80, 30);
            case 'w' -> new Color(60, 110, 190);
            case '*' -> new Color(255, 110, 0);
            case 'U' -> Color.CYAN;
            case 'T' -> Color.RED;
            case 'C' -> Color.YELLOW;
            default -> new Color(120, 100, 80);
        };
    }

    /** Entry point. */
    public static void main(String[] args) throws IOException {
        List<Frame> frames = run(42);
        for (Frame f : frames) {
            System.out.print(text(f));
        }
        if (args.length > 0) {
            Path out = Path.of(args[0]);
            if (out.getParent() != null) {
                Files.createDirectories(out.getParent());
            }
            png(frames, out);
            System.out.println("wrote " + out);
        }
    }
}