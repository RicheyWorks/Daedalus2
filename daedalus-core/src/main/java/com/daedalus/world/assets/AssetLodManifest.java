// SPDX-License-Identifier: MIT

package com.daedalus.world.assets;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.TreeSet;

/**
 * BBA 1, the asset LOD manifest the Blender pipeline writes (blender-team), and the LOD picker. Ported line for line
 * from the Unreal plugin's {@code DaedalusAssetLodCore.h}; {@code AssetLodParityTest} checks it against
 * {@code engines/unreal/core-test/asset_lod_parity.txt}, which the C++ test writes.
 *
 * <pre>
 * BBA 1
 * asset &lt;id&gt; lod0 &lt;faces&gt; lod1 &lt;faces|-&gt; radius &lt;cm&gt; switch &lt;cm&gt;
 * </pre>
 * All numbers are integers (faces, Unreal centimetres). Manifests are all or nothing: one bad line refuses the file.
 */
public final class AssetLodManifest {

    public static final int VERSION = 1;
    public static final long MAX_ASSETS = 200_000;
    public static final long MAX_FACES = 10_000_000;
    public static final long MAX_CM = 100_000_000;
    public static final int MAX_LINE = 512;

    /** One asset; {@code lod1} is -1 when there is no LOD1. */
    public record Asset(String id, long lod0, long lod1, long radius, long switchCm) {
    }

    /** Assets in file order (instances refer to them by index). */
    public record Manifest(List<Asset> assets) {
        public Manifest {
            assets = List.copyOf(assets);
        }
    }

    /** Either a manifest or the first problem ("line N: why"), never both. */
    public record ParseResult(boolean ok, String error, Manifest manifest) {
    }

    /** One placed copy of an asset, by manifest index, at a camera distance in cm. */
    public record Instance(int asset, long distance) {
    }

    public record BudgetResult(int[] lods, long faces) {
        public BudgetResult {
            lods = lods.clone();
        }

        @Override
        public int[] lods() {
            return lods.clone();
        }

        /** The LODs as a string of 0 and 1, one per instance. */
        public String lodString() {
            StringBuilder s = new StringBuilder();
            for (int l : lods) {
                s.append((char) ('0' + l));
            }
            return s.toString();
        }
    }

    private AssetLodManifest() {
    }

    /** The default switch distance the generator writes: 20 bounding radii, never closer than 5 m. */
    public static long switchFor(long radiusCm) {
        return Math.max(500, radiusCm * 20);
    }

