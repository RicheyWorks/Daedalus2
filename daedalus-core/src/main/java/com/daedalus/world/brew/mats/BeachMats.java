// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.mats;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 58 of the Youtube Master Island story, "The Beach Mats" (quest {@code q_beach_mats}). Drying mats lie along
 * the beach as half-open spans [from, to) of paces, some overlapping; {@link #merged()} joins them by sorting and
 * sweeping, and {@link #covered()} is the sand they cover. Naming the cover earns credit; a MISCOUNT earns none.
 */
public final class BeachMats {
    public static final String QUEST_ID = "q_beach_mats";

    public enum Outcome { COVERED, MISCOUNT, DUPLICATE, IGNORED }

    private final List<int[]> mats;
    private final List<int[]> merged;
    private final int covered;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("lay", "mats", 1),
            new QuestProgress.Step("measure", "cover", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int named = -1;
    private Outcome last;

    /** Mats {from, to} with from &lt; to, half-open. */
    public BeachMats(List<int[]> mats) {
        if (mats == null) {
            throw new IllegalArgumentException("a beach of mats");
        }
        this.mats = new ArrayList<>();
        for (int[] m : mats) {
            if (m.length != 2 || m[0] < 0 || m[0] >= m[1]) {
                throw new IllegalArgumentException("a mat spans at least one pace");
            }
            this.mats.add(m.clone());
        }
        List<int[]> sorted = new ArrayList<>(this.mats);
        sorted.sort(Comparator.comparingInt(m -> m[0]));
        List<int[]> out = new ArrayList<>();
        for (int[] m : sorted) {
            if (!out.isEmpty() && m[0] <= out.get(out.size() - 1)[1]) {
                int[] top = out.get(out.size() - 1);
                top[1] = Math.max(top[1], m[1]);
            } else {
                out.add(m.clone());
            }
        }
        int sum = 0;
        for (int[] m : out) {
            sum += m[1] - m[0];
        }
        merged = out;
        covered = sum;
    }

    /** A seeded beach of 0-8 mats within 0-20 paces, each 1-6 long. */
    public static BeachMats seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x3A75L);
        int n = rng.nextInt(9);
        List<int[]> m = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            int a = rng.nextInt(15);
            m.add(new int[] {a, a + 1 + rng.nextInt(6)});
        }
        return new BeachMats(m);
    }

    /** The mats (copies). */
    public List<int[]> mats() {
        List<int[]> out = new ArrayList<>();
        for (int[] m : mats) {
            out.add(m.clone());
        }
        return out;
    }

    /** The merged spans, sorted, disjoint and not touching (copies). */
    public List<int[]> merged() {
        List<int[]> out = new ArrayList<>();
        for (int[] m : merged) {
            out.add(m.clone());
        }
        return out;
    }

    public int covered() {
        return covered;
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

    /** Watches the mats go down: the quest's first step. */
    public void lay(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "lay", "mats");
        }
    }

    /** Names the cover in paces: COVERED if right, else MISCOUNT. */
    public Outcome measure(String eventId, int paces) {
        if (eventId == null || eventId.isBlank() || paces < 0) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        events.add(eventId);
        named = paces;
        last = paces == covered ? Outcome.COVERED : Outcome.MISCOUNT;
        if (last == Outcome.COVERED) {
            quest.apply(eventId, "measure", "cover");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the cover is named. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperMatLines.THANKS;
        }
        return KeeperMatLines.line(this);
    }
}
