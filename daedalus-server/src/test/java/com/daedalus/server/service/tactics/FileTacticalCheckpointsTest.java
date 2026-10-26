// SPDX-License-Identifier: MIT
package com.daedalus.server.service.tactics;

import com.daedalus.world.tactics.AdaptiveDirector;
import com.daedalus.world.tactics.AdaptiveTacticsBrain;
import com.daedalus.world.tactics.TacticalMemory;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class FileTacticalCheckpointsTest {
    @TempDir Path temp;
    private final AdaptiveTacticsBrain.Key key = new AdaptiveTacticsBrain.Key("session", "squad", "faction");
    private byte[] bytes() { return TacticalMemory.encode(AdaptiveDirector.Memory.initial("faction", "session")); }

    @Test void survivesCloseReopenAndExcludesConcurrentWriter() throws Exception {
        try (var store = new FileTacticalCheckpoints(temp)) {
            assertThat(store.load(key)).isNull();
            store.save(key, bytes());
            assertThatThrownBy(() -> new FileTacticalCheckpoints(temp)).isInstanceOf(IOException.class);
            assertThat(store.load(key)).isEqualTo(bytes());
        }
        try (var reopened = new FileTacticalCheckpoints(temp)) { assertThat(reopened.load(key)).isEqualTo(bytes()); }
        try (var files = Files.list(temp)) { assertThat(files.noneMatch(p -> p.toString().endsWith(".pending"))).isTrue(); }
    }

    @Test void rejectedWritesPreserveLastGoodCheckpointAndValidateKeys() throws Exception {
        try (var store = new FileTacticalCheckpoints(temp)) {
            store.save(key, bytes());
            assertThatThrownBy(() -> store.save(key, new byte[] {1})).isInstanceOf(IllegalArgumentException.class);
            var wrong = TacticalMemory.encode(AdaptiveDirector.Memory.initial("other", "session"));
            assertThatThrownBy(() -> store.save(key, wrong)).isInstanceOf(IllegalArgumentException.class);
            assertThatThrownBy(() -> store.load(new AdaptiveTacticsBrain.Key("../bad", "squad", "faction")))
                    .isInstanceOf(IllegalArgumentException.class);
            assertThat(store.load(key)).isEqualTo(bytes());
        }
    }

    @Test void oversizedAndCorruptDiskFilesFailClosed() throws Exception {
        try (var store = new FileTacticalCheckpoints(temp)) {
            store.save(key, bytes());
            Path file;
            try (var files = Files.list(temp)) { file = files.filter(p -> p.toString().endsWith(".dtm")).findFirst().orElseThrow(); }
            Files.write(file, new byte[TacticalMemory.MAX_BYTES + 1]);
            assertThatThrownBy(() -> store.load(key)).isInstanceOf(IllegalArgumentException.class);
            Files.write(file, new byte[] {1});
            assertThatThrownBy(() -> store.load(key)).isInstanceOf(IllegalArgumentException.class);
        }
    }

    @Test void closedStoreRefusesReadsAndWrites() throws Exception {
        var store = new FileTacticalCheckpoints(temp);
        store.close();
        assertThatThrownBy(() -> store.load(key)).isInstanceOf(UncheckedIOException.class);
        assertThatThrownBy(() -> store.save(key, bytes())).isInstanceOf(UncheckedIOException.class);
    }

    @Test void capacityRefusesNewKeysButAllowsExistingReplacement() throws Exception {
        try (var store = new FileTacticalCheckpoints(temp)) {
            store.save(key, bytes());
            for (int i = 1; i < FileTacticalCheckpoints.MAX_FILES; i++) Files.createFile(temp.resolve(i + ".dtm"));
            assertThatThrownBy(() -> store.save(new AdaptiveTacticsBrain.Key("session", "other", "faction"), bytes()))
                    .isInstanceOf(UncheckedIOException.class);
            store.save(key, bytes());
            assertThat(store.load(key)).isEqualTo(bytes());
        }
    }
}
