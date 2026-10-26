// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** A small, strict JSON reader (objects, arrays, strings, numbers, booleans, null) so the core stays JDK-only. */
public final class MiniJson {
    private final String s;
    private int i;

    private MiniJson(String s) {
        this.s = s;
    }

    /** Parses {@code text} into Map, List, String, Double, Boolean or null. */
    public static Object parse(String text) {
        MiniJson p = new MiniJson(text);
        p.ws();
        Object v = p.value();
        p.ws();
        if (p.i != p.s.length()) {
            throw p.err("trailing data");
        }
        return v;
    }

    private IllegalArgumentException err(String m) {
        return new IllegalArgumentException("tonics json: " + m + " at " + i);
    }

    private void ws() {
        while (i < s.length() && Character.isWhitespace(s.charAt(i))) {
            i++;
        }
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
        Map<String, Object> m = new LinkedHashMap<>();
        i++;
        ws();
        if (i < s.length() && s.charAt(i) == '}') {
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
            if (i < s.length() && s.charAt(i) == ',') {
                i++;
                continue;
            }
            expect('}');
            return m;
        }
    }

    private List<Object> array() {
        List<Object> l = new ArrayList<>();
        i++;
        ws();
        if (i < s.length() && s.charAt(i) == ']') {
            i++;
            return l;
        }
        while (true) {
            ws();
            l.add(value());
            ws();
            if (i < s.length() && s.charAt(i) == ',') {
                i++;
                continue;
            }
            expect(']');
            return l;
        }
    }

    private void expect(char c) {
        if (i >= s.length() || s.charAt(i) != c) {
            throw err("expected '" + c + "'");
        }
        i++;
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
            if (c != '\\') {
                b.append(c);
                continue;
            }
            if (i >= s.length()) {
                throw err("bad escape");
            }
            char e = s.charAt(i++);
            switch (e) {
                case 'n':
                    b.append('\n');
                    break;
                case 't':
                    b.append('\t');
                    break;
                case 'r':
                    b.append('\r');
                    break;
                case 'b':
                    b.append('\b');
                    break;
                case 'f':
                    b.append('\f');
                    break;
                case 'u':
                    if (i + 4 > s.length()) {
                        throw err("bad unicode escape");
                    }
                    b.append((char) Integer.parseInt(s.substring(i, i + 4), 16));
                    i += 4;
                    break;
                default:
                    b.append(e);
                    break;
            }
        }
    }

    private Double number() {
        int start = i;
        while (i < s.length() && "+-0123456789.eE".indexOf(s.charAt(i)) >= 0) {
            i++;
        }
        if (start == i) {
            throw err("unexpected character");
        }
        return Double.valueOf(s.substring(start, i));
    }
}
