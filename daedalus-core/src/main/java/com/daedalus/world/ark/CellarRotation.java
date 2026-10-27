// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import com.daedalus.world.ark.ArkCellar.Lot;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * G203 Cellar Rotation: serve the ark crew's daily tonic demand from the G196 cellar shelf.
 *
 * <p>A lot is usable on day {@code d} while {@code d - bottledDay <= tier.shelfDays()}, the same
 * rule {@link ArkCellar} uses. {@link Policy#EARLIEST_EXPIRY} hands out the bottle that spoils
 * soonest, which maximises demand served (unit jobs with deadlines); {@link Policy#FRESHEST}
 * is the tempting newest-first habit that lets older bottles spoil. Plain data, deterministic.
 */
public final class CellarRotation {

    public static final String QUEST_ID = "q_cellar_rotation";

    public enum Policy { EARLIEST_EXPIRY, FRESHEST }

    public record Result(int served, int missed, int wasted, List<Integer> servedPerDay,
                         List<Lot> remaining) {
        public Result {
            servedPerDay = List.copyOf(servedPerDay);
            remaining = List.copyOf(remaining);
        }
    }

    private CellarRotation() { }

    public static int expiryDay(Lot l) {
        return l.bottledDay() + l.tier().shelfDays();
    }

    public static boolean usable(Lot l, int day, int minLevel) {
        return l.tier().level() >= minLevel && day >= l.bottledDay() && day <= expiryDay(l);
    }

    public static Result serve(List<Lot> shelf, int startDay, List<Integer> demand, int minLevel,
                               Policy policy) {
        Comparator<Lot> order = policy == Policy.EARLIEST_EXPIRY
                ? Comparator.comparingInt(CellarRotation::expiryDay)
                        .thenComparingInt(l -> l.tier().level())
                        .thenComparingInt(Lot::bottledDay)
                : Comparator.comparingInt(Lot::bottledDay).reversed()
                        .thenComparing(Comparator.comparingInt((Lot l) -> l.tier().level()).reversed());
        List<Lot> left = new ArrayList<>(shelf);
        List<Integer> perDay = new ArrayList<>();
        int served = 0;
        int missed = 0;
        int wasted = 0;
        for (int i = 0; i < demand.size(); i++) {
            int day = startDay + i;
            int want = demand.get(i);
            if (want < 0) {
                throw new IllegalArgumentException("negative demand");
            }
            int got = 0;
            while (got < want) {
                Lot pick = left.stream().filter(l -> usable(l, day, minLevel)).min(order).orElse(null);
                if (pick == null) {
                    break;
                }
                left.remove(pick);
                got++;
            }
            served += got;
            missed += want - got;
            perDay.add(got);
            List<Lot> keep = new ArrayList<>();
            for (Lot l : left) {
                if (expiryDay(l) <= day) {
                    wasted++;
                } else {
                    keep.add(l);
                }
            }
            left = keep;
        }
        return new Result(served, missed, wasted, perDay, left);
    }

    /** Quest q_cellar_rotation: meet every day's demand from the shelf. */
    public static boolean quest(List<Lot> shelf, int startDay, List<Integer> demand, int minLevel) {
        return serve(shelf, startDay, demand, minLevel, Policy.EARLIEST_EXPIRY).missed() == 0;
    }
}
