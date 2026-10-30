// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.namestones;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 47 of the Youtube Master Island story, "The Name Stones" (quest {@code q_name_stones}). Each family's name
 * is carved on a stone, but carving is slow, so only the start of each name is carved. A carving is clear when no
 * other family's name starts with it. {@link #shortest(int)} is each name's shortest clear start, read from a trie of
 * the names with a count of names through each node; {@link #fewest()} is their total. Carving that many letters
 * earns credit; more letters do not, and an AMBIGUOUS stone two families could read earns none.
 */
public final class NameStones {
    public static final String QUEST_ID = "q_name_stones";

    public enum Outcome { WELL, LONG, AMBIGUOUS, NOT_THERE, DUPLICATE, IGNORED }

    private static final class Node {
        final Map<Character, Node> next = new HashMap<>();
        int through;
    }

    private final List<String> names;
    private final int[] shortest;
    private final int fewest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("list", "families", 1),
            new QuestProgress.Step("carve", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int carved = -1;
    private int clash = -1;
    private Outcome last;

    /** Distinct, non-empty lowercase names, none the start of another. */
    public NameStones(List<String> names) {
        if (names == null || names.isEmpty()) {
            throw new IllegalArgumentException("at least one family");
        }
        for (String a : names) {
            if (a == null || a.isEmpty() || !a.chars().allMatch(c -> c >= 'a' && c <= 'z')) {
                throw new IllegalArgumentException("names are lowercase letters");
            }
        }
        for (int i = 0; i < names.size(); i++) {
            for (int j = 0; j < names.size(); j++) {
                if (i != j && names.get(j).startsWith(names.get(i))) {
                    throw new IllegalArgumentException("no name may start another");
                }
            }
        }
        this.names = List.copyOf(names);
        Node root = new Node();
        for (String s : names) {
            Node at = root;
            for (char c : s.toCharArray()) {
                at = at.next.computeIfAbsent(c, k -> new Node());
                at.through++;
            }
        }
        shortest = new int[names.size()];
        int total = 0;
        for (int i = 0; i < names.size(); i++) {
            Node at = root;
            String s = names.get(i);
            int len = 0;
            while (len < s.length()) {
                at = at.next.get(s.charAt(len));
                len++;
                if (at.through == 1) {
                    break;
                }
            }
            shortest[i] = len;
            total += len;
        }
        fewest = total;
    }

    /** A seeded village of 2-7 family names of 1-5 letters from a, b, c (so starts collide). */
    public static NameStones seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x4A3EL);
        int want = 2 + rng.nextInt(6);
        List<String> out = new ArrayList<>();
        for (int tries = 0; tries < 200 && out.size() < want; tries++) {
            StringBuilder b = new StringBuilder();
            int len = 1 + rng.nextInt(5);
            for (int i = 0; i < len; i++) {
                b.append((char) ('a' + rng.nextInt(3)));
            }
            String s = b.toString();
            if (out.stream().noneMatch(o -> o.startsWith(s) || s.startsWith(o))) {
                out.add(s);
            }
        }
        return new NameStones(out);
    }

    public int families() {
        return names.size();
    }

    public String name(int i) {
        return names.get(i);
    }

    /** The length of name {@code i}'s shortest clear start. */
    public int shortest(int i) {
        return shortest[i];
    }

    /** The fewest letters carved on all the stones. */
    public int fewest() {
        return fewest;
    }

    public int carved() {
        return carved;
    }

    /** The first stone of the last carving another family could read, or -1. */
    public int clash() {
        return clash;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Lists the families: the quest's first step. */
    public void list(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "list", "families");
        }
    }

    /** Carves one start per family, in order: AMBIGUOUS if another name shares it, WELL at the fewest, else LONG. */
    public Outcome carve(String eventId, String... starts) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (starts == null || starts.length != names.size()) {
            return Outcome.NOT_THERE;
        }
        for (int i = 0; i < starts.length; i++) {
            if (starts[i] == null || starts[i].isEmpty() || !names.get(i).startsWith(starts[i])) {
                return Outcome.NOT_THERE;
            }
        }
        events.add(eventId);
        int total = 0;
        clash = -1;
        for (int i = 0; i < starts.length; i++) {
            total += starts[i].length();
            for (int j = 0; j < names.size() && clash < 0; j++) {
                if (j != i && names.get(j).startsWith(starts[i])) {
                    clash = i;
                }
            }
        }
        carved = total;
        if (clash >= 0) {
            last = Outcome.AMBIGUOUS;
        } else {
            last = total == fewest ? Outcome.WELL : Outcome.LONG;
        }
        if (last == Outcome.WELL) {
            quest.apply(eventId, "carve", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the stones are carved well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperNameLines.THANKS;
        }
        return KeeperNameLines.line(this);
    }
}
