// SPDX-License-Identifier: MIT

package com.daedalus.world.colony;

import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * Java twin of the PORT09 ordered quest core ({@code DaedalusPortalQuestCore.h}, tested by
 * {@code engines/unreal/core-test/portal_quest_core_test.cpp}): same steps, limits and results, so the Java
 * server and the Unreal host settle quests the same way. Per player, caller supplies authoritative events;
 * no inventory, persistence or networking here.
 *
 * <p>Rules (identical to the C++ core): 1 to 32 steps, each with type, target and a positive count; events need an
 * id (1 to 128 chars) and a positive amount; an event id counts once, ever (at most 512 ids, never evicted);
 * only the current step advances; the reward can be claimed once, after completion.
 */
public final class QuestProgress {
    public static final int MAX_STEPS = 32;
    public static final int MAX_EVENTS = 512;
    public static final int MAX_EVENT_ID = 128;

    public enum Result { IGNORED, DUPLICATE, PROGRESSED, COMPLETED, CAPACITY_REACHED }

    public record Step(String type, String target, long required) {
        public Step {
            Objects.requireNonNull(type, "type");
            Objects.requireNonNull(target, "target");
        }
    }

    private final List<Step> steps;
    private final String invalid;
    private final Set<String> seen = new HashSet<>();
    private int current;
    private long count;
    private boolean rewardClaimed;

    public QuestProgress(List<Step> steps) {
        String why = "";
        if (steps == null || steps.isEmpty() || steps.size() > MAX_STEPS) {
            why = "Quest needs one to thirty-two steps";
        } else {
            for (Step s : steps) {
                if (s.type().isEmpty() || s.target().isEmpty() || s.required() <= 0) {
                    why = "Quest step needs type, target and positive count";
                    break;
                }
            }
        }
        this.invalid = why;
        this.steps = why.isEmpty() ? List.copyOf(steps) : List.of();
    }

    public boolean valid() {
        return invalid.isEmpty();
    }

    public String why() {
        return invalid;
    }

    public Result apply(String eventId, String type, String target) {
        return apply(eventId, type, target, 1);
    }

    public Result apply(String eventId, String type, String target, long amount) {
        if (!valid() || eventId == null || eventId.isEmpty() || eventId.length() > MAX_EVENT_ID || amount <= 0) {
            return Result.IGNORED;
        }
        if (seen.contains(eventId)) {
            return Result.DUPLICATE;
        }
        if (complete()) {
            return Result.IGNORED;
        }
        Step s = steps.get(current);
        if (!s.type().equals(type) || !s.target().equals(target)) {
            return Result.IGNORED;
        }
        if (seen.size() >= MAX_EVENTS) {
            return Result.CAPACITY_REACHED;
        }
        seen.add(eventId);
        long remaining = s.required() - count;
        count += Math.min(amount, remaining);
        if (count == s.required()) {
            current++;
            count = 0;
        }
        return complete() ? Result.COMPLETED : Result.PROGRESSED;
    }

    public boolean complete() {
        return valid() && current == steps.size();
    }

    public int stepIndex() {
        return current;
    }

    public long stepCount() {
        return count;
    }

    /** The step waiting for an event, or null when complete or invalid. */
    public Step currentStep() {
        return complete() || !valid() ? null : steps.get(current);
    }

    /** A signal only: true once, after completion. The host persists and awards atomically. */
    public boolean claimReward() {
        if (!complete() || rewardClaimed) {
            return false;
        }
        rewardClaimed = true;
        return true;
    }
}
