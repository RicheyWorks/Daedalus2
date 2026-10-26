// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.chests;

import com.daedalus.world.brew.letters.Destination;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 18 of the Youtube Master Island story, "The Keepsake Chests" (quest {@code q_keepsake_chests}). Each sailing
 * family packs one sea chest with a weight limit from its house list of keepsakes. A closed chest is warm when its
 * memory equals the best that fits; {@link #best(String)} is exact 0/1 knapsack dynamic programming.
 */
public final class KeepsakeChests {
    public static final String QUEST_ID = "q_keepsake_chests";
    public static final int KEEPSAKES_TO_PACK = 3;
    static final String[] NAMES = {"quilt", "kettle", "fiddle", "seed_tin", "lantern", "map", "clock", "boots",
        "letters", "jar_of_sand", "spoon", "shell"};

    public enum Outcome { PACKED, UNPACKED, ALREADY_PACKED, NOT_PACKED, TOO_HEAVY, UNKNOWN, WARM, HEAVY, DUPLICATE,
        IGNORED }

    /** A family's chest: its house list and weight limit. */
    public record Chest(String family, List<Keepsake> house, int capacity) {
        public Chest {
            house = List.copyOf(house);
            if (capacity <= 0 || house.isEmpty()) {
                throw new IllegalArgumentException("bad chest " + family);
            }
        }
    }

    private final Map<String, Chest> chests = new LinkedHashMap<>();
    private final Map<String, Map<String, Keepsake>> packed = new LinkedHashMap<>();
    private final Map<String, List<Keepsake>> best = new LinkedHashMap<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("pack", "keepsake", KEEPSAKES_TO_PACK),
            new QuestProgress.Step("close", "warm", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private Outcome last;

    public KeepsakeChests(List<Chest> list) {
        for (Chest c : list) {
            if (chests.put(c.family(), c) != null) {
                throw new IllegalArgumentException("duplicate family " + c.family());
            }
            Set<String> ids = new HashSet<>();
            c.house().forEach(k -> {
                if (!ids.add(k.id())) {
                    throw new IllegalArgumentException("duplicate keepsake " + k.id());
                }
            });
            packed.put(c.family(), new LinkedHashMap<>());
            best.put(c.family(), List.copyOf(knapsack(c.house(), c.capacity())));
        }
        if (chests.isEmpty()) {
            throw new IllegalArgumentException("no families");
        }
    }

    /** One chest per far-island family, each with a seeded house list of 6-8 keepsakes. */
    public static KeepsakeChests seeded(List<Destination> destinations, long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xC4E57L);
        List<Chest> out = new ArrayList<>();
        for (Destination d : destinations) {
            int n = 6 + rng.nextInt(3);
            List<Keepsake> house = new ArrayList<>();
            int total = 0;
            for (int i = 0; i < n; i++) {
                Keepsake k = new Keepsake(NAMES[(i * 5 + rng.nextInt(NAMES.length)) % NAMES.length] + "_" + i,
                        1 + rng.nextInt(9), 1 + rng.nextInt(20));
                house.add(k);
                total += k.weight();
            }
            out.add(new Chest(d.id(), house, Math.max(1, total * (35 + rng.nextInt(26)) / 100)));
        }
        return new KeepsakeChests(out);
    }

    /** Exact 0/1 knapsack: table[i][w] = best memory from the first i keepsakes within weight w, then walk back. */
    static List<Keepsake> knapsack(List<Keepsake> items, int cap) {
        int n = items.size();
        int[][] t = new int[n + 1][cap + 1];
        for (int i = 1; i <= n; i++) {
            Keepsake k = items.get(i - 1);
            for (int w = 0; w <= cap; w++) {
                t[i][w] = t[i - 1][w];
                if (k.weight() <= w) {
                    t[i][w] = Math.max(t[i][w], t[i - 1][w - k.weight()] + k.memory());
                }
            }
        }
        List<Keepsake> chosen = new ArrayList<>();
        for (int i = n, w = cap; i > 0; i--) {
            if (t[i][w] != t[i - 1][w]) {
                Keepsake k = items.get(i - 1);
                chosen.add(0, k);
                w -= k.weight();
            }
        }
        return chosen;
    }

    public List<Chest> chests() {
        return List.copyOf(chests.values());
    }

    /** One best set of keepsakes for this family. */
    public List<Keepsake> best(String family) {
        return best.get(family);
    }

    public int bestMemory(String family) {
        return best.get(family).stream().mapToInt(Keepsake::memory).sum();
    }

    public int capacity(String family) {
        return chests.get(family).capacity();
    }

    public List<Keepsake> packed(String family) {
        return List.copyOf(packed.get(family).values());
    }

    public int weight(String family) {
        return packed.get(family).values().stream().mapToInt(Keepsake::weight).sum();
    }

    public int memory(String family) {
        return packed.get(family).values().stream().mapToInt(Keepsake::memory).sum();
    }

    public QuestProgress quest() {
        return quest;
    }

    public Outcome last() {
        return last;
    }

    private Outcome guard(String eventId, String family) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        return chests.containsKey(family) ? null : Outcome.UNKNOWN;
    }

    private Keepsake item(String family, String id) {
        return chests.get(family).house().stream().filter(k -> k.id().equals(id)).findFirst().orElse(null);
    }

    /** Puts a keepsake in the family's chest, if it still fits. */
    public Outcome pack(String eventId, String family, String keepsakeId) {
        Outcome g = guard(eventId, family);
        if (g != null) {
            return g;
        }
        Keepsake k = item(family, keepsakeId);
        if (k == null) {
            return Outcome.UNKNOWN;
        }
        if (packed.get(family).containsKey(k.id())) {
            return Outcome.ALREADY_PACKED;
        }
        if (weight(family) + k.weight() > capacity(family)) {
            return Outcome.TOO_HEAVY;
        }
        events.add(eventId);
        packed.get(family).put(k.id(), k);
        last = null;
        quest.apply(eventId, "pack", "keepsake");
        return Outcome.PACKED;
    }

    /** Takes a keepsake back out. */
    public Outcome unpack(String eventId, String family, String keepsakeId) {
        Outcome g = guard(eventId, family);
        if (g != null) {
            return g;
        }
        if (packed.get(family).remove(keepsakeId) == null) {
            return Outcome.NOT_PACKED;
        }
        events.add(eventId);
        last = null;
        return Outcome.UNPACKED;
    }

    /** Closes the chest: warm if it holds the most memory that fits, else heavy-hearted. */
    public Outcome close(String eventId, String family) {
        Outcome g = guard(eventId, family);
        if (g != null) {
            return g;
        }
        events.add(eventId);
        last = memory(family) == bestMemory(family) ? Outcome.WARM : Outcome.HEAVY;
        if (last == Outcome.WARM) {
            quest.apply(eventId, "close", "warm");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once a chest closed warm. */
    public String talk(String eventId, String family) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperChestLines.THANKS;
        }
        return KeeperChestLines.line(this, family);
    }
}
