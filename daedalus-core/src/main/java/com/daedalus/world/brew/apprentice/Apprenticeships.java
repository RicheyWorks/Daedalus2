// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.apprentice;

import com.daedalus.world.brew.cellar.RootCellar;
import com.daedalus.world.brew.school.Pupil;
import com.daedalus.world.brew.stones.ChoirStones;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.brew.week.FirstWeek;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Deque;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 15 of the Youtube Master Island story, "The Apprentices" (quest {@code q_apprentices}). The G116 children
 * stay on to learn a trade: each island master takes one apprentice. Every child ranks the masters and every master
 * ranks the children (best first). A pairing is stable when no child and master would both rather have each other
 * than their partners (a blocking pair). {@link #proposing(boolean)} runs Gale-Shapley; with children proposing it
 * gives every child their best partner in any stable pairing, with masters proposing every master theirs.
 */
public final class Apprenticeships {
    public static final String QUEST_ID = "q_apprentices";
    public static final String DOV = "dov";
    public static final List<String> MASTERS = List.of(ChoirStones.MASON, SeedSongSpring.KEEPER, RootCellar.BRINE, DOV);

    public enum Outcome { PAIRED, UNPAIRED, CHILD_TAKEN, MASTER_TAKEN, NOT_PAIRED, UNKNOWN_CHILD, UNKNOWN_MASTER,
        STABLE, UNSTABLE, NOT_EVERYONE, DUPLICATE, IGNORED }

    /** A child and a master who would both rather have each other. */
    public record Pair(String child, String master) {
    }

    private final Map<String, List<String>> childPrefs = new LinkedHashMap<>();
    private final Map<String, List<String>> masterPrefs = new LinkedHashMap<>();
    private final Map<String, String> masterOf = new LinkedHashMap<>();
    private final Set<String> events = new HashSet<>();
    private final Set<String> everPaired = new HashSet<>();
    private final QuestProgress quest;
    private Outcome announced;

    /** Rankings, best first: each child ranks every master and each master ranks every child. */
    public Apprenticeships(Map<String, List<String>> childPrefs, Map<String, List<String>> masterPrefs) {
        if (childPrefs.size() != masterPrefs.size() || childPrefs.isEmpty()) {
            throw new IllegalArgumentException("need as many children as masters");
        }
        childPrefs.forEach((c, p) -> {
            if (!new HashSet<>(p).equals(masterPrefs.keySet()) || p.size() != masterPrefs.size()) {
                throw new IllegalArgumentException(c + " must rank every master once");
            }
            this.childPrefs.put(c, List.copyOf(p));
        });
        masterPrefs.forEach((m, p) -> {
            if (!new HashSet<>(p).equals(childPrefs.keySet()) || p.size() != childPrefs.size()) {
                throw new IllegalArgumentException(m + " must rank every child once");
            }
            this.masterPrefs.put(m, List.copyOf(p));
        });
        quest = new QuestProgress(List.of(
                new QuestProgress.Step("pair", "child", childPrefs.size()),
                new QuestProgress.Step("announce", "stable", 1),
                new QuestProgress.Step("talk", FirstWeek.WICK, 1)));
    }

    /** The G116 children and the four masters, with seeded rankings on both sides. */
    public static Apprenticeships forChildren(List<Pupil> children, long seed) {
        if (children.size() != MASTERS.size()) {
            throw new IllegalArgumentException("one child per master: " + MASTERS.size());
        }
        SplittableRandom rng = new SplittableRandom(seed ^ 0xA9915L);
        List<String> ids = children.stream().map(Pupil::id).toList();
        Map<String, List<String>> cp = new LinkedHashMap<>();
        for (String c : ids) {
            cp.put(c, shuffled(MASTERS, rng));
        }
        Map<String, List<String>> mp = new LinkedHashMap<>();
        for (String m : MASTERS) {
            mp.put(m, shuffled(ids, rng));
        }
        return new Apprenticeships(cp, mp);
    }

    private static List<String> shuffled(List<String> in, SplittableRandom rng) {
        List<String> out = new ArrayList<>(in);
        for (int i = out.size() - 1; i > 0; i--) {
            Collections.swap(out, i, rng.nextInt(i + 1));
        }
        return out;
    }

    /** Gale-Shapley. {@code childrenPropose}: children propose to masters, else masters to children. child to master. */
    public Map<String, String> proposing(boolean childrenPropose) {
        Map<String, List<String>> prop = childrenPropose ? childPrefs : masterPrefs;
        Map<String, List<String>> recv = childrenPropose ? masterPrefs : childPrefs;
        Map<String, Integer> next = new LinkedHashMap<>();
        Map<String, String> held = new LinkedHashMap<>();
        Deque<String> free = new ArrayDeque<>(prop.keySet());
        prop.keySet().forEach(p -> next.put(p, 0));
        while (!free.isEmpty()) {
            String p = free.poll();
            String r = prop.get(p).get(next.get(p));
            next.put(p, next.get(p) + 1);
            String cur = held.get(r);
            if (cur == null) {
                held.put(r, p);
            } else if (recv.get(r).indexOf(p) < recv.get(r).indexOf(cur)) {
                held.put(r, p);
                free.add(cur);
            } else {
                free.add(p);
            }
        }
        Map<String, String> out = new LinkedHashMap<>();
        held.forEach((r, p) -> {
            if (childrenPropose) {
                out.put(p, r);
            } else {
                out.put(r, p);
            }
        });
        Map<String, String> ordered = new LinkedHashMap<>();
        childPrefs.keySet().forEach(c -> ordered.put(c, out.get(c)));
        return ordered;
    }

    /** Every blocking pair of a full pairing (child to master). */
    public List<Pair> blockingPairs(Map<String, String> pairing) {
        Map<String, String> childOf = new LinkedHashMap<>();
        pairing.forEach((c, m) -> childOf.put(m, c));
        List<Pair> out = new ArrayList<>();
        for (Map.Entry<String, List<String>> e : childPrefs.entrySet()) {
            String c = e.getKey();
            List<String> cp = e.getValue();
            for (String m : cp.subList(0, cp.indexOf(pairing.get(c)))) {
                List<String> mp = masterPrefs.get(m);
                if (mp.indexOf(c) < mp.indexOf(childOf.get(m))) {
                    out.add(new Pair(c, m));
                }
            }
        }
        return out;
    }

    /** Rank (0 = first choice) of {@code other} in {@code who}'s list. */
    public int rank(String who, String other) {
        List<String> p = childPrefs.containsKey(who) ? childPrefs.get(who) : masterPrefs.get(who);
        return p.indexOf(other);
    }

    public Map<String, List<String>> childPrefs() {
        return Collections.unmodifiableMap(childPrefs);
    }

    public Map<String, List<String>> masterPrefs() {
        return Collections.unmodifiableMap(masterPrefs);
    }

    /** The lantern board: child to master. */
    public Map<String, String> board() {
        return Collections.unmodifiableMap(masterOf);
    }

    public QuestProgress quest() {
        return quest;
    }

    /** The last announcement (STABLE or UNSTABLE), or null. */
    public Outcome announced() {
        return announced;
    }

    private Outcome guard(String eventId, String child) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (!childPrefs.containsKey(child)) {
            return Outcome.UNKNOWN_CHILD;
        }
        return null;
    }

    /** Pins a child to a master on the lantern board. */
    public Outcome pair(String eventId, String child, String master) {
        Outcome g = guard(eventId, child);
        if (g != null) {
            return g;
        }
        if (!masterPrefs.containsKey(master)) {
            return Outcome.UNKNOWN_MASTER;
        }
        if (masterOf.containsKey(child)) {
            return Outcome.CHILD_TAKEN;
        }
        if (masterOf.containsValue(master)) {
            return Outcome.MASTER_TAKEN;
        }
        events.add(eventId);
        masterOf.put(child, master);
        announced = null;
        if (everPaired.add(child)) {
            quest.apply("pair-" + child, "pair", "child");
        }
        return Outcome.PAIRED;
    }

    /** Takes a child's pin off the board. */
    public Outcome unpair(String eventId, String child) {
        Outcome g = guard(eventId, child);
        if (g != null) {
            return g;
        }
        if (!masterOf.containsKey(child)) {
            return Outcome.NOT_PAIRED;
        }
        events.add(eventId);
        masterOf.remove(child);
        announced = null;
        return Outcome.UNPAIRED;
    }

    /** Lantern night: the board is read out. Stable if there is no blocking pair. */
    public Outcome announce(String eventId) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (masterOf.size() < childPrefs.size()) {
            return Outcome.NOT_EVERYONE;
        }
        events.add(eventId);
        announced = blockingPairs(masterOf).isEmpty() ? Outcome.STABLE : Outcome.UNSTABLE;
        if (announced == Outcome.STABLE) {
            quest.apply(eventId, "announce", "stable");
        }
        return announced;
    }

    /** Talks to Old Wick: the quest's talk step once a stable pairing was announced. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", FirstWeek.WICK);
            return WickApprenticeLines.THANKS;
        }
        return WickApprenticeLines.line(this);
    }
}
