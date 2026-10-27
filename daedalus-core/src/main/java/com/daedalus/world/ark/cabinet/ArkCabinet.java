// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

/**
 * G493 Ark Games Cabinet: a player-facing arcade cabinet that bundles the most showable ark turn games behind one
 * menu. Each slot builds a fresh {@link ArkCabinetGame} adapter over a merged ark piece. The cabinet can play the
 * second seat itself from the piece's own solver ({@link ArkCabinetGame#hint()}), so one player can sit down and play,
 * and {@link #autoplay} runs scripted cabinet-vs-cabinet attract-mode demos.
 *
 * <p>Daedalus hook: the cabinet stands on the ark's mess deck as an in-world arcade machine ({@link #ARCADE_NAME},
 * {@link #arcadeDescription()}); finishing any game on it completes quest {@link #QUEST_ID}. Adding a game is one
 * {@link #register} call with a supplier; nothing else changes.
 */
public final class ArkCabinet {

    /** Quest id for the in-world cabinet hook. */
    public static final String QUEST_ID = "q_ark_cabinet";
    /** In-world name of the arcade machine. */
    public static final String ARCADE_NAME = "The Ark Games Cabinet";
    /** Safety cap on turns for one autoplay demo. */
    public static final int MAX_DEMO_TURNS = 400;

    /** One menu slot. */
    public static final class Slot {
        private final String id;
        private final String title;
        private final String blurb;
        private final Supplier<ArkCabinetGame> maker;

        Slot(String id, String title, String blurb, Supplier<ArkCabinetGame> maker) {
            this.id = id;
            this.title = title;
            this.blurb = blurb;
            this.maker = maker;
        }

        /** Slot id typed at the menu. */
        public String id() {
            return id;
        }

        /** Menu title. */
        public String title() {
            return title;
        }

        /** One-line pitch shown on the menu. */
        public String blurb() {
            return blurb;
        }

        /** A fresh game at its starting position. */
        public ArkCabinetGame open() {
            return maker.get();
        }
    }

    private final Map<String, Slot> slots = new LinkedHashMap<>();

    /** An empty cabinet; use {@link #standard()} for the stocked one. */
    public ArkCabinet() {
        // empty registry
    }

    /** The stocked ark cabinet with every bundled game. */
    public static ArkCabinet standard() {
        ArkCabinet c = new ArkCabinet();
        c.register("chalk", "The Chalk Grid", "noughts and crosses on the deck, 3 in a row (G421)", ChalkGridGame::new);
        c.register("hammock", "The Hammock Rows", "drop hammocks, 3 in a line on a 4x4 rack (G416)",
            HammockRowsGame::new);
        c.register("seeds", "The Seed Trays", "Kalah with 3 trays of 3 seeds a side (G418)", SeedTraysGame::new);
        c.register("hardtack", "The Hardtack Bar", "Chomp: do not eat the soaked corner (G414)", HardtackBarGame::new);
        return c;
    }

    /** Adds a slot; the id must be new and non-blank. */
    public void register(String id, String title, String blurb, Supplier<ArkCabinetGame> maker) {
        if (id == null || id.isBlank() || maker == null || slots.containsKey(id)) {
            throw new IllegalArgumentException("bad or duplicate slot id");
        }
        slots.put(id, new Slot(id, title, blurb, maker));
    }

    /** Slots in menu order, unmodifiable. */
    public List<Slot> slots() {
        return Collections.unmodifiableList(new ArrayList<>(slots.values()));
    }

    /** A fresh game from the slot with this id. */
    public ArkCabinetGame open(String id) {
        Slot s = slots.get(id);
        if (s == null) {
            throw new IllegalArgumentException("no game " + id);
        }
        return s.open();
    }

    /** The menu as text, one numbered line per slot. */
    public String menu() {
        StringBuilder sb = new StringBuilder(ARCADE_NAME).append('\n');
        int i = 1;
        for (Slot s : slots.values()) {
            sb.append(i++).append(") ").append(s.id).append(" - ").append(s.title).append(": ").append(s.blurb)
                .append('\n');
        }
        return sb.toString();
    }

    /** Text the world shows when a player looks at the machine. */
    public String arcadeDescription() {
        return ARCADE_NAME + ": a brass-and-driftwood arcade machine on the ark's mess deck with " + slots.size()
            + " crew games. Pick a game, play the cabinet, and finish one to complete " + QUEST_ID + ".";
    }

    /**
     * Cabinet-vs-cabinet attract mode: plays the solver's hint for both seats until the game ends.
     *
     * @return the moves played, unmodifiable
     */
    public static List<String> autoplay(ArkCabinetGame game) {
        List<String> moves = new ArrayList<>();
        for (int t = 0; t < MAX_DEMO_TURNS && !game.over(); t++) {
            String m = game.hint();
            if (!game.play(m)) {
                throw new IllegalStateException("hint was not legal: " + m);
            }
            moves.add(m);
        }
        return Collections.unmodifiableList(moves);
    }

    /** Quest q_ark_cabinet: done once the player has finished a game on the cabinet. */
    public static boolean quest(ArkCabinetGame game) {
        return game != null && game.over();
    }
}
