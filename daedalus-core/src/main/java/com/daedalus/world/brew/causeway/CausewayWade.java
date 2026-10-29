// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.causeway;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Deque;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 98 of the Youtube Master Island story, "The Causeway Wade" (quest {@code q_causeway_wade}). The causeway is
 * a grid of dry stones (cost 0) and shallows (cost 1). {@link #wades()} is the fewest wet steps corner to corner, by
 * 0-1 BFS with a deque; {@link #straight()} is the trap, the route along the top and down the far side. Naming the
 * wades earns credit; a WRONG count, or an all-DRY causeway, earns none.
 */
public final class CausewayWade {
    public static final String QUEST_ID = "q_causeway_wade";

    public enum Outcome { RIGHT, WRONG, DRY, MALFORMED, DUPLICATE, IGNORED }

    private final List<String> rows;
    private final int wades;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("read", "causeway", 1),
            new QuestProgress.Step("count", "wades", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Causeway rows of equal length, '.' for a dry stone and '~' for a shallow. */
    public CausewayWade(List<String> rows) {
        if (rows == null || rows.isEmpty() || rows.stream().anyMatch(r -> r == null || r.isEmpty()
                || !r.matches("[.~]+") || r.length() != rows.get(0).length())) {
            throw new IllegalArgumentException("a real causeway");
        }
        this.rows = List.copyOf(rows);
        int h = rows.size();
        int w = rows.get(0).length();
        int[] dist = new int[h * w];
        Arrays.fill(dist, Integer.MAX_VALUE);
        dist[0] = wet(0, 0);
        Deque<Integer> dq = new ArrayDeque<>();
        dq.add(0);
        int[][] moves = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        while (!dq.isEmpty()) {
            int at = dq.pollFirst();
            int r = at / w;
            int c = at % w;
            for (int[] m : moves) {
                int nr = r + m[0];
                int nc = c + m[1];
                if (nr < 0 || nc < 0 || nr >= h || nc >= w) {
                    continue;
                }
                int cost = wet(nr, nc);
                int to = nr * w + nc;
                if (dist[at] + cost < dist[to]) {
                    dist[to] = dist[at] + cost;
                    if (cost == 0) {
                        dq.addFirst(to);
                    } else {
                        dq.addLast(to);
                    }
                }
            }
        }
        wades = dist[h * w - 1];
    }

    private int wet(int r, int c) {
        return rows.get(r).charAt(c) == '~' ? 1 : 0;
    }

    /** A seeded causeway of 2-3 rows and 2-4 columns, about a third shallows. */
    public static CausewayWade seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xCA05L);
        int h = 2 + rng.nextInt(2);
        int w = 2 + rng.nextInt(3);
        List<String> rs = new ArrayList<>();
        for (int r = 0; r < h; r++) {
            StringBuilder b = new StringBuilder();
            for (int c = 0; c < w; c++) {
                b.append(rng.nextInt(3) == 0 ? '~' : '.');
            }
            rs.add(b.toString());
        }
        return new CausewayWade(rs);
    }

    public List<String> rows() {
        return rows;
    }

    /** Fewest wet steps corner to corner, counting both corners (0-1 BFS). */
    public int wades() {
        return wades;
    }

    /** Wet steps along the top row and down the far column: the trap. */
    public int straight() {
        int w = rows.get(0).length();
        int n = 0;
        for (int c = 0; c < w; c++) {
            n += wet(0, c);
        }
        for (int r = 1; r < rows.size(); r++) {
            n += wet(r, w - 1);
        }
        return n;
    }

    /** Whether there are no shallows at all. */
    public boolean dry() {
        return rows.stream().noneMatch(r -> r.indexOf('~') >= 0);
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

    /** Reads the causeway: the quest's first step. */
    public void read(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "read", "causeway");
        }
    }

    /** Names the answer: RIGHT, WRONG, DRY or MALFORMED. */
    public Outcome count(String eventId, int guess) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        if (dry()) {
            last = Outcome.DRY;
            return last;
        }
        if (guess < 0) {
            last = Outcome.MALFORMED;
            return last;
        }
        named = guess;
        last = guess == wades() ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "count", "wades");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the answer is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperCausewayWade.THANKS;
        }
        return KeeperCausewayWade.line(this);
    }
}
