// SPDX-License-Identifier: MIT
package com.daedalus.world.activity;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Reads the canonical activity-result v1 wire form ({@link ActivityResultReceipt#toJson()}) back into a receipt.
 *
 * <p>The codec is strict on purpose: it accepts only the exact canonical bytes the receipt would write itself. It
 * re-serialises what it parsed and refuses any input that differs (reordered keys, spaces, extra fields, escapes), so a
 * receipt read from disk or the wire always has the same digest it was journalled with.
 */
public final class ReceiptCodec {

    private ReceiptCodec() { }

    /** Parses one canonical receipt line; throws {@link IllegalArgumentException} on anything else. */
    public static ActivityResultReceipt parse(String json) {
        if (json == null || json.isEmpty()) throw new IllegalArgumentException("empty receipt");
        Reader rd = new Reader(json);
        Object v = rd.value();
        rd.end();
        if (!(v instanceof Map<?, ?> m)) throw new IllegalArgumentException("receipt must be a JSON object");
        if (!ActivityResultReceipt.SCHEMA.equals(m.get("schema")))
            throw new IllegalArgumentException("schema must be " + ActivityResultReceipt.SCHEMA);
        List<ActivityParticipant> participants = new ArrayList<>();
        for (Object o : list(m, "participants")) {
            if (!(o instanceof Map<?, ?> p)) throw new IllegalArgumentException("participant must be an object");
            participants.add(new ActivityParticipant(str(p, "instanceId"),
                    ActivityParticipant.Kind.valueOf(str(p, "kind")), str(p, "profile"), str(p, "role")));
        }
        Object mv = m.get("measures");
        if (!(mv instanceof Map<?, ?> mm)) throw new IllegalArgumentException("measures must be an object");
        TreeMap<String, Long> measures = new TreeMap<>();
        mm.forEach((k, val) -> {
            if (!(val instanceof Long l)) throw new IllegalArgumentException("measure " + k + " must be an integer");
            measures.put((String) k, l);
        });
        List<String> refs = new ArrayList<>();
        for (Object o : list(m, "sourceEventRefs")) {
            if (!(o instanceof String s)) throw new IllegalArgumentException("sourceEventRef must be a string");
            refs.add(s);
        }
        long rev = num(m, "definitionRevision");
        if (rev < 1 || rev > Integer.MAX_VALUE) throw new IllegalArgumentException("definitionRevision out of range");
        ActivityResultReceipt r = new ActivityResultReceipt(str(m, "resultId"), str(m, "sessionId"),
                str(m, "activityId"), (int) rev, ActivityMode.valueOf(str(m, "mode")), str(m, "issuer"),
                str(m, "verificationRef"), ActivityOutcome.valueOf(str(m, "outcome")), participants, measures, refs,
                num(m, "clockBoundaryMs"));
        if (!r.toJson().equals(json)) throw new IllegalArgumentException("receipt is not in canonical form");
        return r;
    }

    private static String str(Map<?, ?> m, String k) {
        if (!(m.get(k) instanceof String s)) throw new IllegalArgumentException(k + " must be a string");
        return s;
    }

    private static long num(Map<?, ?> m, String k) {
        if (!(m.get(k) instanceof Long l)) throw new IllegalArgumentException(k + " must be an integer");
        return l;
    }

    private static List<?> list(Map<?, ?> m, String k) {
        if (!(m.get(k) instanceof List<?> l)) throw new IllegalArgumentException(k + " must be an array");
        return l;
    }

    /** Minimal reader for the canonical subset: objects, arrays, unescaped strings, integers. */
    private static final class Reader {
        private final String s;
        private int i;

        Reader(String s) { this.s = s; }

        Object value() {
            if (i >= s.length()) throw err("unexpected end");
            char c = s.charAt(i);
            if (c == '{') return object();
            if (c == '[') return array();
            if (c == '"') return string();
            if (c == '-' || (c >= '0' && c <= '9')) return number();
            throw err("unexpected '" + c + "'");
        }

        private Map<String, Object> object() {
            Map<String, Object> m = new LinkedHashMap<>();
            i++;
            if (peek() == '}') { i++; return m; }
            while (true) {
                String k = string();
                expect(':');
                if (m.put(k, value()) != null) throw err("duplicate key " + k);
                char c = next();
                if (c == '}') return m;
                if (c != ',') throw err("expected ',' or '}'");
            }
        }

        private List<Object> array() {
            List<Object> l = new ArrayList<>();
            i++;
            if (peek() == ']') { i++; return l; }
            while (true) {
                l.add(value());
                char c = next();
                if (c == ']') return l;
                if (c != ',') throw err("expected ',' or ']'");
            }
        }

        private String string() {
            expect('"');
            int start = i;
            while (i < s.length() && s.charAt(i) != '"') {
                char c = s.charAt(i);
                if (c == '\\' || c < 0x20) throw err("escapes and control characters are not canonical");
                i++;
            }
            if (i >= s.length()) throw err("unterminated string");
            return s.substring(start, i++);
        }

        private Long number() {
            int start = i;
            if (s.charAt(i) == '-') i++;
            while (i < s.length() && Character.isDigit(s.charAt(i))) i++;
            try {
                return Long.parseLong(s.substring(start, i));
            } catch (NumberFormatException e) {
                throw err("bad integer");
            }
        }

        private char peek() {
            if (i >= s.length()) throw err("unexpected end");
            return s.charAt(i);
        }

        private char next() {
            char c = peek();
            i++;
            return c;
        }

        private void expect(char c) {
            if (next() != c) throw err("expected '" + c + "'");
        }

        void end() {
            if (i != s.length()) throw err("trailing characters");
        }

        private IllegalArgumentException err(String msg) {
            return new IllegalArgumentException(msg + " at " + i);
        }
    }
}
