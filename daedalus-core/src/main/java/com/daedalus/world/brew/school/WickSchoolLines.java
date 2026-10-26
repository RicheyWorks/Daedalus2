// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.school;

/** Old Wick (G62) keeps the schoolroom. Lines follow the school quest; also listed in STORY.md. */
public final class WickSchoolLines {
    public static final String GREETING = "Children from every far island, and not one of them knows a seed-song. "
            + "Teach them a tune, then come back to it before it slips. I've six lessons in me a day.";
    public static final String INTRODUCE = "%d more song%s to start them on.";
    public static final String SHELF = "%d pupil%s still to see through. Review what's due; the late ones forget.";
    public static final String THANKS = "Three of them sing all their songs without a record. That's how it was "
            + "on the arks. They'll teach the next ones.";
    public static final String DONE = "School's in every morning. Bring the little ones.";

    private WickSchoolLines() {
    }

    /** The line for this school state. */
    public static String line(SongSchool s) {
        var step = s.quest().currentStep();
        if (step == null) {
            return DONE;
        }
        long left = step.required() - s.quest().stepCount();
        if (s.quest().stepIndex() == 0) {
            return s.quest().stepCount() == 0 ? GREETING : String.format(INTRODUCE, left, left == 1 ? "" : "s");
        }
        return String.format(SHELF, left, left == 1 ? "" : "s");
    }
}
