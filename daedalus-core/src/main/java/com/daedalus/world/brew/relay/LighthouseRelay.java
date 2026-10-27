// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.relay;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 33 of the Youtube Master Island story, "The Lighthouse Relay" (quest {@code q_lighthouse_relay}). A signal
 * passes lamp to lamp from lighthouse 0 to the last lighthouse. Each sightline has a clarity; a relay is as clear as
 * its haziest sightline. {@link #clearest()} is the exact widest (bottleneck) path by a maximin Dijkstra. Sending a
 * relay at that clarity earns credit; a dimmer relay does not, and no relay at all gives {@link Outcome#NO_RELAY}.
 */
public final class LighthouseRelay {
    public static final String QUEST_ID = "q_lighthouse_relay";
    /** No sightline between these lamps. */
    public static final int NONE = 0;

    public enum Outcome { LIT, NO_SIGHT, NOT_THERE, WELL, DIM, NO_RELAY, DUPLICATE, IGNORED }

    private final int[][] clarity;
    private final int clearest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("light", "lamp", 1),
            new QuestProgress.Step("signal", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int at;
    private int haziest = Integer.MAX_VALUE;
    private Outcome last;

    /** @param clarity symmetric sightline clarities, {@link #NONE} where lamps cannot see each other */
    public LighthouseRelay(int[][] clarity) {
        if (clarity == null || clarity.length < 2) {
            throw new IllegalArgumentException("need at least two lighthouses");
        }
        int n = clarity.length;
        this.clarity = new int[n][];
        for (int i = 0; i < n; i++) {
            if (clarity[i].length != n || clarity[i][i] != NONE) {
                throw new IllegalArgumentException("square sightlines, none to the same lamp");
            }
            for (int j = 0; j < n; j++) {
                if (clarity[i][j] < 0 || clarity[i][j] != clarity[j][i]) {
                    throw new IllegalArgumentException("clarities are non-negative and run both ways");
                }
            }
            this.clarity[i] = clarity[i].clone();
        }
        clearest = widest();
    }

    /** A seeded coast of 4-7 lighthouses, each sightline present with probability one half at clarity 1-9. */
    public static LighthouseRelay seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x11647L);
        int n = 4 + rng.nextInt(4);
        int[][] c = new int[n][n];
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                if (rng.nextBoolean()) {
                    c[i][j] = 1 + rng.nextInt(9);
                    c[j][i] = c[i][j];
                }
            }
        }
        return new LighthouseRelay(c);
    }

    private int widest() {
        int n = clarity.length;
        int[] best = new int[n];
        boolean[] done = new boolean[n];
        best[0] = Integer.MAX_VALUE;
        for (int k = 0; k < n; k++) {
            int u = -1;
            for (int i = 0; i < n; i++) {
                if (!done[i] && best[i] > 0 && (u < 0 || best[i] > best[u])) {
                    u = i;
                }
            }
            if (u < 0) {
                break;
            }
            done[u] = true;
            for (int v = 0; v < n; v++) {
                if (clarity[u][v] != NONE) {
                    best[v] = Math.max(best[v], Math.min(best[u], clarity[u][v]));
                }
            }
        }
        return best[n - 1] > 0 ? best[n - 1] : -1;
    }

    public int lamps() {
        return clarity.length;
    }

    public int clarity(int a, int b) {
        return clarity[a][b];
    }

    /** The clarity of the clearest relay, or -1 when no relay reaches. */
    public int clearest() {
        return clearest;
    }

    public int at() {
        return at;
    }

    /** The haziest sightline of the relay so far. */
    public int haziest() {
        return haziest;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    private Outcome guard(String eventId) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        return events.contains(eventId) ? Outcome.DUPLICATE : null;
    }

    /** Passes the signal from the current lamp to another in sight. */
    public Outcome light(String eventId, int to) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (to < 0 || to >= clarity.length) {
            return Outcome.NOT_THERE;
        }
        if (clarity[at][to] == NONE) {
            return Outcome.NO_SIGHT;
        }
        events.add(eventId);
        haziest = Math.min(haziest, clarity[at][to]);
        at = to;
        last = Outcome.LIT;
        quest.apply(eventId, "light", "lamp");
        return Outcome.LIT;
    }

    /** Douses the relay and starts again from lighthouse 0. */
    public void restart() {
        at = 0;
        haziest = Integer.MAX_VALUE;
        last = null;
    }

    /** Sends the signal: NO_RELAY if none can reach, NOT_THERE before the far lamp, WELL at the clearest, else DIM. */
    public Outcome signal(String eventId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (clearest < 0) {
            return Outcome.NO_RELAY;
        }
        if (at != clarity.length - 1) {
            return Outcome.NOT_THERE;
        }
        events.add(eventId);
        last = haziest == clearest ? Outcome.WELL : Outcome.DIM;
        if (last == Outcome.WELL) {
            quest.apply(eventId, "signal", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the signal went well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperRelayLines.THANKS;
        }
        return KeeperRelayLines.line(this);
    }
}
