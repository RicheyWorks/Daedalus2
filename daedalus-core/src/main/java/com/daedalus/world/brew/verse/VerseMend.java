// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.verse;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 22 of the Youtube Master Island story, "The Lost Verse" (quest {@code q_lost_verse}). The children's sung
 * verse has drifted from the true words carved on the boat. The player mends it letter by letter; it rings true when it
 * matches with the fewest changes. {@link #fewest()} is exact Levenshtein DP and {@link #bestScript()} walks it back.
 */
public final class VerseMend {
    public static final String QUEST_ID = "q_lost_verse";
    public static final int CHANGES_TO_MAKE = 3;
    static final String[] TRUE_WORDS = {"salt", "oar", "tide", "home", "gull", "wren", "ember", "spring", "lantern",
        "harbour"};

    public enum Outcome { CHANGED, BAD_EDIT, STARTED_OVER, TRUE, ROUGH, OFF, DUPLICATE, IGNORED }

    private final String carved;
    private final String sung;
    private final int[][] table;
    private String current;
    private int changes;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("change", "letter", CHANGES_TO_MAKE),
            new QuestProgress.Step("ring", "true", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private Outcome last;

    public VerseMend(String carved, String sung) {
        if (carved == null || sung == null || carved.isEmpty() || !carved.matches("[a-z]+") || !sung.matches("[a-z]*")) {
            throw new IllegalArgumentException("verses are lowercase letters");
        }
        this.carved = carved;
        this.sung = sung;
        this.current = sung;
        table = distanceTable(sung, carved);
    }

    /** A seeded drift: one true word with 1-3 random letter edits. */
    public static VerseMend seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x7E25EL);
        String word = TRUE_WORDS[rng.nextInt(TRUE_WORDS.length)];
        String s = word;
        int n = 1 + rng.nextInt(3);
        for (int i = 0; i < n; i++) {
            char c = (char) ('a' + rng.nextInt(26));
            int k = rng.nextInt(3);
            if (k == 0 && !s.isEmpty()) {
                s = new Edit(Edit.Kind.SWAP, rng.nextInt(s.length()), c).apply(s);
            } else if (k == 1 || s.length() <= 1) {
                s = new Edit(Edit.Kind.ADD, rng.nextInt(s.length() + 1), c).apply(s);
            } else {
                s = new Edit(Edit.Kind.DROP, rng.nextInt(s.length()), c).apply(s);
            }
        }
        return new VerseMend(word, s);
    }

    /** d[i][j] = fewest edits from the first i letters of a to the first j letters of b. */
    static int[][] distanceTable(String a, String b) {
        int[][] d = new int[a.length() + 1][b.length() + 1];
        for (int i = 0; i <= a.length(); i++) {
            d[i][0] = i;
        }
        for (int j = 0; j <= b.length(); j++) {
            d[0][j] = j;
        }
        for (int i = 1; i <= a.length(); i++) {
            for (int j = 1; j <= b.length(); j++) {
                int same = a.charAt(i - 1) == b.charAt(j - 1) ? 0 : 1;
                d[i][j] = Math.min(d[i - 1][j - 1] + same, Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1));
            }
        }
        return d;
    }

    public String carved() {
        return carved;
    }

    public String sung() {
        return sung;
    }

    public String current() {
        return current;
    }

    public int changes() {
        return changes;
    }

    /** The fewest letter edits from the sung verse to the carved one. */
    public int fewest() {
        return table[sung.length()][carved.length()];
    }

    /** One fewest-edit script, positions descending so each edit applies cleanly in order to the sung verse. */
    public List<Edit> bestScript() {
        List<Edit> out = new ArrayList<>();
        int i = sung.length();
        int j = carved.length();
        while (i > 0 || j > 0) {
            if (i > 0 && j > 0) {
                int same = sung.charAt(i - 1) == carved.charAt(j - 1) ? 0 : 1;
                if (table[i][j] == table[i - 1][j - 1] + same) {
                    if (same == 1) {
                        out.add(new Edit(Edit.Kind.SWAP, i - 1, carved.charAt(j - 1)));
                    }
                    i--;
                    j--;
                    continue;
                }
            }
            if (i > 0 && table[i][j] == table[i - 1][j] + 1) {
                out.add(new Edit(Edit.Kind.DROP, i - 1, ' '));
                i--;
            } else {
                out.add(new Edit(Edit.Kind.ADD, i, carved.charAt(j - 1)));
                j--;
            }
        }
        return out;
    }

    public QuestProgress quest() {
        return quest;
    }

    public Outcome last() {
        return last;
    }

    private Outcome guard(String eventId) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        return events.contains(eventId) ? Outcome.DUPLICATE : null;
    }

    /** Applies one letter edit to the verse being sung. */
    public Outcome change(String eventId, Edit edit) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        int limit = edit == null ? -1 : edit.kind() == Edit.Kind.ADD ? current.length() : current.length() - 1;
        if (edit == null || edit.pos() < 0 || edit.pos() > limit
                || (edit.kind() != Edit.Kind.DROP && (edit.letter() < 'a' || edit.letter() > 'z'))) {
            return Outcome.BAD_EDIT;
        }
        events.add(eventId);
        current = edit.apply(current);
        changes++;
        last = null;
        quest.apply(eventId, "change", "letter");
        return Outcome.CHANGED;
    }

    /** Goes back to the verse as the children sang it. */
    public Outcome startOver(String eventId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        events.add(eventId);
        current = sung;
        changes = 0;
        last = null;
        return Outcome.STARTED_OVER;
    }

    /** Sings it back: OFF while it differs from the carving, TRUE with the fewest changes, else ROUGH. */
    public Outcome ring(String eventId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (!current.equals(carved)) {
            return Outcome.OFF;
        }
        events.add(eventId);
        last = changes == fewest() ? Outcome.TRUE : Outcome.ROUGH;
        if (last == Outcome.TRUE) {
            quest.apply(eventId, "ring", "true");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once the verse rang true. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperVerseLines.THANKS;
        }
        return KeeperVerseLines.line(this);
    }
}
