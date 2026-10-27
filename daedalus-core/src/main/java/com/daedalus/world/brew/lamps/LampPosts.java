// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lamps;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 54 of the Youtube Master Island story, "The Lamp Posts" (quest {@code q_lamp_posts}). Villagers hang lamps
 * along runs of fence posts for the spring fair; each lamp adds its glow to every post in its run. {@link #light(int)}
 * is each post's light from a difference array and a prefix sum, and {@link #brightest()} the most light on any post.
 * Pointing to a post that bright earns credit; a DIM post earns none.
 */
public final class LampPosts {
    public static final String QUEST_ID = "q_lamp_posts";

    public enum Outcome { BRIGHT, DIM, NOT_THERE, DUPLICATE, IGNORED }

    private final int posts;
    private final List<int[]> lamps;
    private final int[] light;
    private final int brightest;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("hang", "lamps", 1),
            new QuestProgress.Step("point", "bright", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private int pointed = -1;
    private Outcome last;

    /** Lamps {from, to, glow} over posts from..to inclusive. */
    public LampPosts(int posts, List<int[]> lamps) {
        if (posts <= 0 || lamps == null) {
            throw new IllegalArgumentException("at least one post");
        }
        this.posts = posts;
        this.lamps = new ArrayList<>();
        int[] diff = new int[posts + 1];
        for (int[] l : lamps) {
            if (l.length != 3 || l[0] < 0 || l[0] > l[1] || l[1] >= posts || l[2] <= 0) {
                throw new IllegalArgumentException("a lamp hangs over real posts and glows");
            }
            this.lamps.add(l.clone());
            diff[l[0]] += l[2];
            diff[l[1] + 1] -= l[2];
        }
        light = new int[posts];
        int run = 0;
        int best = 0;
        for (int p = 0; p < posts; p++) {
            run += diff[p];
            light[p] = run;
            best = Math.max(best, run);
        }
        brightest = best;
    }

    /** A seeded fence of 1-15 posts with 0-8 lamps of glow 1-6. */
    public static LampPosts seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x1A3BL);
        int n = 1 + rng.nextInt(15);
        int m = rng.nextInt(9);
        List<int[]> l = new ArrayList<>();
        for (int i = 0; i < m; i++) {
            int a = rng.nextInt(n);
            int b = a + rng.nextInt(n - a);
            l.add(new int[] {a, b, 1 + rng.nextInt(6)});
        }
        return new LampPosts(n, l);
    }

    public int posts() {
        return posts;
    }

    /** The lamps (copies). */
    public List<int[]> lamps() {
        List<int[]> out = new ArrayList<>();
        for (int[] l : lamps) {
            out.add(l.clone());
        }
        return out;
    }

    public int light(int post) {
        return light[post];
    }

    public int brightest() {
        return brightest;
    }

    public int pointed() {
        return pointed;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Watches the lamps go up: the quest's first step. */
    public void hang(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "hang", "lamps");
        }
    }

    /** Points to a post: BRIGHT if no post has more light, else DIM. */
    public Outcome point(String eventId, int post) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (post < 0 || post >= posts) {
            return Outcome.NOT_THERE;
        }
        events.add(eventId);
        pointed = post;
        last = light[post] == brightest ? Outcome.BRIGHT : Outcome.DIM;
        if (last == Outcome.BRIGHT) {
            quest.apply(eventId, "point", "bright");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the brightest post is found. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperLampLines.THANKS;
        }
        return KeeperLampLines.line(this);
    }
}
