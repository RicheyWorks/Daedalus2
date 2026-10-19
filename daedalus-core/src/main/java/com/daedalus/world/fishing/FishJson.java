// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Reads a {@code daedalus.rpg-fish/v1} table. Holds a small strict JSON reader (objects, arrays, strings, numbers,
 * booleans, null) so daedalus-core stays JDK-only; it is private to this package on purpose, sized for fish tables.
 */
final class FishJson {

    private final String s;
    private int i;

    private FishJson(String s) {
        this.s = s;
    }

    /** Parses a fish table document. */
    static FishTable table(String json) {
        if (json == null) {
            throw new IllegalArgumentException("fish json: no text");
        }
        Map<?, ?> root = map(parse(json), "document");
        Object realm = root.get("realm");
        String realmName = realm instanceof String r ? r : "unknown";
        List<FishSpecies> fish = new ArrayList<>();
        for (Object o : list(root.get("fish"), "fish")) {
            fish.add(species(map(o, "fish entry")));
        }
        return new FishTable(realmName, fish);
    }

    private static FishSpecies species(Map<?, ?> f) {
        String name = text(f, "name", null);
        return new FishSpecies(name, Rarity.parse(text(f, "rarity", null)), number(f, "weight", Double.NaN, name),
                number(f, "night_weight", 0, name), number(f, "window_s", Double.NaN, name), text(f, "effect", ""),
                (int) Math.round(number(f, "price", 0, name)), text(f, "note", ""), words(f, "seasons"),
                words(f, "spots"), Boolean.TRUE.equals(f.get("dusk_only")));
    }

    private static String text(Map<?, ?> f, String key, String fallback) {
        Object v = f.get(key);
        if (v == null) {
            if (fallback == null) {
                throw new IllegalArgumentException("fish json: '" + key + "' is missing");
            }
            return fallback;
        }
        if (!(v instanceof String str)) {
            throw new IllegalArgumentException("fish json: '" + key + "' must be text");
        }
        return str;
    }

    private static double number(Map<?, ?> f, String key, double fallback, String who) {
        Object v = f.get(key);
        if (v == null) {
            if (Double.isNaN(fallback)) {
                throw new IllegalArgumentException("fish json: " + who + " has no '" + key + "'");
            }
            return fallback;
        }
        if (!(v instanceof Double d)) {
            throw new IllegalArgumentException("fish json: " + who + " '" + key + "' must be a number");
        }
        return d;
    }

    private static List<String> words(Map<?, ?> f, String key) {
        List<String> out = new ArrayList<>();
        Object v = f.get(key);
        if (v != null) {
            for (Object o : list(v, key)) {
                if (!(o instanceof String w)) {
                    throw new IllegalArgumentException("fish json: '" + key + "' must hold text");
                }
                out.add(w);
            }
        }
        return out;
    }

    private static Map<?, ?> map(Object o, String what) {
        if (!(o instanceof Map<?, ?> m)) {
            throw new IllegalArgumentException("fish json: " + what + " must be an object");
        }
        return m;
    }

    private static List<?> list(Object o, String what) {
        if (!(o instanceof List<?> l)) {
            throw new IllegalArgumentException("fish json: '" + what + "' must be a list");
        }
        return l;
    }

    /** Parses {@code text} into Map, List, String, Double, Boolean or null. */
    static Object parse(String text) {
        FishJson p = new FishJson(text);
        p.ws();
        Object v = p.value();
        p.ws();
        if (p.i != p.s.length()) {
            throw p.err("trailing data");
        }
        return v;
    }

    private IllegalArgumentException err(String m) {
        return new IllegalArgumentException("fish json: " + m + " at " + i);
    }

    private void ws() {
        while (i < s.length() && Character.isWhitespace(s.charAt(i))) {
            i++;
        }
    }

    private char peek() {
        if (i >= s.length()) {
            throw err("unexpected end");
        }
        return s.charAt(i);
    }

    private void expect(char c) {
        if (peek() != c) {
            throw err("expected '" + c + "'");
        }
        i++;
    }

    private Object value() {
        char c = peek();
        switch (c) {
            case '{':
                return object();
            case '[':
                return array();
            case '"':
                return string();
            case 't':
                return word("true", Boolean.TRUE);
            case 'f':
                return word("false", Boolean.FALSE);
            case 'n':
                return word("null", null);
            default:
                return number();
        }
    }

    private Map<String, Object> object() {
        expect('{');
        Map<String, Object> m = new LinkedHashMap<>();
        ws();
        if (peek() == '}') {
            i++;
            return m;
        }
        while (true) {
            ws();
            String k = string();
            ws();
            expect(':');
            ws();
            m.put(k, value());
            ws();
            if (peek() == ',') {
                i++;
                continue;
            }
            expect('}');
            return m;
        }
    }

    private List<Object> array() {
        expect('[');
        List<Object> l = new ArrayList<>();
        ws();
        if (peek() == ']') {
            i++;
            return l;
        }
        while (true) {
            ws();
            l.add(value());
            ws();
            if (peek() == ',') {
                i++;
                continue;
            }
            expect(']');
            return l;
        }
    }

    private String string() {
        expect('"');
        StringBuilder b = new StringBuilder();
        while (true) {
            char c = peek();
            i++;
            if (c == '"') {
                return b.toString();
            }
            if (c != '\\') {
                b.append(c);
                continue;
            }
            char e = peek();
            i++;
            switch (e) {
                case '"', '\\', '/' -> b.append(e);
                case 'n' -> b.append('\n');
                case 't' -> b.append('\t');
                case 'r' -> b.append('\r');
                case 'b' -> b.append('\b');
                case 'f' -> b.append('\f');
                case 'u' -> {
                    if (i + 4 > s.length()) {
                        throw err("short unicode escape");
                    }
                    try {
                        b.append((char) Integer.parseInt(s.substring(i, i + 4), 16));
                    } catch (NumberFormatException ex) {
                        throw err("bad unicode escape");
                    }
                    i += 4;
                }
                default -> throw err("bad escape");
            }
        }
    }

    private Object word(String w, Object v) {
        if (!s.startsWith(w, i)) {
            throw err("bad literal");
        }
        i += w.length();
        return v;
    }

    private Double number() {
        int start = i;
        while (i < s.length() && "+-0123456789.eE".indexOf(s.charAt(i)) >= 0) {
            i++;
        }
        if (start == i) {
            throw err("unexpected character");
        }
        try {
            return Double.valueOf(s.substring(start, i));
        } catch (NumberFormatException ex) {
            throw err("bad number");
        }
    }
}
