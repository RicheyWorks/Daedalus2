// SPDX-License-Identifier: MIT
package com.daedalus.server.realm.intake;

import static com.daedalus.server.realm.CreatorRealmScaffold.*;
import static org.assertj.core.api.Assertions.*;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class CreatorIntakeStoreTest {
    private static final String ID = "deathhimself_synthetic_asset";
    private static final String ORIGINAL = "deathhimself_synthetic_original";
    private static final String BYTES = "SYNTHETIC ART INPUT; no creator artwork.\n";
    private static final Attribution CREATOR = new Attribution("synthetic-fixture", Basis.SYNTHETIC, null, null);
    @TempDir Path tmp;

    private Path source() throws IOException {
        return Files.writeString(tmp.resolve("synthetic.txt"), BYTES, StandardCharsets.US_ASCII);
    }
    private static String hash() throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(BYTES.getBytes(StandardCharsets.US_ASCII)));
    }
    private static CreatorIntakeStore.DraftEdit edit(String name) {
        return new CreatorIntakeStore.DraftEdit(name, "Synthetic metadata; no creator direction", ORIGINAL,
                CREATOR, SaleIntent.REVIEW_REQUESTED, List.of());
    }
    private static Manifest replace(Manifest m, Entry entry) {
        return new Manifest(m.schemaVersion(), m.identity(), m.realmAttribution(), m.enabled(), m.ready(),
                m.creative(), m.connection(), m.marketplace(), List.of(entry));
    }
    private CreatorIntakeStore.Snapshot finalized(CreatorIntakeStore store, Path source) throws IOException {
        var added = store.addEntry(store.current().revision(), ID, Role.ASSET, CREATOR, null);
        var brief = store.appendIdea(added.revision(), ID, "Synthetic brief; team implements supplied art and ideas");
        var attached = store.attachOriginal(brief.revision(), ID, ORIGINAL, source, "Synthetic ASCII test input", true);
        var edited = store.editDraft(attached.revision(), ID, edit("Synthetic item"));
        return store.finalizeSourceContent(edited.revision(), ID);
    }
    private static JsonNode cli(String... args) throws IOException {
        var out = new ByteArrayOutputStream();
        var err = new ByteArrayOutputStream();
        try (var stdout = new PrintStream(out, true, StandardCharsets.UTF_8);
             var stderr = new PrintStream(err, true, StandardCharsets.UTF_8)) {
            assertThat(CreatorIntakeCli.run(args, stdout, stderr)).as(err.toString(StandardCharsets.UTF_8)).isZero();
            assertThat(err.toString(StandardCharsets.UTF_8)).isEmpty();
        }
        return new ObjectMapper().readTree(out.toByteArray());
    }

    @Test void cliAuthorsAndExportsAnOfflineSubmissionWithUsefulNoChangeRefusal() throws Exception {
        Path root = tmp.resolve("cli-intake"), source = source(), output = tmp.resolve("cli-labels.json");
        String directory = root.toString(), idea = "deathhimself_cli_idea";
        Path brief = Files.writeString(tmp.resolve("brief.txt"), "Synthetic creator brief", StandardCharsets.US_ASCII);
        Path provenance = Files.writeString(tmp.resolve("provenance.txt"), "Synthetic ASCII input", StandardCharsets.US_ASCII);
        Path edits = tmp.resolve("edit.json"), unchanged = tmp.resolve("unchanged.json");
        var json = new ObjectMapper();
        json.writerWithDefaultPrettyPrinter().writeValue(edits.toFile(), edit("Synthetic CLI item"));
        assertThat(cli("init", directory).get("revision").asInt()).isEqualTo(1);
        cli("new", directory, "1", idea, "IDEA");
        cli("idea", directory, "2", idea, brief.toString());
        assertThat(cli("show", directory, "2").get("manifest").get("entries").get(0).get("ideas")).isEmpty();
        assertThat(cli("history", directory)).hasSize(3);
        cli("new", directory, "3", ID, "ASSET");
        cli("attach", directory, "4", ID, ORIGINAL, source.toString(), provenance.toString(), "--preview");
        cli("edit", directory, "5", ID, edits.toString());
        assertThat(cli("finalize-source", directory, "6", ID).get("revision").asInt()).isEqualTo(7);
        JsonNode exported = cli("export", directory, "7", output.toString());
        assertThat(exported.get("saleReady").asBoolean()).isFalse();
        assertThat(exported.get("entries").get(1).get("contentId").asText()).isEqualTo(ID);
        assertThat(exported.get("entries").get(1).get("metadata").get("name").asText()).isEqualTo("Synthetic CLI item");
        assertThat(exported.get("entries").get(0).get("saleEligibility").asText()).isEqualTo("INELIGIBLE");
        assertThat(Files.readString(output)).contains(ID, hash()).doesNotContain(BYTES.strip());
        assertThat(Files.readString(root.resolve("originals").resolve(hash()))).isEqualTo(BYTES);
        json.writerWithDefaultPrettyPrinter().writeValue(unchanged.toFile(), cli("show", directory).get("manifest"));
        var out = new ByteArrayOutputStream();
        var err = new ByteArrayOutputStream();
        try (var stdout = new PrintStream(out, true, StandardCharsets.UTF_8);
             var stderr = new PrintStream(err, true, StandardCharsets.UTF_8)) {
            assertThat(CreatorIntakeCli.run(new String[] {"save", directory, "7", unchanged.toString()}, stdout, stderr)).isEqualTo(2);
        }
        assertThat(out.toString(StandardCharsets.UTF_8)).isEmpty();
        assertThat(err.toString(StandardCharsets.UTF_8)).contains("no changes to save");
        assertThat(cli("show", directory).get("revision").asInt()).isEqualTo(7);
    }

    @Test void syntheticIntakeRetainsBytesHistoryAndOfflineMetadataAcrossReopen() throws Exception {
        Path root = tmp.resolve("private-intake"), source = source(), output = tmp.resolve("labels.json");
        String digest = hash();
        CreatorIntakeStore.Snapshot saved;
        try (var store = CreatorIntakeStore.create(root, Set.of("labyrinth", "LABYRINTH"))) {
            assertThat(store.current().revision()).isEqualTo(1);
            assertThat(store.current().manifest()).isEqualTo(empty());
            saved = finalized(store, source);
            assertThat(saved.revision()).isEqualTo(6);
            assertThat(store.history()).hasSize(6);
            assertThat(saved.parentSha256()).isEqualTo(store.read(5).sha256());
            assertThat(saved.manifest().entries().getFirst().stage()).isEqualTo(Stage.FINAL);
            Files.writeString(source, "Changed synthetic submission", StandardCharsets.US_ASCII);
            assertThat(Files.readString(root.resolve("originals").resolve(digest))).isEqualTo(BYTES);
            store.export(saved.revision(), output);
            var json = new ObjectMapper().readTree(output.toFile());
            assertThat(json.get("saleReady").asBoolean()).isFalse();
            assertThat(json.get("entries").get(0).get("contentId").asText()).isEqualTo(ID);
            assertThat(Files.readString(output)).contains(digest).doesNotContain(BYTES.strip());
            assertThatThrownBy(() -> store.export(saved.revision(), output)).isInstanceOf(IOException.class);
            assertThatThrownBy(() -> store.export(saved.revision(), root.resolve("labels.json"))).isInstanceOf(IOException.class);
        }
        try (var reopened = CreatorIntakeStore.open(root)) {
            assertThat(reopened.current()).isEqualTo(saved);
            assertThat(reopened.history()).hasSize(6);
            assertThat(reopened.read(1).manifest().entries()).isEmpty();
        }
    }

    @Test void staleSaveLeavesSnapshotAndOriginalUnchanged() throws Exception {
        Path root = tmp.resolve("private-intake");
        try (var store = CreatorIntakeStore.create(root, Set.of())) {
            store.addEntry(1, ID, Role.ASSET, CREATOR, null);
            var saved = store.attachOriginal(2, ID, ORIGINAL, source(), "Synthetic ASCII test input", true);
            Path snapshot = root.resolve("snapshots/00000003.json"), original = root.resolve("originals").resolve(hash());
            byte[] before = Files.readAllBytes(snapshot);
            assertThatThrownBy(() -> store.save(1, saved.manifest())).isInstanceOf(IOException.class);
            assertThat(store.current()).isEqualTo(saved);
            assertThat(store.history()).hasSize(3);
            assertThat(Files.readAllBytes(snapshot)).isEqualTo(before);
            assertThat(Files.readString(original)).isEqualTo(BYTES);
        }
    }

    @Test void tamperedOriginalRefusesExportAndReopen() throws Exception {
        Path root = tmp.resolve("private-intake");
        try (var store = CreatorIntakeStore.create(root, Set.of())) {
            store.addEntry(1, ID, Role.ASSET, CREATOR, null);
            store.attachOriginal(2, ID, ORIGINAL, source(), "Synthetic ASCII test input", true);
            Files.writeString(root.resolve("originals").resolve(hash()), "TAMPERED SYNTHETIC BYTES", StandardCharsets.US_ASCII);
            assertThatThrownBy(() -> store.export(3, tmp.resolve("tampered-export.json"))).isInstanceOf(IOException.class);
            assertThat(Files.exists(tmp.resolve("tampered-export.json"))).isFalse();
        }
        assertThatThrownBy(() -> CreatorIntakeStore.open(root)).isInstanceOf(IOException.class);
    }

    @Test void secondWriterAndExistingRootCreationAreRefusedWithoutLosingStore() throws Exception {
        Path root = tmp.resolve("private-intake");
        try (var store = CreatorIntakeStore.create(root, Set.of())) {
            assertThatThrownBy(() -> CreatorIntakeStore.open(root)).isInstanceOf(IOException.class);
            assertThatThrownBy(() -> CreatorIntakeStore.create(root, Set.of())).isInstanceOf(IOException.class);
            assertThat(store.current().revision()).isEqualTo(1);
        }
        try (var reopened = CreatorIntakeStore.open(root)) {
            assertThat(reopened.current().manifest()).isEqualTo(empty());
        }
    }

    @Test void finalReplacementIsRejectedWhileNewIdRetainsPredecessor() throws Exception {
        Path root = tmp.resolve("private-intake");
        try (var store = CreatorIntakeStore.create(root, Set.of())) {
            var saved = finalized(store, source());
            Entry before = saved.manifest().entries().getFirst();
            Entry replaced = new Entry(before.id(), before.role(), before.stage(), before.supersedesId(), "Replacement",
                    before.description(), before.previewUri(), before.creator(), before.saleIntent(), before.componentIds(),
                    before.originals(), before.ideas());
            assertThatThrownBy(() -> store.save(saved.revision(), replace(saved.manifest(), replaced))).isInstanceOf(IOException.class);
            assertThat(store.current()).isEqualTo(saved);
            var next = store.addEntry(saved.revision(), "deathhimself_synthetic_variant", Role.ASSET, CREATOR, ID);
            assertThat(next.manifest().entries()).hasSize(2).contains(before);
            assertThat(next.manifest().entries().get(1).supersedesId()).isEqualTo(ID);
            assertThat(store.read(saved.revision())).isEqualTo(saved);
        }
    }
}
