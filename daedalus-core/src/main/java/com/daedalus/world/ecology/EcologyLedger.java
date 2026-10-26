// SPDX-License-Identifier: MIT

package com.daedalus.world.ecology;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * The live ecology as text lines, so it survives a restart (ADR-023). The island habitats are not
 * stored — they regrow from each island's seed — only what lives: the day counter, the clock epoch
 * day 0 began at, every island's abundances and every ark's hold.
 *
 * <pre>
 * epoch 1760000000000
 * day 42
 * isle 0 cat=11.25 moss=380.5
 * hold ark-0 red_panda=2.0
 * </pre>
 *
 * Counts are written with {@link Double#toString}, which round-trips exactly, so a restored world
 * steps on from precisely where it stopped.
 */
public final class EcologyLedger {

    private EcologyLedger() {
    }

    /** What the ledger holds. Maps are sorted; the caller owns them. */
    public record State(long epoch, long day, TreeMap<Integer, Map<String, Double>> isles,
                        TreeMap<String, Map<String, Double>> holds) {

        /** Defensive, sorted copies all the way down: a state read from disk is nobody's live map. */
        public State {
            TreeMap<Integer, Map<String, Double>> i = new TreeMap<>();
            if (isles != null) {
                isles.forEach((k, v) -> i.put(k, new TreeMap<>(v)));
            }
            TreeMap<String, Map<String, Double>> h = new TreeMap<>();
            if (holds != null) {
                holds.forEach((k, v) -> h.put(k, new TreeMap<>(v)));
            }
            isles = i;
            holds = h;
        }

        @Override
        public TreeMap<Integer, Map<String, Double>> isles() {
            TreeMap<Integer, Map<String, Double>> out = new TreeMap<>();
            isles.forEach((k, v) -> out.put(k, new TreeMap<>(v)));
            return out;
        }

        @Override
        public TreeMap<String, Map<String, Double>> holds() {
            TreeMap<String, Map<String, Double>> out = new TreeMap<>();
            holds.forEach((k, v) -> out.put(k, new TreeMap<>(v)));
            return out;
        }
    }

    public static List<String> toLines(long epoch, Ecosystem eco, Map<String, Hold> holds) {
        List<String> out = new ArrayList<>();
        out.add("# Daedalus ecology (ADR-023): epoch, day, isle <slot> key=n..., hold <arkId> key=n...");
        out.add("epoch " + epoch);
        out.add("day " + eco.day());
        for (Map.Entry<Integer, Community> e : eco.communities().entrySet()) {
            out.add(row("isle " + e.getKey(), e.getValue().abundance()));
        }
        for (Map.Entry<String, Hold> e : new TreeMap<>(holds).entrySet()) {
            out.add(row("hold " + e.getKey(), e.getValue().cargo()));
        }
        return out;
    }

    private static String row(String head, Map<String, Double> counts) {
        StringBuilder sb = new StringBuilder(head);
        for (Map.Entry<String, Double> c : new TreeMap<>(counts).entrySet()) {
            sb.append(' ').append(c.getKey()).append('=').append(Double.toString(c.getValue()));
        }
        return sb.toString();
    }

    public static State fromLines(List<String> lines) {
        long epoch = 0;
        long day = 0;
        TreeMap<Integer, Map<String, Double>> isles = new TreeMap<>();
        TreeMap<String, Map<String, Double>> holds = new TreeMap<>();
        for (String line : lines) {
            String t = line.trim();
            if (t.isEmpty() || t.startsWith("#")) {
                continue;
            }
            String[] f = t.split("\\s+");
            switch (f[0]) {
                case "epoch" -> epoch = Long.parseLong(need(f, 2, t)[1]);
                case "day" -> day = Long.parseLong(need(f, 2, t)[1]);
                case "isle" -> isles.put(Integer.parseInt(need(f, 2, t)[1]), counts(f, t));
                case "hold" -> holds.put(need(f, 2, t)[1], counts(f, t));
                default -> throw new IllegalArgumentException("Bad ecology row: " + t);
            }
        }
        return new State(epoch, day, isles, holds);
    }

    private static String[] need(String[] f, int min, String line) {
        if (f.length < min) {
            throw new IllegalArgumentException("Bad ecology row: " + line);
        }
        return f;
    }

    private static Map<String, Double> counts(String[] f, String line) {
        Map<String, Double> out = new TreeMap<>();
        for (int i = 2; i < f.length; i++) {
            int eq = f[i].indexOf('=');
            if (eq <= 0) {
                throw new IllegalArgumentException("Bad ecology row: " + line);
            }
            double n = Double.parseDouble(f[i].substring(eq + 1));
            if (!(n > 0) || Double.isInfinite(n)) {
                throw new IllegalArgumentException("Bad ecology count in: " + line);
            }
            out.put(f[i].substring(0, eq), n);
        }
        return out;
    }
}
