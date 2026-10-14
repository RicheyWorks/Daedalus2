// SPDX-License-Identifier: MIT
package com.daedalus.world.land;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.io.DataOutputStream;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Set;
import static org.assertj.core.api.Assertions.*;

class RealmLayoutStoreTest {
    @TempDir Path temp;

    @Test void restartAndMovePreserveIdentityWithDeterministicSnapshots() throws Exception {
        var store = new RealmLayoutStore(temp);
        assertThat(store.load("WORLD-ZERO")).isEmpty();
        var empty = RealmLayout.empty("WORLD-ZERO", Set.of(0, 1));
        store.save(empty, -1);
        var placed = empty.place(52, 52, 2, 42);
        store.save(placed, 0);
        var restarted = new RealmLayoutStore(temp);
        assertThat(restarted.load("WORLD-ZERO")).contains(placed);
        var moved = placed.move(placed.estates().getFirst().landNumber(), 60, 60);
        restarted.save(moved, 1);
        assertThat(new RealmLayoutStore(temp).load("WORLD-ZERO")).contains(moved);
        var other = new RealmLayoutStore(temp.resolve("other"));
        other.save(empty, -1); other.save(placed, 0); other.save(moved, 1);
        assertThat(Files.readAllBytes(temp.resolve("WORLD-ZERO.dlay")))
                .isEqualTo(Files.readAllBytes(temp.resolve("other/WORLD-ZERO.dlay")));
        store.save(RealmLayout.empty("OCEAN", Set.of()), -1);
        assertThat(store.load("WORLD-ZERO")).contains(moved);
        try (var paths = Files.list(temp)) {
            assertThat(paths.filter(p -> p.toString().endsWith(".tmp")).toList()).isEmpty();
        }
    }

    @Test void staleWritersAndBusyLocksCannotReplaceGoodData() throws Exception {
        var store = new RealmLayoutStore(temp);
        var initial = RealmLayout.empty("BRICKS", Set.of());
        store.save(initial, -1);
        var first = initial.place(52, 52, 1, 1);
        store.save(first, 0);
        byte[] before = Files.readAllBytes(temp.resolve("BRICKS.dlay"));
        assertThatIOException().isThrownBy(() -> new RealmLayoutStore(temp).save(initial.place(60, 60, 1, 2), 0));
        assertThatIOException().isThrownBy(() -> store.save(initial, -1));
        assertThatIllegalArgumentException().isThrownBy(() -> store.save(first, -2));
        assertThatIllegalArgumentException().isThrownBy(() -> store.save(first, Long.MAX_VALUE));
        assertThatIllegalArgumentException().isThrownBy(() -> store.save(first, 5));
        try (var channel = FileChannel.open(temp.resolve("BRICKS.lock"), StandardOpenOption.WRITE);
             var lock = channel.lock()) {
            assertThat(lock.isValid()).isTrue();
            assertThatIOException().isThrownBy(() -> store.save(first.move(first.estates().getFirst().landNumber(), 60, 60), 1));
        }
        assertThat(Files.readAllBytes(temp.resolve("BRICKS.dlay"))).isEqualTo(before);
    }

    @Test void corruptFilesFailClosed() throws Exception {
        var store = new RealmLayoutStore(temp);
        Path file = temp.resolve("OCEAN.dlay");
        Files.write(file, new byte[1_000_001]);
        assertThatIOException().isThrownBy(() -> store.load("OCEAN"));
        Files.write(file, new byte[]{1, 2, 3});
        assertThatIOException().isThrownBy(() -> store.load("OCEAN"));
        for (int variant = 0; variant < 10; variant++) {
            try (var out = new DataOutputStream(Files.newOutputStream(file))) {
                out.writeInt(variant == 0 ? 0 : 0x444c4159);
                out.writeInt(variant == 1 ? 99 : 1);
                out.writeUTF(variant == 2 ? "PORTAL" : "OCEAN");
                out.writeLong(variant == 3 ? -1 : 0);
                out.writeInt(variant == 4 ? -1 : variant == 5 ? 10001 : variant == 6 ? 2 : 0);
                if (variant == 6) { out.writeInt(0); out.writeInt(0); }
                out.writeInt(variant == 7 ? 10001 : variant == 8 ? 1 : 0);
                if (variant == 8) { out.writeInt(-1); out.writeInt(50); out.writeInt(50); out.writeInt(1); out.writeLong(0); }
                if (variant == 9) out.writeByte(9);
            }
            assertThatIOException().isThrownBy(() -> store.load("OCEAN"));
        }
        assertThatIllegalArgumentException().isThrownBy(() -> store.load("../OCEAN"));
    }

    @Test void fullGridPersistsWithinBoundAndReadFailureNeverOverwritesIt() throws Exception {
        var rows = new java.util.ArrayList<RealmLayout.Estate>();
        for (int n = 0; n < LandGrid.COUNT; n++) {
            var c = LandGrid.cell(n);
            rows.add(new RealmLayout.Estate(n, c.x(), c.y(), 1, n));
        }
        var all = new RealmLayout("PARCELS", 0, Set.of(), rows);
        var store = new RealmLayoutStore(temp);
        store.save(all, -1);
        assertThat(store.load("PARCELS")).contains(all);
        assertThat(Files.size(temp.resolve("PARCELS.dlay"))).isLessThan(300_000);
        Files.write(temp.resolve("LABYRINTH.dlay"), new byte[]{0});
        assertThatIOException().isThrownBy(() -> store.save(RealmLayout.empty("LABYRINTH", Set.of()), -1));
        assertThat(Files.readAllBytes(temp.resolve("LABYRINTH.dlay"))).containsExactly((byte) 0);
    }
}
