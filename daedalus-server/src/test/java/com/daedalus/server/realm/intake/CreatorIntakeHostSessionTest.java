// SPDX-License-Identifier: MIT
package com.daedalus.server.realm.intake;

import static com.daedalus.server.realm.CreatorRealmScaffold.*;
import static org.assertj.core.api.Assertions.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class CreatorIntakeHostSessionTest {
    private static final String ID = "deathhimself_host_asset";
    private static final String OLD_RESERVED = "deathhimself_source_reserved";
    private static final String BYTES = "SYNTHETIC host-session original; no creator art.\n";
    private static final Attribution CREATOR = new Attribution("synthetic-fixture", Basis.SYNTHETIC, null, null);
    @TempDir Path tmp;

    private static CreatorIntakeHostSession.HostReservations host(String snapshot, Set<String> ids) {
        return new CreatorIntakeHostSession.HostReservations("synthetic-host", snapshot, ids);
    }
    private static Manifest appended(Manifest before, String id) {
        var entries = new ArrayList<>(before.entries());
        entries.add(new Entry(id, Role.IDEA, Stage.DRAFT, null, null, null, null, CREATOR,
                SaleIntent.UNSET, List.of(), List.of(), List.of()));
        return new Manifest(before.schemaVersion(), before.identity(), before.realmAttribution(), before.enabled(), before.ready(),
                before.creative(), before.connection(), before.marketplace(), entries);
    }

    @Test void restoredOldHeaderContinuesUnderImmutableExplicitHostWithoutRewritingPrefix() throws Exception {
        Path source = tmp.resolve("source"), restored = tmp.resolve("restored"), archive = tmp.resolve("transfer.zip");
        Path art = Files.writeString(tmp.resolve("synthetic.txt"), BYTES, StandardCharsets.US_ASCII);
        try (var store = CreatorIntakeStore.create(source, Set.of(OLD_RESERVED))) {
            store.addEntry(1, "deathhimself_source_idea", Role.IDEA, CREATOR, null);
        }
        CreatorIntakeBundle.pack(source, 2, archive);
        CreatorIntakeBundle.receive(archive, restored, Set.of("deathhimself_target_reserved"));
        byte[] header = Files.readAllBytes(restored.resolve("header.json"));
        byte[] prefix = Files.readAllBytes(restored.resolve("snapshots/00000002.json"));
        var mutableIds = new HashSet<>(Set.of("deathhimself_target_reserved"));
        var context = host("snapshot-a", mutableIds);
        mutableIds.add(ID);
        try (var session = CreatorIntakeHostSession.open(restored, context)) {
            assertThat(session.binding().hostId()).isEqualTo("synthetic-host");
            assertThat(session.binding().snapshotId()).isEqualTo("snapshot-a");
            assertThat(session.binding().sha256()).matches("[0-9a-f]{64}");
            session.requireHost(context);
            session.addEntry(2, ID, Role.ASSET, CREATOR, null);
            var saved = session.attachOriginal(3, ID, "deathhimself_host_original", art, "Synthetic ASCII input", true);
            assertThat(saved.revision()).isEqualTo(4);
            assertThat(session.history()).hasSize(4);
            assertThat(session.read(2).manifest().entries()).hasSize(1);
            assertThat(session.review(4).saleReady()).isFalse();
            String digest = saved.manifest().entries().get(1).originals().getFirst().sha256();
            assertThat(Files.readString(restored.resolve("originals").resolve(digest))).isEqualTo(BYTES);
        }
        assertThat(Files.readAllBytes(restored.resolve("header.json"))).isEqualTo(header);
        assertThat(Files.readAllBytes(restored.resolve("snapshots/00000002.json"))).isEqualTo(prefix);
    }

    @Test void currentHostAndSourceReservationsRefuseCollisionsBeforeMutationOrOriginalCopy() throws Exception {
        Path root = tmp.resolve("store");
        try (var store = CreatorIntakeStore.create(root, Set.of(OLD_RESERVED))) { store.addEntry(1, ID, Role.ASSET, CREATOR, null); }
        assertThatThrownBy(() -> CreatorIntakeHostSession.open(root, host("conflict", Set.of(ID)))).isInstanceOf(IOException.class);
        Set<String> ids = Set.of("deathhimself_target_new", "deathhimself_target_original", "deathhimself_target_saved");
        byte[] before = Files.readAllBytes(root.resolve("snapshots/00000002.json"));
        try (var session = CreatorIntakeHostSession.open(root, host("snapshot-b", ids))) {
            var current = session.current();
            assertThatThrownBy(() -> session.addEntry(2, "deathhimself_target_new", Role.IDEA, CREATOR, null))
                    .isInstanceOf(IOException.class);
            assertThatThrownBy(() -> session.attachOriginal(2, ID, "deathhimself_target_original", tmp.resolve("missing.txt"),
                    "Synthetic provenance", true)).isInstanceOf(IOException.class).hasMessageContaining("collision");
            assertThatThrownBy(() -> session.save(2, appended(current.manifest(), "deathhimself_target_saved")))
                    .isInstanceOf(IOException.class);
            assertThatThrownBy(() -> session.addEntry(2, OLD_RESERVED, Role.IDEA, CREATOR, null)).isInstanceOf(IOException.class);
            assertThat(session.current()).isEqualTo(current);
            assertThat(session.history()).hasSize(2);
            try (var originals = Files.list(root.resolve("originals"))) { assertThat(originals.toList()).isEmpty(); }
        }
        assertThat(Files.readAllBytes(root.resolve("snapshots/00000002.json"))).isEqualTo(before);
    }

    @Test void sessionRefusesOtherWritersStaleRevisionsChangedContextAndExternalSnapshotReplacement() throws Exception {
        Path root = tmp.resolve("store");
        try (var ignored = CreatorIntakeStore.create(root, Set.of())) { }
        var context = host("snapshot-c", Set.of());
        var session = CreatorIntakeHostSession.open(root, context);
        try (session) {
            assertThatThrownBy(() -> CreatorIntakeHostSession.open(root, context)).isInstanceOf(IOException.class);
            session.addEntry(1, ID, Role.IDEA, CREATOR, null);
            assertThatThrownBy(() -> session.appendIdea(1, ID, "Synthetic stale brief")).isInstanceOf(IOException.class);
            assertThatThrownBy(() -> session.requireHost(host("snapshot-d", Set.of()))).isInstanceOf(IOException.class);
            assertThat(session.current().revision()).isEqualTo(2);
            Path snapshot = root.resolve("snapshots/00000002.json");
            var json = new ObjectMapper();
            var externallyChanged = json.readTree(snapshot.toFile());
            ((ObjectNode) externallyChanged.at("/manifest/entries/0")).put("name", "Synthetic external draft edit");
            json.writerWithDefaultPrettyPrinter().writeValue(snapshot.toFile(), externallyChanged);
            byte[] changed = Files.readAllBytes(snapshot);
            assertThatThrownBy(() -> session.appendIdea(2, ID, "Must not overwrite external change")).isInstanceOf(IOException.class);
            assertThat(Files.readAllBytes(snapshot)).isEqualTo(changed);
        }
        assertThatThrownBy(session::current).isInstanceOf(IOException.class);
        try (var reopened = CreatorIntakeHostSession.open(root, context)) { assertThat(reopened.current().revision()).isEqualTo(2); }
    }
}
