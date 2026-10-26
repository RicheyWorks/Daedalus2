// SPDX-License-Identifier: MIT

package com.daedalus.world.colony;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.IntStream;
import org.junit.jupiter.api.Test;

class PyRandomTest {

    private static List<Integer> range(int n) {
        return IntStream.range(0, n).boxed().toList();
    }

    @Test
    void everyFixtureDrawMatchesCPython() throws Exception {
        var rows = Fixture.rows("RND");
        assertTrue(rows.size() >= 40, "fixture has the CPython draws");
        for (String[] c : rows) {
            long seed = Long.parseLong(c[1]);
            PyRandom r = new PyRandom(seed);
            String got;
            switch (c[2]) {
                case "random" -> got = Double.toString(r.random());
                case "getrandbits" -> {
                    List<String> xs = new ArrayList<>();
                    for (String k : Fixture.list(c[3])) {
                        xs.add(Long.toString(r.getrandbits(Integer.parseInt(k))));
                    }
                    got = String.join(",", xs);
                }
                case "randbelow" -> {
                    List<String> xs = new ArrayList<>();
                    for (String n : Fixture.list(c[3])) {
                        xs.add(Integer.toString(r.randbelow(Integer.parseInt(n))));
                    }
                    got = String.join(",", xs);
                }
                case "sample" -> {
                    String[] nk = c[3].split(",");
                    got = String.join(",", r.sample(range(Integer.parseInt(nk[0])), Integer.parseInt(nk[1]))
                            .stream().map(String::valueOf).toList());
                }
                default -> throw new AssertionError("unknown op " + c[2]);
            }
            assertEquals(c[4], got, "seed " + seed + " " + c[2] + " " + c[3]);
        }
    }

    @Test
    void knownCPythonValue() {
        // python -c "import random; print(random.Random(42).random())"
        assertEquals(0.6394267984578837, new PyRandom(42).random());
        assertEquals(new PyRandom(-42).random(), new PyRandom(42).random(), "CPython seeds by |n|");
    }

    @Test
    void edgeCasesThrowLikePython() {
        PyRandom r = new PyRandom(1);
        assertThrows(IllegalArgumentException.class, () -> r.choice(List.of()));
        assertThrows(IllegalArgumentException.class, () -> r.sample(range(2), 3));
        assertThrows(IllegalArgumentException.class, () -> r.randbelow(0));
        assertEquals(List.of(), r.sample(range(4), 0));
    }
}
