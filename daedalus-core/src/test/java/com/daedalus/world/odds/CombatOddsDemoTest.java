package com.daedalus.world.odds;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;

class CombatOddsDemoTest {

    @Test
    void demoIsRepeatableAndShowsTheForgeEffect() {
        String a = CombatOddsDemo.run(7, 4000);
        assertEquals(a, CombatOddsDemo.run(7, 4000));
        String[] lines = a.split("\n");
        assertEquals(6, lines.length);
        assertTrue(lines[0].startsWith("DFW 1 SWORD BRONZE"));
        assertTrue(lines[3].startsWith("DFW 1 SWORD STEEL"));
        assertTrue(pwin(lines[4]) > pwin(lines[1]), a);
    }

    private static double pwin(String line) {
        int i = line.indexOf("pwin=") + 5;
        return Double.parseDouble(line.substring(i, line.indexOf(' ', i)));
    }

    @Test
    void mainPrintsTheReport() {
        PrintStream old = System.out;
        ByteArrayOutputStream buf = new ByteArrayOutputStream();
        System.setOut(new PrintStream(buf, true, StandardCharsets.UTF_8));
        try {
            CombatOddsDemo.main(new String[] {"3", "500"});
            CombatOddsDemo.main(new String[0]);
        } finally {
            System.setOut(old);
        }
        String out = buf.toString(StandardCharsets.UTF_8);
        assertTrue(out.contains("DOR 1 seed=3 trials=500"));
        assertTrue(out.contains("DOR 1 seed=1 trials=20000"));
    }
}