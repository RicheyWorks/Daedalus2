// SPDX-License-Identifier: MIT

package com.daedalus.mazegame;

import com.daedalus.model.Direction;
import com.daedalus.model.Point;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.PrintStream;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.function.LongSupplier;

/** Terminal mode: ASCII board, one command per line (w/a/s/d moves, h hint, q quit). */
public final class TextGame {

    private TextGame() {
    }

    /** ASCII render: '@' runner, 'X' exit, '.' hint trail, '?' fog. */
    public static String render(MazeRun run, List<Point> trail) {
        Set<Point> marks = new HashSet<>(trail);
        int n = run.size();
        StringBuilder sb = new StringBuilder();
        sb.append('+').append("--+".repeat(n)).append('\n');
        for (int r = 0; r < n; r++) {
            StringBuilder row = new StringBuilder("|");
            StringBuilder floor = new StringBuilder("+");
            for (int c = 0; c < n; c++) {
                boolean vis = run.isVisible(r, c);
                Point p = new Point(r, c);
                String body;
                if (!vis) {
                    body = "??";
                } else if (p.equals(run.position())) {
                    body = "@@";
                } else if (p.equals(run.exit())) {
                    body = "XX";
                } else if (marks.contains(p)) {
                    body = "..";
                } else {
                    body = "  ";
                }
                row.append(body).append(vis && run.isOpen(r, c, Direction.EAST) ? ' ' : '|');
                floor.append(vis && run.isOpen(r, c, Direction.SOUTH) ? "  " : "--").append('+');
            }
            sb.append(row).append('\n').append(floor).append('\n');
        }
        return sb.toString();
    }

    public static String hud(MazeRun run, long millis) {
        return String.format(Locale.ROOT, "%s  %s %dx%d  moves %d  par %d  time %.1fs/%.1fs  hints %d",
                run.shareCode(), run.difficulty(), run.size(), run.size(), run.moves(), run.par(),
                millis / 1000.0, Scoring.parMillis(run.par()) / 1000.0, run.hints());
    }

    /** Plays until a win, 'q' or end of input. Returns the elapsed millis at the finish, or -1 if unfinished. */
    public static long play(MazeRun run, BufferedReader in, PrintStream out, LongSupplier clockMillis) throws IOException {
        long t0 = clockMillis.getAsLong();
        List<Point> trail = List.of();
        out.println(render(run, trail));
        out.println(hud(run, 0));
        String line;
        while ((line = in.readLine()) != null) {
            for (char ch : line.trim().toLowerCase(Locale.ROOT).toCharArray()) {
                switch (ch) {
                    case 'w' -> run.move(Direction.NORTH);
                    case 's' -> run.move(Direction.SOUTH);
                    case 'a' -> run.move(Direction.WEST);
                    case 'd' -> run.move(Direction.EAST);
                    case 'h' -> trail = run.hint(5);
                    case 'q' -> {
                        out.println("Quit. Share code " + run.shareCode());
                        return -1;
                    }
                    default -> { }
                }
                if (run.isWon()) {
                    long ms = clockMillis.getAsLong() - t0;
                    out.println(render(run, List.of()));
                    out.printf(Locale.ROOT, "ESCAPED! %d star(s), score %d. %s%n", run.stars(ms), run.score(ms), hud(run, ms));
                    return ms;
                }
            }
            out.println(render(run, trail));
            out.println(hud(run, clockMillis.getAsLong() - t0));
        }
        return -1;
    }
}
