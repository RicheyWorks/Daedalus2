// SPDX-License-Identifier: MIT

package com.daedalus.world.tactics;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * DTO 1, the squad-orders contract between the Java combat director and Unreal (ADR-060), ported line for line from
 * the Unreal plugin's {@code DaedalusTacticsCore.h}. {@code TacticsParityTest} checks it against
 * {@code engines/unreal/core-test/tactics_parity.txt}, which the C++ test writes: the same specs refused with the same
 * messages, and the same decided specs written byte for byte.
 *
 * <pre>
 * DTO 1
 * squad &lt;id&gt; tick &lt;n&gt;
 * order &lt;unit&gt; &lt;HOLD|ATTACK|FLANK|DEFEND|RETREAT|REINFORCE&gt; &lt;LEFT|RIGHT|-&gt; &lt;x&gt; &lt;y&gt; &lt;z&gt; | &lt;why&gt;
 * </pre>
 * Points are in Unreal centimetres. Specs are all or nothing: one bad line refuses the whole spec, so a squad never
 * gets half an order.
 */
public final class TacticalOrders {

    public static final int VERSION = 1;
    public static final int MAX_ORDERS = 256;
    public static final int MAX_LINE = 512;
    public static final double MAX_COORD = 1.0e8;

    public enum Verb { HOLD, ATTACK, FLANK, DEFEND, RETREAT, REINFORCE }

    public enum Side {
        NONE("-"), LEFT("LEFT"), RIGHT("RIGHT");

        private final String wire;

        Side(String wire) {
            this.wire = wire;
        }

        public String wire() {
            return wire;
        }
    }

    /** A point in Unreal centimetres. */
    public record Vec(double x, double y, double z) {
    }

    public record Order(String unit, Verb verb, Side side, Vec at, String why) {
    }

    public record Spec(String squad, long tick, List<Order> orders) {
        public Spec {
            orders = List.copyOf(orders);
        }
    }

    /** Either a spec, or the first problem with its line number (and then no orders at all). */
    public record ParseResult(boolean ok, String error, Spec spec) {
    }

    public enum EventKind { SEEN, HIT, DOWN, PLAYER }

    /** HIT: damage taken; SEEN: 1 or 0; DOWN: 0; PLAYER: health. The PLAYER event's unit is "player". */
    public record Event(EventKind kind, String unit, Vec at, double value) {
    }

    private TacticalOrders() {
    }

