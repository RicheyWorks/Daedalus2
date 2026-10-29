// SPDX-License-Identifier: MIT
package com.daedalus.server.realm.intake;

import static com.daedalus.server.realm.CreatorRealmScaffold.*;
import static org.assertj.core.api.Assertions.*;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class CreatorIntakeBundleTest {
    private static final String ID = "deathhimself_bundle_asset";
    private static final String ORIGINAL = "deathhimself_bundle_original";
    private static final String VARIANT = "deathhimself_bundle_variant";
    private static final String BYTES = "SYNTHETIC bundle original; no creator art.\n";
    private static final Attribution CREATOR = new Attribution("synthetic-fixture", Basis.SYNTHETIC, null, null);
    @TempDir Path tmp;

    /** Revision 6 contains final source plus its separate draft iteration; revision 7 adds a later brief. */
    private CreatorIntakeStore.Snapshot seed(Path root) throws IOException {
        Path source = Files.writeString(tmp.resolve("synthetic.txt"), BYTES, StandardCharsets.US_ASCII);
        try (var store = CreatorIntakeStore.create(root, Set.of("labyrinth", "LABYRINTH"))) {
            store.addEntry(1, ID, Role.ASSET, CREATOR, null);
            store.attachOriginal(2, ID, ORIGINAL, source, "Synthetic ASCII original for bundle test", true);
            store.editDraft(3, ID, new CreatorIntakeStore.DraftEdit("Synthetic item", "No creator concept", ORIGINAL,
                    CREATOR, SaleIntent.UNSET, List.of()));
            store.finalizeSourceContent(4, ID);
            var prefix = store.reviseEntry(5, VARIANT, ID, CREATOR);
            store.appendIdea(6, VARIANT, "Synthetic later brief excluded from selected prefix");
            return prefix;
        }
    }

    @Test void prefixRoundTripPreservesRawBytesDraftsAndIndependentLineage() throws Exception {
        Path source = tmp.resolve("source-intake"), archive = tmp.resolve("selected.zip"), received = tmp.resolve("received-intake");
        var selected = seed(source);
        var packed = CreatorIntakeBundle.pack(source, 6, archive);
        assertThat(packed.schemaVersion()).isEqualTo(1);
        assertThat(packed.realmId()).isEqualTo("deathhimself");
        assertThat(packed.revision()).isEqualTo(6);
        assertThat(packed.snapshotSha256()).isEqualTo(selected.sha256());
        assertThat(packed.memberCount()).isPositive();
        assertThat(packed.totalBytes()).isPositive();
        assertThat(CreatorIntakeBundle.validate(archive, Set.of())).isEqualTo(packed);
        assertThat(CreatorIntakeBundle.receive(archive, received, Set.of()).bundle()).isEqualTo(packed);
        assertThat(Files.readAllBytes(received.resolve("header.json"))).isEqualTo(Files.readAllBytes(source.resolve("header.json")));
        for (int revision = 1; revision <= 6; revision++) {
            String snapshot = String.format(Locale.ROOT, "snapshots/%08d.json", revision);
            assertThat(Files.readAllBytes(received.resolve(snapshot))).isEqualTo(Files.readAllBytes(source.resolve(snapshot)));
        }
        String digest = selected.manifest().entries().getFirst().originals().getFirst().sha256();
        assertThat(Files.readString(received.resolve("originals").resolve(digest))).isEqualTo(BYTES);
        assertThat(Files.exists(received.resolve("snapshots/00000007.json"))).isFalse();
        try (var restored = CreatorIntakeStore.open(received)) {
            assertThat(restored.current()).isEqualTo(selected);
            assertThat(restored.history()).hasSize(6);
            var entries = restored.current().manifest().entries();
            assertThat(entries.getFirst().stage()).isEqualTo(Stage.FINAL);
            assertThat(entries.get(1).stage()).isEqualTo(Stage.DRAFT);
            assertThat(entries.get(1).supersedesId()).isEqualTo(ID);
            assertThat(entries.get(1).ideas()).isEmpty();
            assertThat(restored.current().manifest().ready()).isFalse();
        }
        try (var zip = new ZipFile(archive.toFile())) {
            assertThat(zip.getEntry("bundle.json")).isNotNull();
            assertThat(zip.getEntry(".writer.lock")).isNull();
            assertThat(zip.getEntry("snapshots/00000007.json")).isNull();
        }
    }

    @Test void tamperedAndTraversalArchivesRefuseWithoutPublishingATarget() throws Exception {
        Path source = tmp.resolve("source-intake"), archive = tmp.resolve("valid.zip");
        seed(source);
        CreatorIntakeBundle.pack(source, 6, archive);
        Path tampered = alteredArchive(archive, "tampered.zip", true, null);
        Path traversal = alteredArchive(archive, "traversal.zip", false, "../outside.txt");
        assertThatThrownBy(() -> CreatorIntakeBundle.validate(tampered, Set.of())).isInstanceOf(IOException.class);
        assertThatThrownBy(() -> CreatorIntakeBundle.receive(tampered, tmp.resolve("bad-digest"), Set.of())).isInstanceOf(IOException.class);
        assertThatThrownBy(() -> CreatorIntakeBundle.receive(traversal, tmp.resolve("bad-path"), Set.of())).isInstanceOf(IOException.class);
        assertThat(Files.exists(tmp.resolve("bad-digest"))).isFalse();
        assertThat(Files.exists(tmp.resolve("bad-path"))).isFalse();
        assertThat(Files.exists(tmp.resolve("outside.txt"))).isFalse();
    }

    @Test void receiveChecksCurrentIdsAndRefusesExistingOrDivergentStateButAllowsExactReceipt() throws Exception {
        Path source = tmp.resolve("source-intake"), archive = tmp.resolve("valid.zip"), received = tmp.resolve("received-intake");
        seed(source);
        CreatorIntakeBundle.pack(source, 6, archive);
        assertThatThrownBy(() -> CreatorIntakeBundle.validate(archive, Set.of(ID))).isInstanceOf(IOException.class);
        assertThatThrownBy(() -> CreatorIntakeBundle.receive(archive, tmp.resolve("collision"), Set.of(ID))).isInstanceOf(IOException.class);
        assertThat(Files.exists(tmp.resolve("collision"))).isFalse();
        Path existing = Files.createDirectory(tmp.resolve("existing"));
        Path marker = Files.writeString(existing.resolve("keep.txt"), "Synthetic existing state", StandardCharsets.US_ASCII);
        assertThatThrownBy(() -> CreatorIntakeBundle.receive(archive, existing, Set.of())).isInstanceOf(IOException.class);
        assertThat(Files.readString(marker)).isEqualTo("Synthetic existing state");
        CreatorIntakeBundle.receive(archive, received, Set.of());
        assertThat(CreatorIntakeBundle.receive(archive, received, Set.of()).status()).isEqualTo("ALREADY_PRESENT_EXACT");
        assertThatThrownBy(() -> CreatorIntakeBundle.receive(archive, received, Set.of(ID))).isInstanceOf(IOException.class);
        try (var store = CreatorIntakeStore.open(received)) {
            store.appendIdea(6, VARIANT, "Synthetic receiver edit must survive a repeated receive");
        }
        assertThatThrownBy(() -> CreatorIntakeBundle.receive(archive, received, Set.of())).isInstanceOf(IOException.class);
        try (var store = CreatorIntakeStore.open(received)) { assertThat(store.current().revision()).isEqualTo(7); }
    }

    /** Re-encode tiny synthetic members with valid ZIP CRCs so digest/path validation must reject them. */
    private Path alteredArchive(Path source, String filename, boolean tamperHeader, String extraPath) throws IOException {
        Path target = tmp.resolve(filename);
        try (var input = new ZipFile(source.toFile()); var output = new ZipOutputStream(Files.newOutputStream(target))) {
            var members = input.entries();
            while (members.hasMoreElements()) {
                ZipEntry member = members.nextElement();
                byte[] bytes;
                try (var stream = input.getInputStream(member)) { bytes = stream.readAllBytes(); }
                if (tamperHeader && member.getName().equals("header.json")) bytes[0] ^= 1;
                output.putNextEntry(new ZipEntry(member.getName()));
                output.write(bytes);
                output.closeEntry();
            }
            if (extraPath != null) {
                output.putNextEntry(new ZipEntry(extraPath));
                output.write("Synthetic unlisted member".getBytes(StandardCharsets.US_ASCII));
                output.closeEntry();
            }
        }
        return target;
    }
}
