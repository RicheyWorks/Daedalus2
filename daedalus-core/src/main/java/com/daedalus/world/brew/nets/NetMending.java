// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.nets;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 31 of the Youtube Master Island story, "The Net Mending" (quest {@code q_net_mending}). Each mender knows
 * the knots of some torn nets. Every mender takes at most one net and every net at most one mender. {@link #most()}
 * is the exact maximum bipartite matching by augmenting paths (Kuhn). Mending that many earns credit; fewer does not,
 * and a mender put on a net whose knot they do not know is refused.
 */
public final class NetMending {
    public static final String QUEST_ID = "q_net_mending";
    public static final int NONE = -1;

    public enum Outcome { ASSIGNED, CANT_KNOT, TAKEN, NOT_THERE, WELL, FEW, DUPLICATE, IGNORED }

    private final boolean[][] knows;
    private final int most;
    private final int[] netOf;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("assign", "net", 1),
            new QuestProgress.Step("mend", "well", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private Outcome last;

    /** @param knows knows[mender][net] is true when the mender knows that net's knot */
    public NetMending(boolean[][] knows) {
        if (knows == null || knows.length == 0 || knows[0].length == 0) {
            throw new IllegalArgumentException("at least one mender and one net");
        }
        int k = knows[0].length;
        this.knows = new boolean[knows.length][];
        for (int i = 0; i < knows.length; i++) {
            if (knows[i].length != k) {
                throw new IllegalArgumentException("every mender row covers every net");
            }
            this.knows[i] = knows[i].clone();
        }
        netOf = new int[knows.length];
        Arrays.fill(netOf, NONE);
        most = kuhn();
    }

    /** A seeded loft of 2-5 menders and 2-5 nets, each knot known with probability 0.4. */
    public static NetMending seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x4E75L);
        boolean[][] k = new boolean[2 + rng.nextInt(4)][2 + rng.nextInt(4)];
        for (boolean[] row : k) {
            for (int j = 0; j < row.length; j++) {
                row[j] = rng.nextInt(5) < 2;
            }
        }
        return new NetMending(k);
    }

    private int kuhn() {
        int[] menderOf = new int[nets()];
        Arrays.fill(menderOf, NONE);
        int count = 0;
        for (int m = 0; m < menders(); m++) {
            if (augment(m, new boolean[nets()], menderOf)) {
                count++;
            }
        }
        return count;
    }

    private boolean augment(int m, boolean[] seen, int[] menderOf) {
        for (int n = 0; n < nets(); n++) {
            if (knows[m][n] && !seen[n]) {
                seen[n] = true;
                if (menderOf[n] == NONE || augment(menderOf[n], seen, menderOf)) {
                    menderOf[n] = m;
                    return true;
                }
            }
        }
        return false;
    }

    public int menders() {
        return knows.length;
    }

    public int nets() {
        return knows[0].length;
    }

    public boolean knows(int mender, int net) {
        return knows[mender][net];
    }

    /** The most nets that can be mended at once. */
    public int most() {
        return most;
    }

    public int netOf(int mender) {
        return netOf[mender];
    }

    public int assigned() {
        return (int) Arrays.stream(netOf).filter(x -> x != NONE).count();
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

    /** Puts a mender on a net, or takes them off with {@link #NONE}. */
    public Outcome assign(String eventId, int mender, int net) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (mender < 0 || mender >= menders() || net < NONE || net >= nets()) {
            return Outcome.NOT_THERE;
        }
        if (net != NONE) {
            if (!knows[mender][net]) {
                return Outcome.CANT_KNOT;
            }
            for (int m = 0; m < menders(); m++) {
                if (m != mender && netOf[m] == net) {
                    return Outcome.TAKEN;
                }
            }
        }
        events.add(eventId);
        netOf[mender] = net;
        last = null;
        if (net != NONE) {
            quest.apply(eventId, "assign", "net");
        }
        return Outcome.ASSIGNED;
    }

    /** Sets the menders to work: WELL when as many nets are mended as possible, else FEW. */
    public Outcome mend(String eventId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        events.add(eventId);
        last = assigned() == most ? Outcome.WELL : Outcome.FEW;
        if (last == Outcome.WELL) {
            quest.apply(eventId, "mend", "well");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the nets were mended well. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperNetLines.THANKS;
        }
        return KeeperNetLines.line(this);
    }
}
