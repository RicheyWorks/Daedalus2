// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ForgeCommissions.Commission;
import com.daedalus.world.forge.ForgeCommissions.Delivery;
import com.daedalus.world.forge.ForgeCommissions.Ledger;
import com.daedalus.world.forge.ForgeGrades.Material;
import com.daedalus.world.forge.ForgeGrades.Weapon;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * C++ = Java, line for line (G98): engines/unreal/core-test/forge_commissions_parity.txt is written by
 * forge_commissions_core_test.cpp --write from DaedalusForgeCommissionsCore.h.
 */
class ForgeCommissionsParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "forge_commissions_parity.txt");
    private static final List<Material> METALS = List.of(Material.COPPER, Material.BRONZE, Material.IRON, Material.STEEL,
            Material.STARMETAL);

    /** The same 100 days of seeded deliveries into one running ledger that the C++ test plays. */
    static List<String> expected() {
        List<String> out = new ArrayList<>();
        Ledger book = new Ledger();
        for (int day = 0; day < 100; day++) {
            SplittableRandom rng = new SplittableRandom(day * 13L + 5);
            for (Commission k : ForgeCommissions.board(day)) {
                Weapon w = rng.nextInt(6) == 0 ? (k.weapon() == Weapon.SWORD ? Weapon.BLASTER : Weapon.SWORD) : k.weapon();
                Material m = k.material();
                if (rng.nextInt(6) == 0) {
                    m = METALS.get((METALS.indexOf(k.material()) + 1) % METALS.size());
                }
                int t = rng.nextInt(101);
                int shifts = rng.nextInt(5);
                Delivery d = book.record(k, ForgeGrades.grade(w, m, t), shifts);
                out.add(k.encode() + " | t=" + t + " shifts=" + shifts + " -> " + d.encode() + " | coins=" + book.coins()
                        + " delivered=" + book.delivered() + " regard=" + book.regard(k.patron()));
            }
        }
        return out;
    }

    @Test
    void javaMatchesTheCppParityFileLineForLine() throws IOException {
        List<String> lines = Files.readAllLines(PARITY);
        assertThat(lines.get(0)).startsWith("# forge_commissions_core_test.cpp --write");
        assertThat(lines.subList(1, lines.size())).containsExactlyElementsOf(expected());
    }
}
