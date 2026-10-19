// SPDX-License-Identifier: MIT

package com.daedalus.world.activity.learned;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Strict JSON for the activity envelope and the pond catalog. JDK only. Objects, arrays, strings, numbers, booleans, null. */
final class ActivityJson {
    private final String s;
    private int i;

    private ActivityJson(String s) {
        this.s = s;
    }

    static Object parse(String text) {
        if (text == null) {
            throw new IllegalArgumentException("json is required");
        }
        if (!text.isEmpty() && text.charAt(0) == '\uFEFF') {
            throw new IllegalArgumentException("json starts with a BOM");
        }
        ActivityJson p = new ActivityJson(text);
        p.ws();
        Object v = p.value();
        p.ws();
        if (p.i != p.s.length()) {
            throw p.err("trailing data");
        }
        return v;
    }

    /** Canonical string escape used by {@link ActivityResult#serialize()}. */
    static String quote(String value) {
        StringBuilder b = new StringBuilder(value.length() + 2);
        b.append('"');
        for (int n = 0; n < value.length(); n++) {
            char c = value.charAt(n);
            switch (c) {
                case '"':
                    b.append("\\\"");
                    break;
                case '\\':
                    b.append("\\\\");
                    break;
                case '\b':
                    b.append("\\b");
                    break;
                case '\f':
                    b.append("\\f");
                    break;
                case '\n':
                    b.append("\\n");
                    break;
                case '\r':
                    b.append("\\r");
                    break;
                case '\t':
                    b.append("\\t");
                    break;
                default:
                    if (c < 0x20) {
                        b.append(String.format("\\u%04x", (int) c));
                    } else {
                        b.append(c);
                    }
                    break;
            }
        }
        b.append('"');
        return b.toString();
    }

    private IllegalArgumentException err(String message) {
        return new IllegalArgumentException(message + " at " + i);
    }

    private void ws() {
        while (i < s.length()) {
            char c = s.charAt(i);
            if (c != ' ' && c != '\n' && c != '\r' && c != '\t') {
                return;
            }
            i++;
        }
    }

    private boolean peek(char c) {
        return i < s.length() && s.charAt(i) == c;
    }

    private void expect(char c) {
        if (!peek(c)) {
            throw err("expected '" + c + "'");
        }
        i++;
    }

    private Object value() {
        if (i >= s.length()) {
            throw err("unexpected end");
        }
        char c = s.charAt(i);
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

    private Object word(String w, Object v) {
        if (!s.startsWith(w, i)) {
            throw err("bad literal");
        }
        i += w.length();
        return v;
    }

    private Map<String, Object> object() {
        expect('{');
        Map<String, Object> m = new LinkedHashMap<>();
        ws();
        if (peek('}')) {
            i++;
            return m;
        }
        while (true) {
            ws();
            String k = string();
            if (m.containsKey(k)) {
                throw err("duplicate key " + k);
            }
            ws();
            expect(':');
            ws();
            m.put(k, value());
            ws();
            if (peek(',')) {
                i++;
                ws();
                if (peek('}')) {
                    throw err("trailing comma");
                }
                continue;
            }
            expect('}');
            return m;
        }
    }

    private List<Object> array() {
        expect('[');
        List<Object> list = new ArrayList<>();
        ws();
        if (peek(']')) {
            i++;
            return list;
        }
        while (true) {
            ws();
            list.add(value());
            ws();
            if (peek(',')) {
                i++;
                ws();
                if (peek(']')) {
                    throw err("trailing comma");
                }
                continue;
            }
            expect(']');
            return list;
        }
    }

    private String string() {
        expect('"');
        StringBuilder b = new StringBuilder();
        while (true) {
            if (i >= s.length()) {
                throw err("unterminated string");
            }
            char c = s.charAt(i++);
            if (c == '"') {
                return b.toString();
            }
            if (c < 0x20) {
                throw err("raw control in string");
            }
            if (c != '\\') {
                if (Character.isSurrogate(c)) {
                    throw err("lone surrogate");
                }
                b.append(c);
                continue;
            }
            if (i >= s.length()) {
                throw err("bad escape");
            }
            char e = s.charAt(i++);
            switch (e) {
                case '"':
                case '\\':
                case '/':
                    b.append(e);
                    break;
                case 'b':
                    b.append('\b');
                    break;
                case 'f':
                    b.append('\f');
                    break;
                case 'n':
                    b.append('\n');
                    break;
                case 'r':
                    b.append('\r');
                    break;
                case 't':
                    b.append('\t');
                    break;
                case 'u':
                    b.append(unicode());
                    break;
                default:
                    throw err("bad escape");
            }
        }
    }

    private char unicode() {
        if (i + 4 > s.length()) {
            throw err("bad unicode escape");
        }
        int cp;
        try {
            cp = Integer.parseInt(s.substring(i, i + 4), 16);
        } catch (NumberFormatException ex) {
            throw err("bad unicode escape");
        }
        i += 4;
        char c = (char) cp;
        if (Character.isSurrogate(c)) {
            throw err("lone surrogate");
        }
        return c;
    }

    private Object number() {
        int start = i;
        if (peek('-')) {
            i++;
        }
        if (i >= s.length() || !digit(s.charAt(i))) {
            throw err("bad number");
        }
        if (s.charAt(i) == '0') {
            i++;
        } else {
            while (i < s.length() && digit(s.charAt(i))) {
                i++;
            }
        }
        boolean fraction = false;
        if (peek('.')) {
            fraction = true;
            i++;
            int frac = i;
            while (i < s.length() && digit(s.charAt(i))) {
                i++;
            }
            if (i == frac) {
                throw err("bad number");
            }
        }
        if (peek('e') || peek('E')) {
            fraction = true;
            i++;
            if (peek('+') || peek('-')) {
                i++;
            }
            int exp = i;
            while (i < s.length() && digit(s.charAt(i))) {
                i++;
            }
            if (i == exp) {
                throw err("bad number");
            }
        }
        String lit = s.substring(start, i);
        if (!fraction) {
            try {
                return Long.valueOf(lit);
            } catch (NumberFormatException ex) {
                throw err("number out of range");
            }
        }
        double d = Double.parseDouble(lit);
        if (!Double.isFinite(d)) {
            throw err("nonfinite number");
        }
        return d;
    }

    private static boolean digit(char c) {
        return c >= '0' && c <= '9';
    }
}
