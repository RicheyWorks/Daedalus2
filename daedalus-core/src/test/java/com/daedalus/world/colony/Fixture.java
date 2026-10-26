// SPDX-License-Identifier: MIT

package com.daedalus.world.colony;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Reads daybook-parity.tsv, written by tools/economy/daybook_parity.py from the Python cores. */
final class Fixture {
    private Fixture() {
    }

    static List<String[]> rows(String kind) throws IOException {
        List<String[]> out = new ArrayList<>();
        try (var in = Fixture.class.getResourceAsStream("daybook-parity.tsv")) {
            if (in == null) {
                throw new IOException("daybook-parity.tsv missing: run python tools/economy/daybook_parity.py");
            }
            var r = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
            for (String line = r.readLine(); line != null; line = r.readLine()) {
                if (line.startsWith("#") || line.isBlank()) {
                    continue;
                }
                String[] c = line.split("\t", -1);
                if (kind == null || c[0].equals(kind)) {
                    out.add(c);
                }
            }
        }
        return out;
    }

    static List<String> list(String s) {
        return s.equals("-") ? List.of() : Arrays.asList(s.split(",", -1));
    }
}
