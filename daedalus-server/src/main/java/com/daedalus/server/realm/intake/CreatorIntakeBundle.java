// SPDX-License-Identifier: MIT
package com.daedalus.server.realm.intake;

import com.daedalus.server.realm.CreatorRealmScaffold;
import com.daedalus.server.realm.CreatorRealmScaffold.Manifest;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeSet;
import java.util.zip.CRC32;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

/**
 * Explicit local private-art transfer, not the JSON-only metadata export or a network/publication service.
 * A v1 ZIP contains bundle.json, the byte-exact store header, a selected history prefix and referenced originals.
 * File names, digests, CRCs and expanded bytes are bounded and verified before restoring into a new directory.
 * Failed staging directories are retained and named in the error; successful staging is removed.
 * Existing destinations are never replaced. Only an identical receipt with unchanged complete state is idempotent.
 * The caller must supply current host IDs; source-header reservations alone never establish compatibility.
 * Compatibility is checked at transfer time; the byte-exact restored header does not reserve future host IDs.
 * Hashes verify byte integrity, not creator identity, legal ownership or permission to distribute private originals.
 */
public final class CreatorIntakeBundle {
    public static final int MAX_MEMBERS = 10_000;
    public static final long MAX_TOTAL_BYTES = 1024L * 1024 * 1024;
    public static final long MAX_ARCHIVE_BYTES = MAX_TOTAL_BYTES;
    private static final String INDEX = "bundle.json";
    private static final String STAMP = ".bundle-receipt.json";
    private static final String HASH = "[0-9a-f]{64}";
    private static final ObjectMapper JSON = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT)
            .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION).enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);

    public record Member(String path, String sha256, long size) { }
    private record Index(int schemaVersion, String realmId, int revision, String snapshotSha256, List<Member> members) {
        private Index { members = List.copyOf(members); }
    }
    private record Stored(int schemaVersion, int revision, String parentSha256, Manifest manifest) { }
    private record Stamp(int schemaVersion, String bundleSha256, String snapshotSha256, int revision) { }
    private record Staged(Path work, Path store, Index index, Inspection inspection) { }
    private static final class BoundedOutput extends OutputStream {
        private final OutputStream output;
        private long count;
        private BoundedOutput(OutputStream output) { this.output = output; }
        @Override public void write(int value) throws IOException {
            reserve(1);
            output.write(value);
        }
        @Override public void write(byte[] bytes, int offset, int length) throws IOException {
            reserve(length);
            output.write(bytes, offset, length);
        }
        private void reserve(int length) throws IOException {
            if (length < 0 || count > MAX_ARCHIVE_BYTES - length) throw new IOException("Archive exceeds byte budget");
            count += length;
        }
        @Override public void flush() throws IOException { output.flush(); }
        @Override public void close() throws IOException { output.close(); }
    }
    public record Inspection(int schemaVersion, String realmId, int revision, String snapshotSha256,
                             String bundleSha256, int memberCount, long totalBytes) { }
    public record Receipt(Inspection bundle, String status) { }

    private CreatorIntakeBundle() { }

    /** Archive only an explicitly selected validated prefix; no source path, lock, pending file or orphan blob is included. */
    public static Inspection pack(Path location, int revision, Path newArchive) throws IOException {
        Path root = directory(location);
        Path target = newTarget(newArchive);
        if (target.startsWith(root)) throw new IOException("Private bundle must be outside the intake store");
        if (Files.exists(target, LinkOption.NOFOLLOW_LINKS)) throw new IOException("Archive destination already exists");
        Path temporary = null;
        try (CreatorIntakeStore store = CreatorIntakeStore.open(root)) {
            var selected = store.read(revision);
            List<Member> members = new ArrayList<>();
            byte[] header = bytes(root.resolve("header.json"));
            members.add(new Member("header.json", hash(header), header.length));
            List<CreatorIntakeStore.Revision> history = store.history();
            if (revision > MAX_MEMBERS - 1) throw new IOException("Bundle member limit exceeded");
            for (int number = 1; number <= revision; number++) {
                String name = snapshotName(number);
                byte[] raw = bytes(root.resolve(name));
                String sha = hash(raw);
                if (!sha.equals(history.get(number - 1).sha256())) throw new IOException("Snapshot changed while packing");
                members.add(new Member(name, sha, raw.length));
            }
            for (String sha : originalHashes(selected.manifest())) {
                long size = regular(root.resolve("originals").resolve(sha)).size();
                members.add(new Member("originals/" + sha, sha, size));
            }
            Index index = new Index(1, CreatorRealmScaffold.REALM_ID, revision, selected.sha256(), members);
            long total = validateIndex(index);
            byte[] indexBytes = JSON.writeValueAsBytes(index);
            if (indexBytes.length > CreatorIntakeStore.MAX_METADATA_BYTES) throw new IOException("Bundle index exceeds size limit");
            temporary = Files.createTempFile(parent(target), ".creator-bundle-", ".pending");
            try (ZipOutputStream zip = new ZipOutputStream(new BoundedOutput(
                    Files.newOutputStream(temporary, StandardOpenOption.WRITE)))) {
                put(zip, INDEX, indexBytes);
                for (Member member : members) {
                    ZipEntry entry = new ZipEntry(member.path());
                    entry.setTime(0L);
                    zip.putNextEntry(entry);
                    copyFile(root.resolve(member.path()), zip, member.size(), member.sha256());
                    zip.closeEntry();
                }
            }
            force(temporary);
            String sha = fileHash(temporary, MAX_ARCHIVE_BYTES);
            Files.createLink(target, temporary);
            Files.delete(temporary);
            temporary = null;
            return new Inspection(1, index.realmId(), revision, index.snapshotSha256(), sha, members.size(), total);
        } catch (IOException | RuntimeException e) {
            throw failure("Cannot pack private intake", temporary, e);
        }
    }

    /** Full validation includes opening the staged store with the existing chain/original validator; successful scratch is removed. */
    public static Inspection validate(Path archive, Set<String> currentReservedIds) throws IOException {
        Set<String> ids = currentIds(currentReservedIds);
        Path scratchParent = directory(Path.of(System.getProperty("java.io.tmpdir")));
        Staged staged = stage(archive, scratchParent, ids);
        Inspection inspection = staged.inspection();
        removeOwnedStage(staged.work());
        return inspection;
    }

    /** New-only local restore. Repeating the same archive succeeds only while every restored byte and the history remain identical. */
    public static Receipt receive(Path archive, Path newPrivateRoot, Set<String> currentReservedIds) throws IOException {
        Set<String> ids = currentIds(currentReservedIds);
        Path target = newTarget(newPrivateRoot);
        boolean existing = Files.exists(target, LinkOption.NOFOLLOW_LINKS);
        if (existing && !Files.isRegularFile(target.resolve(STAMP), LinkOption.NOFOLLOW_LINKS)) {
            throw new IOException("Existing destination is not an identical completed bundle receipt");
        }
        Staged staged = stage(archive, parent(target), ids);
        try {
            if (existing) {
                Stamp stamp = JSON.readValue(bytes(target.resolve(STAMP)), Stamp.class);
                if (!stamp.equals(stamp(staged.inspection()))) throw new IOException("Existing destination has a different bundle receipt");
                verifyStore(target, staged.index(), ids, true);
                removeOwnedStage(staged.work());
                return new Receipt(staged.inspection(), "ALREADY_PRESENT_EXACT");
            }
            Files.createDirectory(target);
            Files.createDirectory(target.resolve("originals"));
            Files.createDirectory(target.resolve("snapshots"));
            for (Member member : staged.index().members()) {
                if (!member.path().equals("header.json")) {
                    Files.createLink(target.resolve(member.path()), staged.store().resolve(member.path()));
                }
            }
            // Publish the byte-exact header only after all content exists. The completed receipt is the final commit marker.
            Files.createLink(target.resolve("header.json"), staged.store().resolve("header.json"));
            verifyStore(target, staged.index(), ids, false);
            publish(target.resolve(STAMP), JSON.writeValueAsBytes(stamp(staged.inspection())));
            removeOwnedStage(staged.work());
            return new Receipt(staged.inspection(), "CREATED");
        } catch (IOException | RuntimeException e) {
            throw failure("Receive failed; destination may contain incomplete owned state at " + target, staged.work(), e);
        }
    }

    private static Staged stage(Path archive, Path parent, Set<String> ids) throws IOException {
        Path work = Files.createTempDirectory(parent, ".creator-intake-bundle-");
        try {
            Path copy = work.resolve("archive.zip");
            BasicFileAttributes source = regular(archive);
            if (source.size() > MAX_ARCHIVE_BYTES) throw new IOException("Archive exceeds size limit");
            String archiveSha;
            try (OutputStream output = Files.newOutputStream(copy, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
                archiveSha = copyFile(archive, output, source.size(), null);
            }
            Path store = Files.createDirectory(work.resolve("store"));
            Files.createDirectory(store.resolve("originals"));
            Files.createDirectory(store.resolve("snapshots"));
            Index index;
            long total;
            try (ZipFile zip = new ZipFile(copy.toFile())) {
                Map<String, ZipEntry> entries = zipEntries(zip);
                ZipEntry descriptor = entries.get(INDEX);
                if (descriptor == null) throw new IOException("Missing bundle index");
                byte[] raw = zipBytes(zip, descriptor, CreatorIntakeStore.MAX_METADATA_BYTES);
                index = JSON.readValue(raw, Index.class);
                total = validateIndex(index);
                Set<String> expected = new HashSet<>();
                expected.add(INDEX);
                for (Member member : index.members()) expected.add(member.path());
                if (!entries.keySet().equals(expected)) throw new IOException("ZIP members differ from the exact bundle allowlist");
                long written = 0;
                for (Member member : index.members()) {
                    ZipEntry entry = entries.get(member.path());
                    if (entry.getSize() != member.size()) throw new IOException("ZIP member size mismatch");
                    Path output = store.resolve(member.path());
                    try (FileChannel channel = FileChannel.open(output, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
                        written += copyZip(zip, entry, channel, member.size(), member.sha256());
                        if (written > MAX_TOTAL_BYTES) throw new IOException("Expanded bundle exceeds byte budget");
                        channel.force(true);
                    }
                }
                if (written != total) throw new IOException("Expanded bundle size mismatch");
            }
            verifyStore(store, index, ids, false);
            return new Staged(work, store, index, new Inspection(1, index.realmId(), index.revision(),
                    index.snapshotSha256(), archiveSha, index.members().size(), total));
        } catch (IOException | RuntimeException e) {
            throw failure("Invalid private intake bundle", work, e);
        }
    }

    private static Map<String, ZipEntry> zipEntries(ZipFile zip) throws IOException {
        Map<String, ZipEntry> entries = new HashMap<>();
        var iterator = zip.entries();
        while (iterator.hasMoreElements()) {
            ZipEntry entry = iterator.nextElement();
            String name = entry.getName();
            if (entries.size() >= MAX_MEMBERS + 1 || entry.isDirectory() || !allowed(name)
                    || entries.putIfAbsent(name, entry) != null) throw new IOException("Unknown, duplicate or excessive ZIP member");
            if (entry.getSize() < 0 || entry.getCompressedSize() < 0 || entry.getCrc() < 0
                    || entry.getCompressedSize() > MAX_ARCHIVE_BYTES
                    || entry.getMethod() != ZipEntry.STORED && entry.getMethod() != ZipEntry.DEFLATED) {
                throw new IOException("Unsupported ZIP member representation");
            }
        }
        return entries;
    }

    private static long validateIndex(Index index) throws IOException {
        if (index.schemaVersion() != 1 || !CreatorRealmScaffold.REALM_ID.equals(index.realmId())
                || index.revision() < 1 || index.revision() > MAX_MEMBERS - 1
                || index.snapshotSha256() == null || !index.snapshotSha256().matches(HASH)
                || index.members().size() > MAX_MEMBERS) throw new IOException("Unsupported bundle index");
        Set<String> names = new HashSet<>();
        long total = 0;
        for (Member member : index.members()) {
            if (member == null || !allowed(member.path()) || INDEX.equals(member.path()) || !names.add(member.path())
                    || member.sha256() == null || !member.sha256().matches(HASH) || member.size() < 0
                    || member.size() > (member.path().startsWith("originals/") ? CreatorIntakeStore.MAX_ORIGINAL_BYTES
                    : CreatorIntakeStore.MAX_METADATA_BYTES)) throw new IOException("Invalid bundle member descriptor");
            if (member.path().startsWith("originals/") && !member.path().equals("originals/" + member.sha256())) {
                throw new IOException("Original member name must pin its digest");
            }
            total += member.size();
            if (total > MAX_TOTAL_BYTES) throw new IOException("Bundle exceeds expanded byte budget");
        }
        if (!names.contains("header.json")) throw new IOException("Missing store header");
        for (int revision = 1; revision <= index.revision(); revision++) {
            if (!names.contains(snapshotName(revision))) throw new IOException("Missing history prefix member");
        }
        for (String name : names) {
            if (name.startsWith("snapshots/") && Integer.parseInt(name.substring(10, 18)) > index.revision()) {
                throw new IOException("Unexpected history after selected revision");
            }
        }
        return total;
    }

    private static void verifyStore(Path root, Index index, Set<String> ids, boolean receiptExpected) throws IOException {
        directory(root);
        Set<String> actual = new HashSet<>();
        try (var children = Files.list(root)) {
            for (Path child : children.toList()) {
                String name = fileName(child);
                if (name.equals("originals") || name.equals("snapshots")) {
                    directory(child);
                    try (var files = Files.list(child)) {
                        for (Path file : files.toList()) {
                            regular(file);
                            actual.add(name + "/" + fileName(file));
                        }
                    }
                } else if (name.equals(".writer.lock")) {
                    regular(child);
                } else if (name.equals(STAMP) && receiptExpected) {
                    regular(child);
                } else {
                    regular(child);
                    actual.add(name);
                }
            }
        }
        Set<String> expected = new HashSet<>();
        for (Member member : index.members()) expected.add(member.path());
        if (!actual.equals(expected)) throw new IOException("Store files differ from the exact restored bundle state");
        try (CreatorIntakeStore store = CreatorIntakeStore.open(root)) {
            var snapshot = store.current();
            if (snapshot.revision() != index.revision() || !snapshot.sha256().equals(index.snapshotSha256())) {
                throw new IOException("Selected intake revision/digest mismatch");
            }
            Set<String> originals = originalHashes(snapshot.manifest());
            for (Member member : index.members()) {
                Path file = root.resolve(member.path());
                if (regular(file).size() != member.size() || !fileHash(file, member.size()).equals(member.sha256())) {
                    throw new IOException("Restored member digest mismatch: " + member.path());
                }
                if (member.path().startsWith("snapshots/")) {
                    Stored stored = JSON.readValue(bytes(file), Stored.class);
                    List<String> errors = CreatorRealmScaffold.validate(stored.manifest(), ids);
                    if (!errors.isEmpty()) throw new IOException("Current host ID compatibility: " + String.join("; ", errors));
                } else if (member.path().startsWith("originals/") && !originals.remove(member.sha256())) {
                    throw new IOException("Unreferenced original in bundle");
                }
            }
            if (!originals.isEmpty()) throw new IOException("Missing referenced originals");
        }
    }

    private static Set<String> currentIds(Set<String> ids) throws IOException {
        if (ids == null || ids.size() > MAX_MEMBERS || ids.stream().anyMatch(id -> id == null || id.isBlank() || id.length() > 256)) {
            throw new IOException("Explicit current reserved IDs are required (empty set permitted)");
        }
        List<String> errors = CreatorRealmScaffold.validate(CreatorRealmScaffold.empty(), ids);
        if (!errors.isEmpty()) throw new IOException("Current host ID compatibility: " + String.join("; ", errors));
        return Set.copyOf(ids);
    }

    private static Set<String> originalHashes(Manifest manifest) {
        Set<String> hashes = new TreeSet<>();
        for (var entry : manifest.entries()) for (var original : entry.originals()) hashes.add(original.sha256());
        return hashes;
    }

    private static long copyZip(ZipFile zip, ZipEntry entry, FileChannel output, long limit, String expectedHash) throws IOException {
        MessageDigest digest = digest();
        CRC32 crc = new CRC32();
        long count = 0;
        try (InputStream input = zip.getInputStream(entry)) {
            byte[] buffer = new byte[64 * 1024];
            for (int length; (length = input.read(buffer)) != -1;) {
                count += length;
                if (count > limit) throw new IOException("ZIP member exceeds declared byte budget");
                crc.update(buffer, 0, length);
                digest.update(buffer, 0, length);
                ByteBuffer bytes = ByteBuffer.wrap(buffer, 0, length);
                while (bytes.hasRemaining()) output.write(bytes);
            }
        }
        if (count != limit || crc.getValue() != entry.getCrc() || !HexFormat.of().formatHex(digest.digest()).equals(expectedHash)) {
            throw new IOException("ZIP member size, CRC or SHA-256 mismatch");
        }
        return count;
    }

    private static byte[] zipBytes(ZipFile zip, ZipEntry entry, int limit) throws IOException {
        if (entry.getSize() > limit) throw new IOException("Bundle index exceeds size limit");
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        CRC32 crc = new CRC32();
        try (InputStream input = zip.getInputStream(entry)) {
            byte[] buffer = new byte[8192];
            for (int length; (length = input.read(buffer)) != -1;) {
                if (output.size() + length > limit) throw new IOException("Bundle index exceeds byte budget");
                crc.update(buffer, 0, length);
                output.write(buffer, 0, length);
            }
        }
        if (output.size() != entry.getSize() || crc.getValue() != entry.getCrc()) throw new IOException("Bundle index size/CRC mismatch");
        return output.toByteArray();
    }

    private static String copyFile(Path source, OutputStream output, long expectedSize, String expectedHash) throws IOException {
        BasicFileAttributes before = regular(source);
        if (before.size() != expectedSize || expectedSize > MAX_ARCHIVE_BYTES) throw new IOException("Source file size mismatch");
        MessageDigest digest = digest();
        long count = 0;
        try (InputStream input = Files.newInputStream(source, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) {
            byte[] buffer = new byte[64 * 1024];
            for (int length; (length = input.read(buffer)) != -1;) {
                count += length;
                if (count > expectedSize) throw new IOException("Source grew while copying");
                digest.update(buffer, 0, length);
                output.write(buffer, 0, length);
            }
        }
        BasicFileAttributes after = regular(source);
        String hash = HexFormat.of().formatHex(digest.digest());
        if (count != expectedSize || before.size() != after.size() || !before.lastModifiedTime().equals(after.lastModifiedTime())
                || !Objects.equals(before.fileKey(), after.fileKey()) || expectedHash != null && !hash.equals(expectedHash)) {
            throw new IOException("Source changed or digest mismatched while copying");
        }
        return hash;
    }

    private static String fileHash(Path file, long limit) throws IOException {
        long size = regular(file).size();
        if (size > limit) throw new IOException("File exceeds size limit");
        return copyFile(file, OutputStream.nullOutputStream(), size, null);
    }
    private static byte[] bytes(Path file) throws IOException {
        if (regular(file).size() > CreatorIntakeStore.MAX_METADATA_BYTES) throw new IOException("Metadata exceeds size limit");
        try (InputStream input = Files.newInputStream(file, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) {
            byte[] bytes = input.readNBytes(CreatorIntakeStore.MAX_METADATA_BYTES + 1);
            if (bytes.length > CreatorIntakeStore.MAX_METADATA_BYTES) throw new IOException("Metadata exceeds size limit");
            return bytes;
        }
    }
    private static void publish(Path target, byte[] bytes) throws IOException {
        Path temporary = Files.createTempFile(parent(target), ".bundle-receipt-", ".pending");
        try (FileChannel output = FileChannel.open(temporary, StandardOpenOption.WRITE)) {
            ByteBuffer buffer = ByteBuffer.wrap(bytes);
            while (buffer.hasRemaining()) output.write(buffer);
            output.force(true);
        }
        Files.createLink(target, temporary);
        Files.delete(temporary);
    }
    private static void force(Path file) throws IOException {
        try (FileChannel channel = FileChannel.open(file, StandardOpenOption.WRITE)) { channel.force(true); }
    }
    private static void put(ZipOutputStream zip, String name, byte[] bytes) throws IOException {
        ZipEntry entry = new ZipEntry(name);
        entry.setTime(0L);
        zip.putNextEntry(entry);
        zip.write(bytes);
        zip.closeEntry();
    }
    private static boolean allowed(String name) {
        return name != null && (name.equals(INDEX) || name.equals("header.json")
                || name.matches("snapshots/[0-9]{8}\\.json") || name.matches("originals/" + HASH));
    }
    private static String snapshotName(int revision) { return String.format(java.util.Locale.ROOT, "snapshots/%08d.json", revision); }
    private static Path newTarget(Path target) throws IOException {
        Path requested = target.toAbsolutePath().normalize();
        Path requestedParent = requested.getParent();
        Path name = requested.getFileName();
        if (requestedParent == null || name == null) throw new IOException("A new named destination and existing parent are required");
        return directory(requestedParent).resolve(name);
    }
    private static Path directory(Path path) throws IOException {
        if (!Files.isDirectory(path, LinkOption.NOFOLLOW_LINKS)) throw new IOException("Expected a local directory");
        return path.toRealPath();
    }
    private static BasicFileAttributes regular(Path file) throws IOException {
        BasicFileAttributes attributes = Files.readAttributes(file, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        if (!attributes.isRegularFile()) throw new IOException("Expected a regular local file");
        return attributes;
    }
    private static Path parent(Path path) throws IOException {
        Path parent = path.getParent();
        if (parent == null) throw new IOException("Missing destination parent");
        return parent;
    }
    private static String fileName(Path path) throws IOException {
        Path name = path.getFileName();
        if (name == null) throw new IOException("Missing file name");
        return name.toString();
    }
    private static MessageDigest digest() {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch (NoSuchAlgorithmException e) { throw new IllegalStateException("SHA-256 unavailable", e); }
    }
    private static String hash(byte[] bytes) { return HexFormat.of().formatHex(digest().digest(bytes)); }
    private static Stamp stamp(Inspection inspection) {
        return new Stamp(1, inspection.bundleSha256(), inspection.snapshotSha256(), inspection.revision());
    }
    private static IOException failure(String message, Path retained, Exception cause) {
        return new IOException(message + (retained == null ? "" : "; failure evidence retained at " + retained)
                + ": " + cause.getClass().getSimpleName() + ": " + cause.getMessage(), cause);
    }
    private static void removeOwnedStage(Path work) throws IOException {
        // Only an internally allocated fresh staging root is eligible; never traverse a caller's destination or a symlink.
        if (!fileName(work).startsWith(".creator-intake-bundle-")) throw new IOException("Not an owned bundle staging directory");
        try (var paths = Files.walk(work)) {
            for (Path path : paths.sorted(java.util.Comparator.reverseOrder()).toList()) Files.delete(path);
        }
    }
}
