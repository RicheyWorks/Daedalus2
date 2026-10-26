// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.song;

/**
 * Archivist Tamsin (first met in the record hunt, G46) keeps the catalogue. Lines follow the song quest; also listed
 * in STORY.md.
 */
public final class TamsinLines {
    public static final String GREETING = "Twelve records came off the arks. The island has never had one of its own. "
            + "Ask each of them for a verse, a step from the tune they love.";
    public static final String GATHER = "%d more verse%s. One step from each guest; no one gives two.";
    public static final String COMPOSE = "Now put them together: four or five herbs, each step a different verse, "
            + "and it has to come home. And don't hand me a copy of an ark tune in a new key, I'll know.";
    public static final String BREW = "Brew it once, so we know it holds. Then I'll press it.";
    public static final String THANKS = "Record thirteen. I've left room on the shelf for it since the hunt. "
            + "Here's the first pressing.";
    public static final String DONE = "Play it at the spring. It's the island's now.";

    private TamsinLines() {
    }

    /** The line for this song state. */
    public static String line(ThirteenthSong s) {
        var step = s.quest().currentStep();
        if (step == null) {
            return DONE;
        }
        long left = step.required() - s.quest().stepCount();
        return switch (s.quest().stepIndex()) {
            case 0 -> s.quest().stepCount() == 0 ? GREETING : String.format(GATHER, left, left == 1 ? "" : "s");
            case 1 -> COMPOSE;
            default -> BREW;
        };
    }
}
