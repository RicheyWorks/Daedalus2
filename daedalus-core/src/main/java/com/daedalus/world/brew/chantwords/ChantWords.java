// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.chantwords;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 99 of the Youtube Master Island story, "The Chant Words" (quest {@code q_chant_words}). The festival chant
 * runs without breaks. {@link #total()} counts every place a blessing word is sung, overlaps included, with an
 * Aho-Corasick automaton in one pass; {@link #found()} is the trap, how many words turn up at all. Naming the total
 * earns credit; a WRONG count, or a SILENT chant, earns none.
 */
public final class ChantWords {
    public static final String QUEST_ID = "q_chant_words";

    public enum Outcome { RIGHT, WRONG, SILENT, MALFORMED, DUPLICATE, IGNORED }

    private final String chant;
    private final List<String> words;
    private final int total;
    private final int found;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "chant", 1),
            new QuestProgress.Step("count", "blessings", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** A chant of letters a-z and 1+ distinct, non-empty blessing words of letters a-z. */
    public ChantWords(String chant, List<String> words) {
        if (chant == null || !chant.matches("[a-z]*") || words == null || words.isEmpty()
                || words.stream().anyMatch(w -> w == null || !w.matches("[a-z]+"))
                || new HashSet<>(words).size() != words.size()) {
            throw new IllegalArgumentException("a real chant and words");
        }
        this.chant = chant;
        this.words = List.copyOf(words);
        int cap = 1 + words.stream().mapToInt(String::length).sum();
        int[][] next = new int[cap][26];
        int[] fail = new int[cap];
        long[] out = new long[cap];
        int nodes = 1;
        for (String w : this.words) {
            int at = 0;
            for (char ch : w.toCharArray()) {
                if (next[at][ch - 'a'] == 0) {
                    next[at][ch - 'a'] = nodes++;
                }
                at = next[at][ch - 'a'];
            }
            out[at]++;
        }
        ArrayDeque<Integer> q = new ArrayDeque<>();
        for (int c = 0; c < 26; c++) {
            if (next[0][c] != 0) {
                q.add(next[0][c]);
            }
        }
        while (!q.isEmpty()) {
            int u = q.poll();
            out[u] += out[fail[u]];
            for (int c = 0; c < 26; c++) {
                int v = next[u][c];
                if (v != 0) {
                    fail[v] = next[fail[u]][c];
                    q.add(v);
                } else {
                    next[u][c] = next[fail[u]][c];
                }
            }
        }
        long t = 0;
        int at = 0;
        for (char ch : chant.toCharArray()) {
            at = next[at][ch - 'a'];
            t += out[at];
        }
        total = (int) t;
        found = (int) this.words.stream().filter(chant::contains).count();
    }

    /** A seeded chant of 0-12 syllables a-c and 1-3 distinct words of 1-3 syllables. */
    public static ChantWords seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xC4A7L);
        int n = rng.nextInt(13);
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < n; i++) {
            b.append((char) ('a' + rng.nextInt(3)));
        }
        int k = 1 + rng.nextInt(3);
        List<String> ws = new ArrayList<>();
        while (ws.size() < k) {
            StringBuilder w = new StringBuilder();
            int len = 1 + rng.nextInt(3);
            for (int i = 0; i < len; i++) {
                w.append((char) ('a' + rng.nextInt(3)));
            }
            if (!ws.contains(w.toString())) {
                ws.add(w.toString());
            }
        }
        return new ChantWords(b.toString(), ws);
    }

    public String chant() {
        return chant;
    }

    public List<String> words() {
        return words;
    }

    /** Every place a blessing word is sung, overlaps included (Aho-Corasick). */
    public int total() {
        return total;
    }

    /** How many of the words turn up at all: the trap. */
    public int found() {
        return found;
    }

    /** Whether no blessing is sung. */
    public boolean silent() {
        return total == 0;
    }

    public int named() {
        return named;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Reads the chant: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "chant");
        }
    }

    /** Names the answer: RIGHT, WRONG, SILENT or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (silent()) {
            last = Outcome.SILENT;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == total() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "blessings");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperChantWords.THANKS;
        }
        return KeeperChantWords.line(this);
    }
}
