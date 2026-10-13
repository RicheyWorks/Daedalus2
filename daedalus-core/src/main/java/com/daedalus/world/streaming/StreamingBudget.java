// SPDX-License-Identifier: MIT

package com.daedalus.world.streaming;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * DSB 1, the island streaming budget manifest, and the resident-set picker (disk-saver). Ported line for line from
 * the Unreal plugin's {@code DaedalusStreamingBudgetCore.h}; {@code StreamingBudgetParityTest} checks it against
 * {@code engines/unreal/core-test/streaming_budget_parity.txt}, which the C++ test writes.
 *
 * <pre>
 * DSB 1
 * island &lt;id&gt; x &lt;cm&gt; y &lt;cm&gt; ram &lt;kib&gt; disk &lt;kib&gt;
 * </pre>
 * Integers only. All or nothing: one bad line refuses the file. An island is wanted when it is within the load
 * radius, or already resident and still within the (larger) unload radius, so islands on the edge do not thrash.
 * Wanted islands are taken nearest first (ties by manifest index) while their RAM fits the budget; ones that do not
 * fit are skipped, never partly loaded. Java stays the authority for which islands exist; the plugin runs the same
 * pick every frame without a network round trip.
 */
public final class StreamingBudget {

    public static final int VERSION = 1;
    public static final int MAX_ISLANDS = 20_000;
    public static final long MAX_CM = 1_000_000_000L;
    public static final long MAX_KIB = 100_000_000L;
    public static final int MAX_LINE = 512;

    /** One island: centre in Unreal cm, resident RAM and on-disk size in KiB. */
    public record Island(String id, long x, long y, long ram, long disk) {
    }

    /** Islands in file order (picks refer to them by index). */
    public record Manifest(List<Island> islands) {
        public Manifest {
            islands = List.copyOf(islands);
        }
    }

    /** Either a manifest or the first problem ("line N: why"), never both. */
    public record ParseResult(boolean ok, String error, Manifest manifest) {
    }

    /** Which islands are resident (one flag per manifest index) and what they cost. */
    public record PickResult(boolean[] resident, long ram, long disk, int count) {
        public PickResult {
            resident = resident.clone();
        }

        @Override
        public boolean[] resident() {
            return resident.clone();
        }

        public String bits() {
            return StreamingBudget.bits(resident);
        }
    }

    private StreamingBudget() {
    }

