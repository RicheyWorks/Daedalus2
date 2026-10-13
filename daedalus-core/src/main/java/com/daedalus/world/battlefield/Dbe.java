// SPDX-License-Identifier: MIT

package com.daedalus.world.battlefield;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * DBE 1, Daedalus Battlefield Ecology: the plain-text contract between the Java ecology and Unreal (ADR-061), in the
 * same style as DTO 1 / DTE 1 (ADR-060). Specs are all or nothing: a bad line refuses the whole spec with its line
 * number and the reason.
 *
 * <pre>
 * DBE 1                                   snapshot, Java -> Unreal (and save files)
 * grid &lt;w&gt; &lt;h&gt; &lt;cellCm&gt; &lt;originX&gt; &lt;originY&gt; &lt;seed&gt;
 * tick &lt;n&gt;
 * row &lt;j&gt; &lt;w vegetation codes . m s p o w&gt;       exactly h rows, j = 0..h-1 in order
 * fire &lt;i&gt; &lt;j&gt; &lt;ticksLeft&gt;                  zero or more, after the rows
 *
 * DBE-E 1                                 combat events, Unreal -> Java
 * event &lt;IGNITE|BLAST|DOUSE&gt; &lt;x&gt; &lt;y&gt; &lt;z&gt; &lt;radiusCm&gt;   at most 256
 * </pre>
 */
public final class Dbe {

    public static final int MAX_EVENTS = 256;

    public record Event(BattlefieldEcology.EventKind kind, double x, double y, double z, double radiusCm) {}

    private Dbe() {}

    public static String write(BattlefieldEcology e) {
        StringBuilder b = new StringBuilder(e.width() * e.height() + 128);
        b.append("DBE 1\n");
        b.append(String.format(Locale.ROOT, "grid %d %d %s %s %s %d%n", e.width(), e.height(), num(e.cellCm()), num(e.originX()), num(e.originY()), e.seed()));
        b.append("tick ").append(e.tickCount()).append('\n');
        for (int j = 0; j < e.height(); j++) {
            b.append("row ").append(j).append(' ');
            for (int i = 0; i < e.width(); i++) {
                b.append(e.vegetation(i, j).code());
            }
            b.append('\n');
        }
        for (int j = 0; j < e.height(); j++) {
            for (int i = 0; i < e.width(); i++) {
                if (e.burning(i, j) > 0) {
                    b.append("fire ").append(i).append(' ').append(j).append(' ').append(e.burning(i, j)).append('\n');
                }
            }
        }
        return b.toString().replace("\r\n", "\n");
    }

    public static BattlefieldEcology read(String spec) {
        String[] lines = spec.replace("\r\n", "\n").split("\n", -1);
        int n = lines.length;
        while (n > 0 && lines[n - 1].isBlank()) {
            n--;
        }
        if (n < 3 || !lines[0].equals("DBE 1")) {
            throw bad(1, "first line must be 'DBE 1'");
        }
        String[] g = fields(lines[1], 2, "grid", 7);
        int w = intOf(g[1], 2, "width");
        int h = intOf(g[2], 2, "height");
        BattlefieldEcology e;
        try {
            e = new BattlefieldEcology(w, h, dbl(g[3], 2, "cellCm"), dbl(g[4], 2, "originX"), dbl(g[5], 2, "originY"), longOf(g[6], 2, "seed"));
        } catch (IllegalArgumentException ex) {
            throw bad(2, ex.getMessage());
        }
        String[] t = fields(lines[2], 3, "tick", 2);
        long tick = longOf(t[1], 3, "tick");
        if (tick < 0) {
            throw bad(3, "tick must be >= 0");
        }
        if (n < 3 + h) {
            throw bad(n + 1, "expected " + h + " row lines");
        }
        for (int j = 0; j < h; j++) {
            int ln = 4 + j;
            String[] r = fields(lines[3 + j], ln, "row", 3);
            if (intOf(r[1], ln, "row index") != j) {
                throw bad(ln, "rows must be in order, expected row " + j);
            }
            if (r[2].length() != w) {
                throw bad(ln, "row has " + r[2].length() + " cells, grid width is " + w);
            }
            for (int i = 0; i < w; i++) {
                try {
                    e.restore(tick, i, j, Vegetation.ofCode(r[2].charAt(i)), 0);
                } catch (IllegalArgumentException ex) {
                    throw bad(ln, ex.getMessage());
                }
            }
        }
        for (int k = 3 + h; k < n; k++) {
            int ln = k + 1;
            String[] f = fields(lines[k], ln, "fire", 4);
            int i = intOf(f[1], ln, "i");
            int j = intOf(f[2], ln, "j");
            int left = intOf(f[3], ln, "ticks");
            if (i < 0 || j < 0 || i >= w || j >= h) {
                throw bad(ln, "fire cell outside grid");
            }
            if (left < 1 || left > 64) {
                throw bad(ln, "fire ticks must be 1..64");
            }
            if (e.vegetation(i, j).flammability() <= 0) {
                throw bad(ln, "cell " + i + "," + j + " (" + e.vegetation(i, j) + ") cannot burn");
            }
            e.restore(tick, i, j, e.vegetation(i, j), left);
        }
        return e;
    }