    static boolean token(String s) {
        if (s.isEmpty() || s.length() > 64) {
            return false;
        }
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            boolean ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')
                    || c == '_' || c == '-' || c == '.';
            if (!ok) {
                return false;
            }
        }
        return true;
    }

    /** Plain decimals only, the same grammar as the C++: [+-]? (digits [. digits?] | . digits) ([eE] [+-]? digits)?. */
    static boolean decimal(String s) {
        int i = 0;
        int n = s.length();
        if (i < n && (s.charAt(i) == '+' || s.charAt(i) == '-')) {
            i++;
        }
        int b = i;
        while (i < n && Character.isDigit(s.charAt(i)) && s.charAt(i) < 128) {
            i++;
        }
        int whole = i - b;
        int frac = 0;
        if (i < n && s.charAt(i) == '.') {
            i++;
            b = i;
            while (i < n && Character.isDigit(s.charAt(i)) && s.charAt(i) < 128) {
                i++;
            }
            frac = i - b;
        }
        if (whole == 0 && frac == 0) {
            return false;
        }
        if (i < n && (s.charAt(i) == 'e' || s.charAt(i) == 'E')) {
            i++;
            if (i < n && (s.charAt(i) == '+' || s.charAt(i) == '-')) {
                i++;
            }
            b = i;
            while (i < n && Character.isDigit(s.charAt(i)) && s.charAt(i) < 128) {
                i++;
            }
            if (i == b) {
                return false;
            }
        }
        return i == n;
    }

    /** The number, or NaN if it is not a plain decimal within MAX_COORD. */
    static double number(String s) {
        if (s.isEmpty() || !decimal(s)) {
            return Double.NaN;
        }
        double v = Double.parseDouble(s);
        return Double.isFinite(v) && Math.abs(v) <= MAX_COORD ? v : Double.NaN;
    }

    private static ParseResult fail(int line, String why) {
        return new ParseResult(false, "line " + line + ": " + why, null);
    }

    private static boolean space(char c) {
        return c == ' ' || c == '\t' || c == '\u000B' || c == '\f' || c == '\r' || c == '\n';
    }

    /** Whitespace-separated words, as C++'s {@code istream >> word} sees them. One pass, no regex. */
    private static List<String> words(String body) {
        List<String> out = new ArrayList<>(8);
        int n = body.length();
        int i = 0;
        while (i < n) {
            while (i < n && space(body.charAt(i))) {
                i++;
            }
            if (i >= n) {
                break;
            }
            int b = i;
            while (i < n && !space(body.charAt(i))) {
                i++;
            }
            out.add(body.substring(b, i));
        }
        return out;
    }

    /** Longer than MAX_LINE in UTF-8 bytes, as C++ counts it, without encoding short lines. */
    static boolean tooLong(String line) {
        if (line.length() > MAX_LINE) {
            return true;   // every char is at least one byte
        }
        return line.length() * 3 > MAX_LINE && line.getBytes(StandardCharsets.UTF_8).length > MAX_LINE;
    }

    private static String stripLeadingSpaces(String s) {
        int i = 0;
        while (i < s.length() && s.charAt(i) == ' ') {
            i++;
        }
        return s.substring(i);
    }

    public static ParseResult parse(String text) {
        String[] lines = text.split("\n", -1);
        int count = text.endsWith("\n") ? lines.length - 1 : lines.length;   // getline never sees the trailing empty line
        if (text.isEmpty()) {
            count = 0;
        }
        boolean head = false;
        boolean squadSeen = false;
        String squad = null;
        long tick = 0;
        List<Order> orders = new ArrayList<>();
        java.util.Set<String> seen = new java.util.HashSet<>();
        int n = 0;
        for (int li = 0; li < count; li++) {
            ++n;
            String line = lines[li];
            if (line.endsWith("\r")) {
                line = line.substring(0, line.length() - 1);
            }
            if (tooLong(line)) {   // bytes, as in C++
                return fail(n, "line too long");
            }
            if (line.isEmpty() || line.charAt(0) == '#') {
                continue;
            }
            String body = line;
            String why = "";
            int bar = line.indexOf('|');
            if (bar >= 0) {
                body = line.substring(0, bar);
                why = stripLeadingSpaces(line.substring(bar + 1));
            }
            List<String> t = words(body);
            if (t.isEmpty()) {
                return fail(n, "a line with only a reason");
            }
            if (!head) {
                if (t.size() != 2 || !t.get(0).equals("DTO")) {
                    return fail(n, "expected 'DTO 1'");
                }
                if (!t.get(1).equals(Integer.toString(VERSION))) {
                    return fail(n, "unsupported version " + t.get(1));
                }
                head = true;
                continue;
            }
            if (t.get(0).equals("squad")) {
                if (squadSeen) {
                    return fail(n, "second squad line");
                }
                if (t.size() != 4 || !t.get(2).equals("tick") || !token(t.get(1))) {
                    return fail(n, "expected 'squad <id> tick <n>'");
                }
                double tk = number(t.get(3));
                if (Double.isNaN(tk) || tk < 0 || tk != Math.floor(tk)) {
                    return fail(n, "bad tick");
                }
                squad = t.get(1);
                tick = (long) tk;
                squadSeen = true;
                continue;
            }
            if (t.get(0).equals("order")) {
                if (!squadSeen) {
                    return fail(n, "order before the squad line");
                }
                if (t.size() != 7) {
                    return fail(n, "expected 'order <unit> <VERB> <SIDE> <x> <y> <z>'");
                }
                if (orders.size() >= MAX_ORDERS) {
                    return fail(n, "more than " + MAX_ORDERS + " orders");
                }
                if (!token(t.get(1))) {
                    return fail(n, "bad unit id");
                }
                Verb verb = null;
                for (Verb v : Verb.values()) {
                    if (v.name().equals(t.get(2))) {
                        verb = v;
                    }
                }
                if (verb == null) {
                    return fail(n, "unknown verb " + t.get(2));
                }
                Side side = null;
                for (Side sd : Side.values()) {
                    if (sd.wire().equals(t.get(3))) {
                        side = sd;
                    }
                }
                if (side == null) {
                    return fail(n, "unknown side " + t.get(3));
                }
                if (verb == Verb.FLANK && side == Side.NONE) {
                    return fail(n, "FLANK needs LEFT or RIGHT");
                }
                double x = number(t.get(4));
                double y = number(t.get(5));
                double z = number(t.get(6));
                if (Double.isNaN(x) || Double.isNaN(y) || Double.isNaN(z)) {
                    return fail(n, "bad point");
                }
                String unit = t.get(1);
                if (!seen.add(unit)) {   // a hash set: the list scan made a full spec O(n^2)
                    return fail(n, "two orders for " + unit);
                }
                orders.add(new Order(unit, verb, side, new Vec(x, y, z), why));
                continue;
            }
            return fail(n, "unknown line '" + t.get(0) + "'");
        }
        if (!head) {
            return fail(0, "empty spec");
        }
        if (!squadSeen) {
            return fail(n, "no squad line");
        }
        return new ParseResult(true, "", new Spec(squad, tick, orders));
    }

    /** C's printf("%.1f"): the exact binary value rounded half-even, keeping the sign of a negative that rounds to 0. */
    static String num(double v) {
        StringBuilder b = new StringBuilder(16);
        appendNum(b, v);
        return b.toString();
    }

    /**
     * {@link #num} appended in place. Fast path: below 1e9 the product {@code v * 10} is off by under 1e-6, so unless it
     * sits that close to a .5 tie its rounding is already the exact value's; only near-ties (rare) go through BigDecimal.
     * {@code TacticsNumTest} compares both on a million values, ties included.
     */
    static void appendNum(StringBuilder out, double v) {
        double a = Math.abs(v);
        if (a < 1e9) {
            double t = a * 10;
            double frac = t - Math.floor(t);
            if (Math.abs(frac - 0.5) > 1e-6) {
                long r = (long) Math.floor(t + 0.5);
                boolean negative = v < 0 || (v == 0 && 1.0 / v < 0);
                if (negative) {
                    out.append('-');
                }
                out.append(r / 10).append('.').append((char) ('0' + (int) (r % 10)));
                return;
            }
        }
        out.append(slowNum(v));
    }

    static String slowNum(double v) {
        String s = new BigDecimal(v).setScale(1, RoundingMode.HALF_EVEN).toPlainString();
        boolean negative = v < 0 || (v == 0 && 1.0 / v < 0);
        if (negative && !s.startsWith("-")) {
            s = "-" + s;
        }
        return s;
    }

    public static String write(Spec s) {
        StringBuilder out = new StringBuilder("DTO 1\nsquad ").append(s.squad()).append(" tick ").append(s.tick()).append('\n');
        for (Order o : s.orders()) {
            out.append("order ").append(o.unit()).append(' ').append(o.verb().name()).append(' ').append(o.side().wire())
                    .append(' ').append(num(o.at().x())).append(' ').append(num(o.at().y())).append(' ')
                    .append(num(o.at().z()));
            String why = o.why() == null ? "" : o.why().replace('\n', ' ');
            if (!why.isEmpty()) {
                out.append(" | ").append(why);
            }
            out.append('\n');
        }
        return out.toString();
    }

    public static String writeEvents(long tick, List<Event> events) {
        StringBuilder out = new StringBuilder("DTE 1\ntick ").append(tick).append('\n');
        for (Event e : events) {
            out.append("event ").append(e.kind().name()).append(' ').append(e.unit()).append(' ')
                    .append(num(e.at().x())).append(' ').append(num(e.at().y())).append(' ').append(num(e.at().z()))
                    .append(' ').append(num(e.value())).append('\n');
        }
        return out.toString();
    }

    /** A DTE 1 batch: the host tick it was taken at and the events in order. */
    public record Events(long tick, List<Event> events) {
        public Events {
            events = List.copyOf(events);
        }
    }

    /** At most this many events in one batch: the host keeps 512 and drops the oldest. */
    public static final int MAX_EVENTS = 512;

    /**
     * Reads a DTE 1 batch, as written by {@code UDaedalusTactics::TakeEvents} (C++ {@code WriteEvents}):
     * <pre>
     * DTE 1
     * tick &lt;n&gt;
     * event &lt;SEEN|HIT|DOWN|PLAYER&gt; &lt;unit|player&gt; &lt;x&gt; &lt;y&gt; &lt;z&gt; &lt;value&gt;
     * </pre>
     * Throws {@link IllegalArgumentException} naming the line. Values are observations, not authority: HIT is
     * damage taken, PLAYER is the hero's health (-1 = unknown), SEEN is 1 or 0, DOWN is 0.
     */
    public static Events parseEvents(String text) {
        String[] lines = text.split("\n", -1);
        if (lines.length < 2 || !lines[0].equals("DTE 1")) {
            throw new IllegalArgumentException("line 1: expected 'DTE 1'");
        }
        List<String> h = words(lines[1]);
        double tick = h.size() == 2 && h.get(0).equals("tick") ? number(h.get(1)) : Double.NaN;
        if (Double.isNaN(tick) || tick < 0 || tick != Math.floor(tick)) {
            throw new IllegalArgumentException("line 2: expected 'tick <n>'");
        }
        List<Event> events = new ArrayList<>();
        for (int i = 2; i < lines.length; i++) {
            if (lines[i].isEmpty()) {
                continue;
            }
            List<String> t = words(lines[i]);
            EventKind kind = null;
            if (t.size() == 7 && t.get(0).equals("event")) {
                for (EventKind k : EventKind.values()) {
                    if (k.name().equals(t.get(1))) {
                        kind = k;
                    }
                }
            }
            double[] v = new double[4];
            boolean ok = kind != null && token(t.get(2)) && (kind != EventKind.PLAYER || t.get(2).equals("player"));
            for (int k = 0; ok && k < 4; k++) {
                v[k] = number(t.get(3 + k));
                ok = !Double.isNaN(v[k]);
            }
            if (!ok || events.size() >= MAX_EVENTS) {
                throw new IllegalArgumentException("line " + (i + 1) + ": bad event line");
            }
            events.add(new Event(kind, t.get(2), new Vec(v[0], v[1], v[2]), v[3]));
        }
        return new Events((long) tick, events);
    }

    /** One unit of a DTR 1 roster: the host's trusted bootstrap for a squad (ADR-060, Astra's Frame needs it). */
    public record RosterUnit(String unit, String kind, double health, double maxHealth, Vec at, boolean seesPlayer) {
    }

    /** A DTR 1 roster: the Unreal world's session, the squad, the tick and its units. */
    public record Roster(String session, String squad, long tick, List<RosterUnit> units) {
        public Roster {
            units = List.copyOf(units);
        }

        /** The units as the directors take them (SquadDirector, and AdaptiveDirector's Frame); the fallen keep health 0. */
        public List<SquadDirector.Unit> toUnits() {
            List<SquadDirector.Unit> out = new ArrayList<>();
            for (RosterUnit u : units) {
                out.add(new SquadDirector.Unit(u.unit(), u.at(), u.health(), u.maxHealth(), u.seesPlayer()));
            }
            return out;
        }
    }

    /**
     * Reads a DTR 1 roster, written by {@code UDaedalusTactics::TakeRoster} (C++ {@code WriteRoster}):
     * <pre>
     * DTR 1
     * session &lt;id&gt; squad &lt;id&gt; tick &lt;n&gt;
     * unit &lt;id&gt; &lt;KIND&gt; &lt;health&gt; &lt;maxHealth&gt; &lt;x&gt; &lt;y&gt; &lt;z&gt; &lt;sees 0|1&gt;
     * </pre>
     * Throws {@link IllegalArgumentException} naming the line on anything else.
     */
    public static Roster parseRoster(String text) {
        String[] lines = text.split("\n", -1);
        if (lines.length < 2 || !lines[0].equals("DTR 1")) {
            throw new IllegalArgumentException("line 1: expected 'DTR 1'");
        }
        List<String> h = words(lines[1]);
        if (h.size() != 6 || !h.get(0).equals("session") || !h.get(2).equals("squad") || !h.get(4).equals("tick")
                || !token(h.get(1)) || !token(h.get(3))) {
            throw new IllegalArgumentException("line 2: expected 'session <id> squad <id> tick <n>'");
        }
        double tick = number(h.get(5));
        if (Double.isNaN(tick) || tick < 0 || tick != Math.floor(tick)) {
            throw new IllegalArgumentException("line 2: bad tick");
        }
        List<RosterUnit> units = new ArrayList<>();
        for (int i = 2; i < lines.length; i++) {
            if (lines[i].isEmpty()) {
                continue;
            }
            List<String> t = words(lines[i]);
            double[] v = new double[5];
            boolean ok = t.size() == 9 && t.get(0).equals("unit") && token(t.get(1)) && token(t.get(2))
                    && (t.get(8).equals("0") || t.get(8).equals("1"));
            for (int k = 0; ok && k < 5; k++) {
                v[k] = number(t.get(3 + k));
                ok = !Double.isNaN(v[k]);
            }
            if (!ok || v[0] < 0 || v[1] < 0 || units.size() >= MAX_ORDERS) {
                throw new IllegalArgumentException("line " + (i + 1) + ": bad unit line");
            }
            units.add(new RosterUnit(t.get(1), t.get(2), v[0], v[1], new Vec(v[2], v[3], v[4]), t.get(8).equals("1")));
        }
        return new Roster(h.get(1), h.get(3), (long) tick, units);
    }

    /** Lower-case name, for logs. */
    public static String label(Verb v) {
        return v.name().toLowerCase(Locale.ROOT);
    }
}
