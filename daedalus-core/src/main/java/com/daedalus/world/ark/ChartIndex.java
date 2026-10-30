// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;

/**
 * G252 The Chart Index: the ark's chart room files every port name in a trie. Logging a visit
 * adds the port (names are lower-cased); {@link #countPrefix} says how many ports start with a
 * typed prefix and {@link #suggest} autocompletes the top-k most-visited of them, ties broken
 * alphabetically. Prefix lookups cost O(prefix length) before collecting matches.
 */
public final class ChartIndex {

    public static final String QUEST_ID = "q_chart_index";

    /** A suggested port and how often the ark has called there. */
    public record Port(String name, long visits) { }

    private static final class Node {
        private final Map<Character, Node> next = new TreeMap<>();
        private long visits;
        private boolean port;
        private int below;
    }

    private final Node root = new Node();

    /** Logs {@code visits} calls at {@code name}, filing it if new. */
    public void visit(String name, long visits) {
        String key = normalize(name);
        if (visits < 0) {
            throw new IllegalArgumentException("visits < 0");
        }
        boolean fresh = !contains(key);
        Node n = root;
        if (fresh) {
            n.below++;
        }
        for (int i = 0; i < key.length(); i++) {
            n = n.next.computeIfAbsent(key.charAt(i), c -> new Node());
            if (fresh) {
                n.below++;
            }
        }
        n.port = true;
        n.visits += visits;
    }

    public boolean contains(String name) {
        Node n = find(normalize(name));
        return n != null && n.port;
    }

    public long visits(String name) {
        Node n = find(normalize(name));
        return n != null && n.port ? n.visits : 0;
    }

    public int size() {
        return root.below;
    }

    public int countPrefix(String prefix) {
        Node n = find(prefix.toLowerCase(Locale.ROOT));
        return n == null ? 0 : n.below;
    }

    /** Top {@code k} ports starting with {@code prefix}: most visits first, then alphabetical. */
    public List<Port> suggest(String prefix, int k) {
        if (k < 0) {
            throw new IllegalArgumentException("k < 0");
        }
        String p = prefix.toLowerCase(Locale.ROOT);
        Node n = find(p);
        List<Port> all = new ArrayList<>();
        if (n != null) {
            collect(n, new StringBuilder(p), all);
        }
        all.sort(Comparator.comparingLong(Port::visits).reversed().thenComparing(Port::name));
        return List.copyOf(all.subList(0, Math.min(k, all.size())));
    }

    private static void collect(Node n, StringBuilder sb, List<Port> out) {
        if (n.port) {
            out.add(new Port(sb.toString(), n.visits));
        }
        for (Map.Entry<Character, Node> e : n.next.entrySet()) {
            sb.append(e.getKey().charValue());
            collect(e.getValue(), sb, out);
            sb.setLength(sb.length() - 1);
        }
    }

    private Node find(String key) {
        Node n = root;
        for (int i = 0; i < key.length() && n != null; i++) {
            n = n.next.get(key.charAt(i));
        }
        return n;
    }

    private static String normalize(String name) {
        if (name == null || name.isBlank()) {
            throw new IllegalArgumentException("blank port name");
        }
        return name.toLowerCase(Locale.ROOT);
    }

    /** Quest q_chart_index: the navigator's top-k list for the prefix must match the index. */
    public static boolean quest(ChartIndex index, String prefix, int k, List<String> answer) {
        List<String> truth = index.suggest(prefix, k).stream().map(Port::name).toList();
        return truth.equals(answer);
    }
}
