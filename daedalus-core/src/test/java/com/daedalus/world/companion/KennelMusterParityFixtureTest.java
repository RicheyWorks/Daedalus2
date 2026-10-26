// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.Test;

/**
 * Contest gap G128: the Java G107 muster roster ({@link KennelArkMuster#fits}, {@link KennelArkMuster#assign}) written
 * as a parity table that the header-only C++ twin {@code DaedalusKennelMusterCore.h} replays in
 * {@code engines/unreal/core-test/kennel_muster_core_test.cpp}. Crews come from a 64-bit LCG that both sides share.
 * The table is regenerated into target/ every run and must match the committed copy byte for byte.
 */
class KennelMusterParityFixtureTest {
    static final int[] CARES = {0, 3, 10, 21, 60};
    static final int[] BONDS = {0, 25, 50, 80, 100};
    static final int CREWS = 300;
    static final long SEED = 20261019L;

    private long x = SEED;

    private long next() {
        x = x * 6364136223846793005L + 1442695040888963407L;
        return x >>> 33;
    }

    List<String> table() {
        List<String> out = new ArrayList<>();
        out.add("MUSTER 1");
        for (int c : CARES) {
            for (int b : BONDS) {
                for (int p = 0; p < KennelArkMuster.ROLES.size(); p++) {
                    KennelGrowth.Pup h = new KennelGrowth.Pup("h", c, c, b, 0);
                    out.add("fits " + c + " " + b + " " + p + " " + (KennelArkMuster.fits(h, KennelArkMuster.ROLES.get(p)) ? 1 : 0));
                }
            }
        }
        x = SEED;
        for (int k = 0; k < CREWS; k++) {
            int n = (int) (next() % 9);
            List<KennelGrowth.Pup> crew = new ArrayList<>();
            StringBuilder line = new StringBuilder("crew ").append(n);
            for (int i = 0; i < n; i++) {
                int care = (int) (next() % 80);
                int bond = (int) (next() % 101);
                crew.add(new KennelGrowth.Pup("h" + i, care, care, bond, 0));
                line.append(' ').append(care).append(' ').append(bond);
            }
            KennelArkMuster.Roster r = KennelArkMuster.assign(crew);
            line.append(" = ").append(r.posts().size()).append(' ').append(r.totalPct());
            for (String role : KennelArkMuster.ROLES) {
                int idx = r.posts().stream().filter(p -> p.role().equals(role))
                    .mapToInt(p -> Integer.parseInt(p.hound().substring(1))).findFirst().orElse(-1);
                line.append(' ').append(idx);
            }
            out.add(line.toString());
        }
        return out;
    }

    @Test
    void committedMusterParityTableMatchesJava() throws Exception {
        String want = String.join("\n", table()) + "\n";
        Path target = Path.of("target", "kennel_muster_parity.txt");
        Files.createDirectories(target.getParent());
        Files.writeString(target, want, StandardCharsets.UTF_8);
        Path committed = Path.of("..", "engines", "unreal", "core-test", "kennel_muster_parity.txt");
        assertThat(Files.exists(committed)).as("committed kennel_muster_parity.txt").isTrue();
        assertThat(Files.readString(committed, StandardCharsets.UTF_8).replace("\r\n", "\n")).isEqualTo(want);
    }

    @Test
    void tableCoversFullShortAndEmptyCrews() {
        List<String> t = table();
        assertThat(t).hasSize(1 + CARES.length * BONDS.length * 4 + CREWS);
        assertThat(t).anyMatch(s -> s.startsWith("crew ") && s.contains(" = 4 "));
        assertThat(t).anyMatch(s -> s.startsWith("crew ") && s.contains(" = 2 "));
        assertThat(t).anyMatch(s -> s.startsWith("crew 0 = 0 0 -1 -1 -1 -1"));
    }
}