    static boolean token(String s) {
        if (s.isEmpty() || s.length() > 96) {
            return false;
        }
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            boolean ok = c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c >= '0' && c <= '9' || c == '_' || c == '-' || c == '.';
            if (!ok) {
                return false;
            }
        }
        return true;
    }

    /** Plain decimal, no sign, no leading zero, within [lo, hi]; else -1 (all valid values are non-negative). */
    static long integer(String s, long lo, long hi) {
        if (s.isEmpty() || s.length() > 12 || s.length() > 1 && s.charAt(0) == '0') {
            return -1;
        }
        long v = 0;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c < '0' || c > '9') {
                return -1;
            }
            v = v * 10 + (c - '0');
        }
        return v < lo || v > hi ? -1 : v;
    }

    static List<String> words(String line) {
        List<String> w = new ArrayList<>();
        for (String p : line.split(" ")) {
            if (!p.isEmpty()) {
                w.add(p);
            }
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
        if (start < text.length()) {
            lines.add(text.substring(start));
        }
        boolean head = false;
        List<Asset> assets = new ArrayList<>();
        for (int i = 0; i < lines.size(); i++) {
            String l = lines.get(i);
            int n = i + 1;
            if (l.endsWith("\r")) {
                l = l.substring(0, l.length() - 1);
            }
            if (l.length() > MAX_LINE) {
                return fail(n, "line too long");
            }
            if (l.isEmpty() || l.charAt(0) == '#') {
                continue;
            }
            if (l.indexOf('\t') >= 0) {
                return fail(n, "tab");
            }
            List<String> w = words(l);
            if (!head) {
                if (w.size() != 2 || !w.get(0).equals("BBA")) {
                    return fail(n, "expected 'BBA 1'");
                }
                if (!w.get(1).equals("1")) {
                    return fail(n, "unsupported version " + w.get(1));
                }
                head = true;
                continue;
            }
            if (!w.get(0).equals("asset")) {
                return fail(n, "unknown record " + w.get(0));
            }
            if (w.size() != 10 || !w.get(2).equals("lod0") || !w.get(4).equals("lod1") || !w.get(6).equals("radius")
                    || !w.get(8).equals("switch")) {
                return fail(n, "expected 'asset <id> lod0 <n> lod1 <n|-> radius <cm> switch <cm>'");
            }
            String id = w.get(1);
            if (!token(id)) {
                return fail(n, "bad asset id");
            }
            long lod0 = integer(w.get(3), 1, MAX_FACES);
            if (lod0 < 0) {
                return fail(n, "bad lod0");
            }
            long lod1 = -1;
            if (!w.get(5).equals("-")) {
                lod1 = integer(w.get(5), 1, MAX_FACES);
                if (lod1 < 0) {
                    return fail(n, "bad lod1");
                }
            }
            if (lod1 > lod0) {
                return fail(n, "lod1 has more faces than lod0");
            }
            long radius = integer(w.get(7), 1, MAX_CM);
            if (radius < 0) {
                return fail(n, "bad radius");
            }
            long sw = integer(w.get(9), 0, MAX_CM);
            if (sw < 0) {
                return fail(n, "bad switch");
            }
            assets.add(new Asset(id, lod0, lod1, radius, sw));
            if (assets.size() > MAX_ASSETS) {
                return fail(n, "too many assets");
            }
        }
        if (!head) {
            return fail(lines.size() + 1, "empty");
        }
        TreeSet<String> seen = new TreeSet<>();
        TreeSet<String> dup = new TreeSet<>();
        for (Asset a : assets) {
            if (!seen.add(a.id())) {
                dup.add(a.id());
            }
        }
        if (!dup.isEmpty()) {
            return new ParseResult(false, "duplicate asset " + dup.first(), null);
        }
        return new ParseResult(true, "", new Manifest(assets));
    }

    /** Canonical form: assets sorted by id (byte order, as C++ std::string), single spaces, '\n' line ends. */
    public static String write(Manifest m) {
        List<Asset> a = new ArrayList<>(m.assets());
        a.sort(Comparator.comparing(Asset::id));
        StringBuilder s = new StringBuilder("BBA 1\n");
        for (Asset x : a) {
            s.append("asset ").append(x.id()).append(" lod0 ").append(x.lod0()).append(" lod1 ")
                    .append(x.lod1() < 0 ? "-" : Long.toString(x.lod1())).append(" radius ").append(x.radius())
                    .append(" switch ").append(x.switchCm()).append('\n');
        }
        return s.toString();
    }

    /** 1 = draw LOD1: it exists and the camera is at or beyond the switch distance. */
    public static int select(Asset a, long distanceCm) {
        return a.lod1() >= 0 && distanceCm >= a.switchCm() ? 1 : 0;
    }

    public static long faces(Asset a, int lod) {
        return lod == 1 ? a.lod1() : a.lod0();
    }

    /**
     * Distance rule first; then, while over the face budget, drop the farthest LOD0 instances that have a LOD1 (ties:
     * lower asset id, then lower instance index). Can stay over budget when nothing is left to drop.
     */
    public static BudgetResult budget(Manifest m, List<Instance> in, long faceBudget) {
        int[] lods = new int[in.size()];
        long total = 0;
        List<Integer> cand = new ArrayList<>();
        for (int i = 0; i < in.size(); i++) {
            Asset a = m.assets().get(in.get(i).asset());
            lods[i] = select(a, in.get(i).distance());
            total += faces(a, lods[i]);
            if (lods[i] == 0 && a.lod1() >= 0) {
                cand.add(i);
            }
        }
        cand.sort(Comparator.<Integer>comparingLong(i -> -in.get(i).distance())
                .thenComparing(i -> m.assets().get(in.get(i).asset()).id())
                .thenComparingInt(i -> i));
        for (int i : cand) {
            if (total <= faceBudget) {
                break;
            }
            Asset a = m.assets().get(in.get(i).asset());
            total -= a.lod0() - a.lod1();
            lods[i] = 1;
        }
        return new BudgetResult(lods, total);
    }
}
