// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ArkDrydock.Life;
import com.daedalus.world.forge.TemperForge.Result;

import java.util.Arrays;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Quest q_forge_temper (contest gap G42): the Hephaestus Island arrival quest
 * (data/islands/hephaestus/ISLAND.md, beat 5). It asks the player to "prove you can dual-quench a tonic,
 * water the pens through a forge shift, and leave one ark plate stamped with your mark". The quest closes
 * when the Great Forge glows at full strength.
 *
 * <p>Steps, in the order Old Keeper Ysolde Anvilward asks for them: {@link Step#ARRIVAL} (drink from a clean
 * source, since the caldera doubles thirst), {@link Step#PENS} (every pen's trough filled to its daily need
 * within one forge shift), {@link Step#TONIC} (one dual-quench recipe from the island cookbook),
 * {@link Step#PLATE} (an ark plate stamped at the anvil, a {@link TemperForge} result with
 * {@code arkPlate}), and {@link Step#GLOW}. A step's progress may be made in any order. Pen and bed water
 * that does not finish a step before the shift ends is lost, because troughs and beds dry out.
 *
 * <p>The Great Forge Glow is the island's balance (mechanics.json {@code balance}): water 30, animals 30,
 * herb beds 30, dual tonic 10. The test reads that file to keep the weights in step. The host owns the
 * state; every event returns an {@link Outcome} and repeated events change nothing.
 */
public final class ForgeTemperQuest {

    public static final int GLOW_WATER = 30;
    public static final int GLOW_ANIMALS = 30;
    public static final int GLOW_HERBS = 30;
    public static final int GLOW_TEA = 10;
    /** Herb beds the glow counts; each needs 1 L a day (ISLAND.md). */
    public static final int BEDS = 3;
    public static final int BED_DL = 10;

    /** Clean drinking water on the island (mechanics.json water.sources marked clean). */
    public static final List<String> CLEAN_SOURCES = List.of("HotSpring_Clean", "SteamVentCatch", "RainCatch_Ash",
            "SaltStill_Basalt");
    /** The island's dual-quench cookbook (mechanics.json herbs, quench dual). */
    public static final List<String> DUAL_COOKBOOK = List.of("dual_riveters_temper", "dual_lava_runner",
            "dual_caldera_canteen", "dual_quench_tub_draught", "dual_drydock_shift", "dual_void_crossing",
            "dual_ash_well_antidote", "dual_scar_prospector");
    /** The six pens; their daily trough need is the island's own (see {@link Life#dlPerDay()}). */
    public static final List<Life> PENS = List.of(Life.EMBERHEN, Life.ASHGOAT, Life.FORGEOX, Life.LAVABOAR,
            Life.CINDERWOOL, Life.VENT_BEES);

    /** The quest's steps. */
    public enum Step { ARRIVAL, PENS, TONIC, PLATE, GLOW, COMPLETE }

    /** What an event did. */
    public enum Outcome { PROGRESS, STEP_DONE, ALREADY_DONE, DIRTY_WATER, NOT_A_PEN, NOT_DUAL, UNKNOWN_RECIPE, NOT_STAMPED,
        BAD_AMOUNT, NO_SUCH_BED, QUEST_COMPLETE }

    /** One player's q_forge_temper, held by the host. */
    public static final class Quest {

        private final Set<Step> done = EnumSet.noneOf(Step.class);
        private final Map<Life, Integer> trough = new EnumMap<>(Life.class);
        private final boolean[] beds = new boolean[BEDS];
        private boolean bedsGlowing;
        private String tonic = "";
        private int shifts;

        /** Drink at {@code source}; only clean water counts. */
        public Outcome drink(String source) {
            if (!CLEAN_SOURCES.contains(source)) {
                return Outcome.DIRTY_WATER;
            }
            return finish(Step.ARRIVAL);
        }

        /** Pour {@code dl} decilitres into {@code pen}'s trough during this shift. */
        public Outcome waterPen(Life pen, int dl) {
            if (!PENS.contains(pen)) {
                return Outcome.NOT_A_PEN;
            }
            if (dl <= 0) {
                return Outcome.BAD_AMOUNT;
            }
            if (done.contains(Step.PENS)) {
                return Outcome.ALREADY_DONE;
            }
            trough.merge(pen, dl, Integer::sum);
            for (Life p : PENS) {
                if (trough.getOrDefault(p, 0) < p.dlPerDay()) {
                    return Outcome.PROGRESS;
                }
            }
            return finish(Step.PENS);
        }

        /** Water herb bed {@code bed} (0..2) with {@code dl} decilitres this shift. */
        public Outcome waterBed(int bed, int dl) {
            if (bed < 0 || bed >= BEDS) {
                return Outcome.NO_SUCH_BED;
            }
            if (dl < BED_DL) {
                return Outcome.BAD_AMOUNT;
            }
            if (beds[bed]) {
                return Outcome.ALREADY_DONE;
            }
            beds[bed] = true;
            boolean all = true;
            for (boolean b : beds) {
                all &= b;
            }
            bedsGlowing |= all;
            return all ? checkGlow() : Outcome.PROGRESS;
        }

        /** Quench a brewed tonic; the step wants a recipe from the dual cookbook, quenched dual. */
        public Outcome quenchTonic(String recipe, TemperForge.Quench path) {
            if (!DUAL_COOKBOOK.contains(recipe)) {
                return Outcome.UNKNOWN_RECIPE;
            }
            if (path != TemperForge.Quench.DUAL) {
                return Outcome.NOT_DUAL;
            }
            if (tonic.isEmpty()) {
                tonic = recipe;
            }
            return finish(Step.TONIC);
        }

        /** Leave an ark plate at the drydock: it must bear a stamp from the anvil. */
        public Outcome leavePlate(Result forged) {
            if (!forged.arkPlate()) {
                return Outcome.NOT_STAMPED;
            }
            return finish(Step.PLATE);
        }

        /** The forge shift ends: unfinished troughs and beds dry out. */
        public void endShift() {
            shifts++;
            if (!done.contains(Step.PENS)) {
                trough.clear();
            }
            if (!bedsGlowing) {
                Arrays.fill(beds, false);
            }
        }

        private Outcome finish(Step s) {
            if (done.contains(Step.COMPLETE)) {
                return Outcome.ALREADY_DONE;
            }
            if (!done.add(s)) {
                return Outcome.ALREADY_DONE;
            }
            return checkGlow() == Outcome.QUEST_COMPLETE ? Outcome.QUEST_COMPLETE : Outcome.STEP_DONE;
        }

        /** Close the quest if every step is done and the glow is full (beds can supply the last 30). */
        Outcome checkGlow() {
            if (glow() == 100 && done.containsAll(EnumSet.of(Step.ARRIVAL, Step.PENS, Step.TONIC, Step.PLATE))) {
                done.add(Step.GLOW);
                done.add(Step.COMPLETE);
                return Outcome.QUEST_COMPLETE;
            }
            return Outcome.PROGRESS;
        }

        /** Great Forge Glow, 0..100: water running, pens producing, herb beds watered, dual tonic in pack. */
        public int glow() {
            int pens = 0;
            for (Life p : PENS) {
                if (done.contains(Step.PENS) || trough.getOrDefault(p, 0) >= p.dlPerDay()) {
                    pens++;
                }
            }
            int bedsWet = 0;
            for (boolean b : beds) {
                bedsWet += b ? 1 : 0;
            }
            return (done.contains(Step.ARRIVAL) ? GLOW_WATER : 0)
                    + GLOW_ANIMALS * pens / PENS.size()
                    + GLOW_HERBS * (bedsGlowing ? BEDS : bedsWet) / BEDS
                    + (tonic.isEmpty() ? 0 : GLOW_TEA);
        }

        /** The first step not yet done (COMPLETE once the glow is full). */
        public Step current() {
            for (Step s : Step.values()) {
                if (!done.contains(s)) {
                    return s;
                }
            }
            return Step.COMPLETE;
        }

        public boolean complete() {
            return done.contains(Step.COMPLETE);
        }

        public String tonic() {
            return tonic;
        }

        public int shifts() {
            return shifts;
        }

        /** One-line FTQ 1 summary, the same text as Encode() in DaedalusForgeTemperQuestCore.h. */
        public String encode() {
            StringBuilder flags = new StringBuilder();
            for (Step s : Step.values()) {
                flags.append(done.contains(s) ? '1' : '0');
            }
            return "FTQ 1 " + current() + " glow=" + glow() + " tonic=" + (tonic.isEmpty() ? "-" : tonic) + " shifts=" + shifts
                    + " done=" + flags;
        }
    }

    private ForgeTemperQuest() {
    }

    /** Old Keeper Ysolde Anvilward's line for the step the player is on. */
    public static String keeperLine(Step s) {
        return switch (s) {
            case ARRIVAL -> "Drink first, smith. The caldera takes water twice as fast as you think. Clean springs only.";
            case PENS -> "Hens, goats, oxen, boars, wool and bees. Fill every trough before the shift bell, or start again.";
            case TONIC -> "Brew it at the mortar, then magma and spring within ten breaths. One dual tonic, from the book.";
            case PLATE -> "Heat alone breaks. Water alone softens. Bring me a plate with your stamp on it.";
            case GLOW -> "Water the three beds. When water, pens, herbs and tonic all run, the Great Forge will tell you.";
            case COMPLETE -> "She glows. You are tempered, smith. The drydock will take your plates now.";
        };
    }
}
