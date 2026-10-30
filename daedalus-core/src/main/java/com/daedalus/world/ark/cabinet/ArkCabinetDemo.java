// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * Runnable entry point for the Ark Games Cabinet. With no arguments it is an interactive keyboard game: pick a slot,
 * you are player 1 (X / first seat) and the cabinet plays player 2. With {@code --demo} it plays every slot
 * cabinet-vs-cabinet and prints the transcripts. Type {@code hint} for a suggestion or {@code quit} to leave.
 */
public final class ArkCabinetDemo {

    private ArkCabinetDemo() {
    }

    /** Entry point. */
    public static void main(String[] args) throws IOException {
        PrintStream out = new PrintStream(System.out, true, StandardCharsets.UTF_8);
        ArkCabinet cab = ArkCabinet.standard();
        if (args.length > 0 && "--demo".equals(args[0])) {
            demo(cab, out);
            return;
        }
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        play(cab, in, out);
    }

    /** Plays every slot cabinet-vs-cabinet. */
    public static void demo(ArkCabinet cab, PrintStream out) {
        out.println(cab.arcadeDescription());
        for (ArkCabinet.Slot s : cab.slots()) {
            ArkCabinetGame g = s.open();
            List<String> moves = ArkCabinet.autoplay(g);
            out.println("== " + s.title() + " ==");
            out.println("moves: " + String.join(" ", moves));
            out.print(g.render());
            out.println(g.winner() == 0 ? "result: draw" : "result: player " + g.winner() + " wins");
        }
    }

    /** One interactive session read from {@code in}. */
    public static void play(ArkCabinet cab, BufferedReader in, PrintStream out) throws IOException {
        out.print(cab.menu());
        out.println("Pick a game id:");
        String id = in.readLine();
        if (id == null) {
            return;
        }
        ArkCabinetGame g;
        try {
            g = cab.open(id.trim());
        } catch (IllegalArgumentException e) {
            out.println("No such game.");
            return;
        }
        out.println(g.rules());
        while (!g.over()) {
            out.print(g.render());
            if (g.toMove() == 2) {
                String m = g.hint();
                g.play(m);
                out.println("Cabinet plays " + m);
                continue;
            }
            out.println("Your move " + g.legalMoves() + ":");
            String line = in.readLine();
            if (line == null || "quit".equalsIgnoreCase(line.trim())) {
                return;
            }
            if ("hint".equalsIgnoreCase(line.trim())) {
                out.println("Try " + g.hint());
            } else if (!g.play(line)) {
                out.println("Not a legal move.");
            }
        }
        out.print(g.render());
        out.println(g.winner() == 0 ? "Draw." : g.winner() == 1 ? "You win!" : "The cabinet wins.");
        out.println("Quest " + ArkCabinet.QUEST_ID + (ArkCabinet.quest(g) ? " complete." : " open."));
    }
}