    static boolean goodId(String s) {
        if (s.isEmpty() || s.length() > 64) {
            return false;
        }
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            boolean ok = c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c >= '0' && c <= '9' || c == '_';
            if (!ok) {
                return false;
            }
        }
        return true;
    }

    /** Plain decimal (optional '-' when allowed, no "-0", no leading zero) within [lo, hi]; null otherwise. */
    static Long integer(String s, boolean allowNeg, long lo, long hi) {
        int i = 0;
        boolean neg = false;
        if (allowNeg && !s.isEmpty() && s.charAt(0) == '-') {
            neg = true;
            i = 1;
        }
        if (i >= s.length() || s.length() - i > 12) {
            return null;
        }
        if (s.charAt(i) == '0' && s.length() - i > 1) {
            return null;
        }
        if (neg && s.length() - i == 1 && s.charAt(i) == '0') {
            return null;
        }
        long v = 0;
        for (; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c < '0' || c > '9') {
                return null;
            }
            v = v * 10 + (c - '0');
        }
        v = neg ? -v : v;
        return v < lo || v > hi ? null : v;
    }

    static List<String> words(String line) {
        List<String> w = new ArrayList<>();
        StringBuilder cur = new StringBuilder();
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (c == ' ' || c == '\t') {
                if (cur.length() > 0) {
                    w.add(cur.toString());
                    cur.setLength(0);
                }
            } else {
                cur.append(c);
            }
        }
        if (cur.length() > 0) {
            w.add(cur.toString());
        }
        return w;
    }

    private static ParseResult fail(int n, String why) {
        return new ParseResult(false, "line " + n + ": " + why, null);
    }

    public static ParseResult parse(String text) {
        List<String> lines = new ArrayList<>();
        int start = 0;
        for (int i = 0; i < text.length(); i++) {
            if (text.charAt(i) == '\n') {
                lines.add(text.substring(start, i));
                start = i + 1;
            }
        }
        lines.add(text.substring(start));
        boolean header = false;
        Set<String> seen = new HashSet<>();
        List<Island> out = new ArrayList<>();
        for (int n = 1; n <= lines.size(); n++) {
            String l = lines.get(n - 1);
            if (!l.isEmpty() && l.charAt(l.length() - 1) == '\r') {
                l = l.substring(0, l.length() - 1);
            }
            if (l.length() > MAX_LINE) {
                return fail(n, "line too long");
            }
            List<String> t = words(l);
            if (t.isEmpty() || t.get(0).charAt(0) == '#') {
                continue;
            }
            if (!header) {
                if (t.size() == 2 && t.get(0).equals("DSB")) {
                    if (!t.get(1).equals("1")) {
                        return fail(n, "unsupported version " + t.get(1));
                    }
                    header = true;
                    continue;
                }
                return fail(n, "expected 'DSB 1'");
            }
            if (!t.get(0).equals("island")) {
                return fail(n, "unknown record " + t.get(0));
            }
            if (t.size() != 10 || !t.get(2).equals("x") || !t.get(4).equals("y") || !t.get(6).equals("ram")
                    || !t.get(8).equals("disk")) {
                return fail(n, "expected 'island <id> x <cm> y <cm> ram <kib> disk <kib>'");
            }
            String id = t.get(1);
            if (!goodId(id)) {
                return fail(n, "bad island id");
            }
            if (!seen.add(id)) {
                return fail(n, "duplicate island " + id);
            }
            Long x = integer(t.get(3), true, -MAX_CM, MAX_CM);
            if (x == null) {
                return fail(n, "bad x");
            }
            Long y = integer(t.get(5), true, -MAX_CM, MAX_CM);
            if (y == null) {
                return fail(n, "bad y");
            }
            Long ram = integer(t.get(7), false, 1, MAX_KIB);
            if (ram == null) {
                return fail(n, "bad ram");
            }
            Long disk = integer(t.get(9), false, 1, MAX_KIB);
            if (disk == null) {
                return fail(n, "bad disk");
            }
            if (out.size() >= MAX_ISLANDS) {
                return fail(n, "too many islands");
            }
            out.add(new Island(id, x, y, ram, disk));
        }
        if (!header) {
            return fail(1, "empty");
        }
        return new ParseResult(true, "", new Manifest(out));
    }

    /** Canonical form: header, then islands sorted by id, single spaces, LF endings. */
    public static String write(Manifest m) {
        List<Island> p = new ArrayList<>(m.islands());
        p.sort(Comparator.comparing(Island::id));
        StringBuilder o = new StringBuilder("DSB 1\n");
        for (Island i : p) {
            o.append("island ").append(i.id()).append(" x ").append(i.x()).append(" y ").append(i.y())
                    .append(" ram ").append(i.ram()).append(" disk ").append(i.disk()).append('\n');
        }
        return o.toString();
    }

    static long dist2(Island i, long vx, long vy) {
        long dx = i.x() - vx;
        long dy = i.y() - vy;
        return dx * dx + dy * dy;
    }

    /** Viewer within +-MAX_CM, radii within 0..MAX_CM; an unload radius below the load radius acts as the load radius. */
    public static PickResult pick(Manifest m, long vx, long vy, long loadCm, long unloadCm, long ramBudget,
            boolean[] wasResident) {
        long load2 = loadCm * loadCm;
        long u = Math.max(loadCm, unloadCm);
        long unload2 = u * u;
        List<long[]> want = new ArrayList<>();
        List<Island> is = m.islands();
        for (int i = 0; i < is.size(); i++) {
            long d = dist2(is.get(i), vx, vy);
            boolean was = wasResident != null && i < wasResident.length && wasResident[i];
            if (d <= load2 || was && d <= unload2) {
                want.add(new long[] {d, i});
            }
        }
        want.sort(Comparator.<long[]>comparingLong(w -> w[0]).thenComparingLong(w -> w[1]));
        boolean[] res = new boolean[is.size()];
        long ram = 0;
        long disk = 0;
        int count = 0;
        for (long[] w : want) {
            Island i = is.get((int) w[1]);
            if (i.ram() > ramBudget - ram) {
                continue;
            }
            res[(int) w[1]] = true;
            ram += i.ram();
            disk += i.disk();
            count++;
        }
        return new PickResult(res, ram, disk, count);
    }

    /** Flags as a string of 0 and 1. */
    public static String bits(boolean[] b) {
        StringBuilder s = new StringBuilder();
        for (boolean v : b) {
            s.append(v ? '1' : '0');
        }
        return s.toString();
    }
}