    public static List<Event> readEvents(String spec) {
        String[] lines = spec.replace("\r\n", "\n").split("\n", -1);
        int n = lines.length;
        while (n > 0 && lines[n - 1].isBlank()) {
            n--;
        }
        if (n < 1 || !lines[0].equals("DBE-E 1")) {
            throw bad(1, "first line must be 'DBE-E 1'");
        }
        if (n - 1 > MAX_EVENTS) {
            throw bad(MAX_EVENTS + 2, "at most " + MAX_EVENTS + " events");
        }
        List<Event> out = new ArrayList<>();
        for (int k = 1; k < n; k++) {
            int ln = k + 1;
            String[] f = fields(lines[k], ln, "event", 6);
            BattlefieldEcology.EventKind kind;
            try {
                kind = BattlefieldEcology.EventKind.valueOf(f[1]);
            } catch (IllegalArgumentException ex) {
                throw bad(ln, "unknown event '" + f[1] + "'");
            }
            double r = dbl(f[5], ln, "radius");
            if (r < 0 || r > 100_000) {
                throw bad(ln, "radius must be 0..100000 cm");
            }
            out.add(new Event(kind, dbl(f[2], ln, "x"), dbl(f[3], ln, "y"), dbl(f[4], ln, "z"), r));
        }
        return List.copyOf(out);
    }

    /** Applies DBE-E events in order; returns the cells changed. */
    public static int apply(BattlefieldEcology e, List<Event> events) {
        int c = 0;
        for (Event ev : events) {
            c += e.apply(ev.kind(), ev.x(), ev.y(), ev.radiusCm());
        }
        return c;
    }

    private static String[] fields(String line, int ln, String head, int count) {
        String[] f = line.trim().split(" +");
        if (!f[0].equals(head)) {
            throw bad(ln, "expected '" + head + "' line");
        }
        if (f.length != count) {
            throw bad(ln, "'" + head + "' needs " + (count - 1) + " values");
        }
        return f;
    }

    private static int intOf(String s, int ln, String what) {
        try {
            return Integer.parseInt(s);
        } catch (NumberFormatException ex) {
            throw bad(ln, what + " is not an integer: " + s);
        }
    }

    private static long longOf(String s, int ln, String what) {
        try {
            return Long.parseLong(s);
        } catch (NumberFormatException ex) {
            throw bad(ln, what + " is not an integer: " + s);
        }
    }

    private static double dbl(String s, int ln, String what) {
        try {
            double v = Double.parseDouble(s);
            if (!Double.isFinite(v)) {
                throw bad(ln, what + " must be finite");
            }
            return v;
        } catch (NumberFormatException ex) {
            throw bad(ln, what + " is not a number: " + s);
        }
    }

    private static String num(double v) {
        return v == Math.rint(v) && Math.abs(v) < 1e15 ? Long.toString((long) v) : Double.toString(v);
    }

    private static IllegalArgumentException bad(int line, String why) {
        return new IllegalArgumentException("DBE line " + line + ": " + why);
    }
}
