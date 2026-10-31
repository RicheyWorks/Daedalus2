// SPDX-License-Identifier: MIT

package com.daedalus.mazegame;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.time.Clock;

/**
 * Entry point. {@code java -jar daedalus-maze-game.jar [--headless|--text] [--seed N|--daily|--code LR-H-XXXX]
 * [--difficulty easy|normal|hard|brutal]}. With no mode flag it opens the Swing window, or text
 * mode when no display is available.
 */
public final class LabyrinthRun {

    /** Parsed command line. */
    static final class Options {
        String mode = "auto";
        long seed;
        Difficulty difficulty = Difficulty.NORMAL;
    }

    private LabyrinthRun() {
    }

    public static void main(String[] args) throws IOException {
        int code = run(args, System.in, System.out, Clock.systemUTC(), java.awt.GraphicsEnvironment.isHeadless());
        if (code != 0) {
            System.exit(code);
        }
    }

    static int run(String[] args, InputStream in, PrintStream out, Clock clock, boolean noDisplay) throws IOException {
        Options o;
        try {
            o = parse(args, clock);
        } catch (IllegalArgumentException e) {
            out.println(e.getMessage());
            out.println(usage());
            return 2;
        }
        MazeFactory factory = new MazeFactory();
        String mode = "auto".equals(o.mode) ? (noDisplay ? "text" : "swing") : o.mode;
        switch (mode) {
            case "help" -> {
                out.println(usage());
                return 0;
            }
            case "headless" -> {
                return HeadlessCheck.run(o.seed, factory, out) == 0 ? 0 : 1;
            }
            case "text" -> {
                MazeRun run = new MazeRun(o.seed, o.difficulty, factory);
                BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
                long ms = TextGame.play(run, reader, out, clock::millis);
                if (ms >= 0) {
                    BestScores best = new BestScores(BestScores.defaultFile());
                    boolean nb = best.record(run.shareCode().encode(), run.score(ms), run.stars(ms), run.moves(), ms);
                    out.println(nb ? "New local best saved." : "Local best stands.");
                }
                return 0;
            }
            default -> {
                com.daedalus.mazegame.swing.SwingGame.launch(o.seed, o.difficulty, factory);
                return 0;
            }
        }
    }

    static Options parse(String[] args, Clock clock) {
        Options o = new Options();
        o.seed = DailySeed.today(clock);
        for (int i = 0; i < args.length; i++) {
            String a = args[i];
            switch (a) {
                case "--headless" -> o.mode = "headless";
                case "--text" -> o.mode = "text";
                case "--swing" -> o.mode = "swing";
                case "--help", "-h" -> o.mode = "help";
                case "--daily" -> o.seed = DailySeed.today(clock);
                case "--seed" -> o.seed = parseSeed(value(args, ++i, a));
                case "--difficulty" -> o.difficulty = Difficulty.parse(value(args, ++i, a));
                case "--code" -> {
                    ShareCode sc = ShareCode.parse(value(args, ++i, a));
                    o.seed = sc.seed();
                    o.difficulty = sc.difficulty();
                }
                default -> throw new IllegalArgumentException("Unknown option: " + a);
            }
        }
        return o;
    }

    private static long parseSeed(String s) {
        long v;
        try {
            v = Long.parseLong(s);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("Seed must be a whole number: " + s, e);
        }
        if (v < 0) {
            throw new IllegalArgumentException("Seed must be non-negative: " + s);
        }
        return v;
    }

    private static String value(String[] args, int i, String flag) {
        if (i >= args.length) {
            throw new IllegalArgumentException("Missing value for " + flag);
        }
        return args[i];
    }

    static String usage() {
        return "Usage: java -jar daedalus-maze-game.jar [--headless|--text|--swing] "
                + "[--seed N|--daily|--code LR-H-XXXX] [--difficulty easy|normal|hard|brutal]";
    }
}
