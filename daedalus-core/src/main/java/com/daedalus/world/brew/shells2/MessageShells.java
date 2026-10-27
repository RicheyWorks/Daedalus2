// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.shells2;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 53 of the Youtube Master Island story, "The Message Shells" (quest {@code q_message_shells}). Each islander
 * always passes a message shell to the same neighbour. Starting from islander 0 the shell must eventually come round
 * again. {@link #tail()} is how many passes before it enters the loop and {@link #loop()} the loop's length, by
 * Floyd's tortoise and hare. Reading both right earns credit; a wrong reading earns none.
 */
public final class MessageShells {
    public static final String QUEST_ID = "q_message_shells";

    public enum Outcome { RIGHT, WRONG, DUPLICATE, IGNORED }

    private final int[] next;
    private final int tail;
    private final int loop;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("pass", "shell", 1),
            new QuestProgress.Step("read", "right", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private Outcome last;
    private int namedTail = -1;
    private int namedLoop = -1;

    /** {@code next[i]}: who islander i passes to. */
    public MessageShells(int... next) {
        if (next == null || next.length == 0) {
            throw new IllegalArgumentException("at least one islander");
        }
        for (int n : next) {
            if (n < 0 || n >= next.length) {
                throw new IllegalArgumentException("no such islander");
            }
        }
        this.next = next.clone();
        int slow = next[0];
        int fast = next[next[0]];
        while (slow != fast) {
            slow = next[slow];
            fast = next[next[fast]];
        }
        int mu = 0;
        slow = 0;
        while (slow != fast) {
            slow = next[slow];
            fast = next[fast];
            mu++;
        }
        int lam = 1;
        fast = next[slow];
        while (slow != fast) {
            fast = next[fast];
            lam++;
        }
        tail = mu;
        loop = lam;
    }

    /** A seeded island of 1-12 islanders passing at random. */
    public static MessageShells seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x5E11L);
        int[] n = new int[1 + rng.nextInt(12)];
        for (int i = 0; i < n.length; i++) {
            n[i] = rng.nextInt(n.length);
        }
        return new MessageShells(n);
    }

    public int islanders() {
        return next.length;
    }

    public int next(int i) {
        return next[i];
    }

    /** Passes before the shell first reaches the loop. */
    public int tail() {
        return tail;
    }

    /** Passes once round the loop. */
    public int loop() {
        return loop;
    }

    public int namedTail() {
        return namedTail;
    }

    public int namedLoop() {
        return namedLoop;
    }

    public Outcome last() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Passes the shell to see it go: the quest's first step. */
    public void pass(String eventId) {
        if (eventId != null && !eventId.isBlank() && events.add(eventId)) {
            quest.apply(eventId, "pass", "shell");
        }
    }

    /** Names the tail and the loop: RIGHT if both match, else WRONG. */
    public Outcome read(String eventId, int tailPasses, int loopPasses) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (!events.add(eventId)) {
            return Outcome.DUPLICATE;
        }
        namedTail = tailPasses;
        namedLoop = loopPasses;
        last = tailPasses == tail && loopPasses == loop ? Outcome.RIGHT : Outcome.WRONG;
        if (last == Outcome.RIGHT) {
            quest.apply(eventId, "read", "right");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the reading is right. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperShellLines.THANKS;
        }
        return KeeperShellLines.line(this);
    }
}
