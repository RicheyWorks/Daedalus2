// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.fires;

import com.daedalus.world.brew.letters.Destination;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 17 of the Youtube Master Island story, "The Signal Fires" (quest {@code q_signal_fires}). Home and the far
 * islands keep signal fires so they can call each other. A fire link between two places costs
 * {@link Isle#woodTo} wood. Sea stacks ({@link Isle#relay()}) may carry a relay fire. The signal can go up once every
 * island (not every stack) is joined by lit links; it is warm when the wood is the least possible. {@link #best()} is
 * exact: for each subset of relays, Kruskal over the islands and those relays, keeping the cheapest.
 */
public final class SignalFires {
    public static final String QUEST_ID = "q_signal_fires";
    public static final String HOME = "home";
    public static final int MILES_PER_LEG = 10;
    public static final int RELAYS = 2;
    public static final int LINKS_TO_LIGHT = 4;

    public enum Outcome { LIT, DOUSED, ALREADY_LIT, NOT_LIT, SAME_ISLE, UNKNOWN_ISLE, WARM, SMOKY, NOT_JOINED,
        DUPLICATE, IGNORED }

    /** A fire link between two places, ids in sorted order. */
    public record Link(String a, String b, int wood) {
    }

    private final Map<String, Isle> isles = new LinkedHashMap<>();
    private final Map<String, Link> lit = new LinkedHashMap<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("light", "link", LINKS_TO_LIGHT),
            new QuestProgress.Step("signal", "warm", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private final List<Link> best;
    private final int bestWood;
    private Outcome last;

    public SignalFires(List<Isle> list) {
        for (Isle i : list) {
            if (isles.put(i.id(), i) != null) {
                throw new IllegalArgumentException("duplicate isle " + i.id());
            }
        }
        if (list.stream().filter(i -> !i.relay()).count() < 2) {
            throw new IllegalArgumentException("need at least two islands");
        }
        best = List.copyOf(solve());
        bestWood = best.stream().mapToInt(Link::wood).sum();
    }

    /** Home at the centre, each far island at its ark-route distance on its own bearing, plus seeded sea stacks. */
    public static SignalFires seaMap(List<Destination> destinations, long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xF12EL);
        List<Isle> out = new ArrayList<>();
        out.add(new Isle(HOME, 0, 0, false));
        int n = destinations.size();
        for (int i = 0; i < n; i++) {
            Destination d = destinations.get(i);
            double r = d.route().legs().size() * MILES_PER_LEG;
            double a = 2 * Math.PI * i / n + (rng.nextDouble() - 0.5) * 0.6;
            out.add(new Isle(d.id(), round(r * Math.cos(a)), round(r * Math.sin(a)), false));
        }
        double reach = destinations.stream().mapToInt(d -> d.route().legs().size()).max().orElse(1) * MILES_PER_LEG;
        for (int s = 1; s <= RELAYS; s++) {
            double r = reach * (0.3 + 0.5 * rng.nextDouble());
            double a = 2 * Math.PI * rng.nextDouble();
            out.add(new Isle("stack_" + s, round(r * Math.cos(a)), round(r * Math.sin(a)), true));
        }
        return new SignalFires(out);
    }

    private static double round(double v) {
        return Math.round(v * 10) / 10.0;
    }

    /** The link between two places (ids in sorted order). */
    public Link link(String a, String b) {
        String lo = a.compareTo(b) <= 0 ? a : b;
        String hi = lo.equals(a) ? b : a;
        return new Link(lo, hi, isles.get(lo).woodTo(isles.get(hi)));
    }

    /** Cheapest spanning tree (Kruskal) over these places, or null if fewer than one. */
    List<Link> kruskal(List<String> places) {
        List<Link> all = new ArrayList<>();
        for (int i = 0; i < places.size(); i++) {
            for (int j = i + 1; j < places.size(); j++) {
                all.add(link(places.get(i), places.get(j)));
            }
        }
        all.sort(Comparator.comparingInt(Link::wood).thenComparing(Link::a).thenComparing(Link::b));
        Map<String, String> parent = new LinkedHashMap<>();
        places.forEach(p -> parent.put(p, p));
        List<Link> tree = new ArrayList<>();
        for (Link l : all) {
            String ra = find(parent, l.a());
            String rb = find(parent, l.b());
            if (!ra.equals(rb)) {
                parent.put(ra, rb);
                tree.add(l);
            }
        }
        return tree;
    }

    private static String find(Map<String, String> parent, String x) {
        String r = x;
        while (!parent.get(r).equals(r)) {
            r = parent.get(r);
        }
        return r;
    }

    private List<Link> solve() {
        List<String> islands = isles.values().stream().filter(i -> !i.relay()).map(Isle::id).toList();
        List<String> relays = isles.values().stream().filter(Isle::relay).map(Isle::id).toList();
        List<Link> top = null;
        int topWood = Integer.MAX_VALUE;
        for (int mask = 0; mask < (1 << relays.size()); mask++) {
            List<String> places = new ArrayList<>(islands);
            for (int r = 0; r < relays.size(); r++) {
                if ((mask & (1 << r)) != 0) {
                    places.add(relays.get(r));
                }
            }
            List<Link> t = kruskal(places);
            int w = t.stream().mapToInt(Link::wood).sum();
            if (w < topWood) {
                topWood = w;
                top = t;
            }
        }
        return top;
    }

    public List<Isle> isles() {
        return List.copyOf(isles.values());
    }

    /** One least-wood set of links. */
    public List<Link> best() {
        return best;
    }

    public int bestWood() {
        return bestWood;
    }

    public List<Link> lit() {
        return List.copyOf(lit.values());
    }

    public int wood() {
        return lit.values().stream().mapToInt(Link::wood).sum();
    }

    public QuestProgress quest() {
        return quest;
    }

    public Outcome last() {
        return last;
    }

    /** Whether every island (stacks optional) is joined by lit links. */
    public boolean joined() {
        Map<String, String> parent = new LinkedHashMap<>();
        isles.keySet().forEach(p -> parent.put(p, p));
        for (Link l : lit.values()) {
            String ra = find(parent, l.a());
            String rb = find(parent, l.b());
            if (!ra.equals(rb)) {
                parent.put(ra, rb);
            }
        }
        Set<String> roots = new HashSet<>();
        isles.values().stream().filter(i -> !i.relay()).forEach(i -> roots.add(find(parent, i.id())));
        return roots.size() == 1;
    }

    private Outcome guard(String eventId, String a, String b) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (!isles.containsKey(a) || !isles.containsKey(b)) {
            return Outcome.UNKNOWN_ISLE;
        }
        if (a.equals(b)) {
            return Outcome.SAME_ISLE;
        }
        return null;
    }

    /** Lights the fire link between two places. */
    public Outcome light(String eventId, String a, String b) {
        Outcome g = guard(eventId, a, b);
        if (g != null) {
            return g;
        }
        Link l = link(a, b);
        String key = l.a() + "|" + l.b();
        if (lit.containsKey(key)) {
            return Outcome.ALREADY_LIT;
        }
        events.add(eventId);
        lit.put(key, l);
        last = null;
        quest.apply(eventId, "light", "link");
        return Outcome.LIT;
    }

    /** Douses a lit link (its wood comes back). */
    public Outcome douse(String eventId, String a, String b) {
        Outcome g = guard(eventId, a, b);
        if (g != null) {
            return g;
        }
        Link l = link(a, b);
        if (lit.remove(l.a() + "|" + l.b()) == null) {
            return Outcome.NOT_LIT;
        }
        events.add(eventId);
        last = null;
        return Outcome.DOUSED;
    }

    /** Sends the signal round: warm if every island is joined on the least wood. */
    public Outcome signal(String eventId) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (!joined()) {
            return Outcome.NOT_JOINED;
        }
        events.add(eventId);
        last = wood() == bestWood ? Outcome.WARM : Outcome.SMOKY;
        if (last == Outcome.WARM) {
            quest.apply(eventId, "signal", "warm");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the signal went round warm. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperFireLines.THANKS;
        }
        return KeeperFireLines.line(this);
    }
}
