package com.daedalus.world.forge;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.forge.ForgeGrades.Material;
import com.daedalus.world.forge.ForgeGrades.Weapon;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/** C++ = Java, line for line: engines/unreal/core-test/forge_grades_parity.txt is written by the C++ test. */
class ForgeGradesParityTest {
    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "forge_grades_parity.txt");

    @Test
    void javaMatchesCppForEveryWeaponMaterialAndTemper() throws IOException {
        List<String> expected = new ArrayList<>();
        for (String line : Files.readAllLines(PARITY)) {
            if (!line.startsWith("#") && !line.isBlank()) expected.add(line);
        }
        List<String> actual = new ArrayList<>();
        for (Weapon w : Weapon.values()) {
            for (Material m : Material.values()) {
                for (int t = 0; t <= 100; t++) actual.add(ForgeGrades.grade(w, m, t).encode());
            }
        }
        assertEquals(2 * 8 * 101, expected.size());
        assertTrue(expected.size() == actual.size());
        for (int i = 0; i < actual.size(); i++) assertEquals(expected.get(i), actual.get(i), "line " + i);
    }
}
