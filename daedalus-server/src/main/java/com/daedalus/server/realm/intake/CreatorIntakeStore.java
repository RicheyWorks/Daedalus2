// SPDX-License-Identifier: MIT
package com.daedalus.server.realm.intake;

import com.daedalus.api.dto.IslandTokenMetadata;
import com.daedalus.api.dto.TokenAttribute;
import com.daedalus.server.realm.CreatorRealmScaffold;
import com.daedalus.server.realm.CreatorRealmScaffold.Attribution;
import com.daedalus.server.realm.CreatorRealmScaffold.Entry;
import com.daedalus.server.realm.CreatorRealmScaffold.Manifest;
import com.daedalus.server.realm.CreatorRealmScaffold.Original;
import com.daedalus.server.realm.CreatorRealmScaffold.Role;
import com.daedalus.server.realm.CreatorRealmScaffold.SaleIntent;
import com.daedalus.server.realm.CreatorRealmScaffold.Stage;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
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
import java.util.function.UnaryOperator;

/** Private local authoring store. It has no server bean, endpoint, network client or publication capability. */
public final class CreatorIntakeStore implements AutoCloseable {
    public static final int MAX_METADATA_BYTES = 8 * 1024 * 1024;
    public static final long MAX_ORIGINAL_BYTES = 256L * 1024 * 1024;
    private static final int MAX_REVISIONS = 100_000;
    private static final ObjectMapper JSON = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT)
            .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION).enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);

    public record Snapshot(int revision, String sha256, String parentSha256, Manifest manifest) { }
    public record Revision(int revision, String sha256, String parentSha256, int entryCount) { }
    public record DraftEdit(String name, String description, String previewOriginalId, Attribution creator,
                            SaleIntent saleIntent, List<String> componentIds) {
        public DraftEdit { componentIds = componentIds == null ? List.of() : List.copyOf(componentIds); }
    }
    public record ExportEntry(String contentId, Role role, Stage stage, String saleEligibility,
                              List<TokenAttribute> labels, IslandTokenMetadata metadata, List<String> missingInputs) {
        public ExportEntry { labels = List.copyOf(labels); missingInputs = List.copyOf(missingInputs); }
    }
    public record ExportBundle(int schemaVersion, int revision, String manifestSha256, boolean saleReady,
                               CreatorRealmScaffold.Marketplace marketplace, List<ExportEntry> entries) {
        public ExportBundle { entries = List.copyOf(entries); }
    }
    private record Header(int schemaVersion, String realmId, Set<String> reservedIds) {
        private Header { reservedIds = Set.copyOf(reservedIds); }
    }
    private record Stored(int schemaVersion, int revision, String parentSha256, Manifest manifest) { }
    private record Loaded(Snapshot selected, List<Revision> revisions) {
        private Loaded { revisions = List.copyOf(revisions); }
    }

    private final Path root;
    private final Path originals;
    private final Path snapshots;
    private final Header header;
    private final FileChannel lockChannel;
    private final FileLock lock;
    private boolean closed;

    public static CreatorIntakeStore create(Path root, Set<String> reservedIds) throws IOException {
        return new CreatorIntakeStore(root, true, Set.copyOf(reservedIds));
    }

    public static CreatorIntakeStore open(Path root) throws IOException {
        return new CreatorIntakeStore(root, false, Set.of());
    }

    private CreatorIntakeStore(Path location, boolean create, Set<String> reservedIds) throws IOException {
        Path requested = location.toAbsolutePath().normalize();
        if (requested.getParent() == null) throw new IOException("Intake must name a new private directory");
        if (create) {
            requireValid(CreatorRealmScaffold.empty(), reservedIds);
            Files.createDirectories(requested.getParent());
            Files.createDirectory(requested);
        }
        directory(requested);
        root = requested.toRealPath();
        originals = root.resolve("originals");
        snapshots = root.resolve("snapshots");
        lockChannel = FileChannel.open(root.resolve(".writer.lock"), StandardOpenOption.CREATE,
                StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS);
        try {
            lock = lockChannel.tryLock();
            if (lock == null) throw new IOException("Intake already has a writer");
        } catch (IOException | OverlappingFileLockException e) {
            lockChannel.close();
            throw new IOException("Cannot acquire intake writer lock", e);
        }
        try {
            if (create) {
                Files.createDirectory(originals);
                Files.createDirectory(snapshots);
                header = new Header(1, CreatorRealmScaffold.REALM_ID, reservedIds);
                publish(root.resolve("header.json"), JSON.writeValueAsBytes(header));
                writeSnapshot(1, null, CreatorRealmScaffold.empty());
            } else {
                directory(originals);
                directory(snapshots);
                header = JSON.readValue(readBytes(root.resolve("header.json")), Header.class);
                if (header.schemaVersion() != 1 || !CreatorRealmScaffold.REALM_ID.equals(header.realmId())) {
                    throw new IOException("Unsupported creator intake header");
                }
                requireValid(CreatorRealmScaffold.empty(), header.reservedIds());
                load(0);
            }
        } catch (IOException | RuntimeException e) {
            lockChannel.close();
            throw e;
        }
    }

    public synchronized Snapshot current() throws IOException { return load(0).selected(); }
    public synchronized Snapshot read(int revision) throws IOException {
        if (revision < 1) throw new IOException("Revision must be positive");
        return load(revision).selected();
    }
    public synchronized List<Revision> history() throws IOException { return load(0).revisions(); }

    /** A stale revision refuses without replacing any snapshot, original or current version. */
    public synchronized Snapshot save(int expectedRevision, Manifest candidate) throws IOException {
        Snapshot previous = expected(expectedRevision);
        return commit(previous, candidate);
    }

    public synchronized Snapshot addEntry(int expectedRevision, String id, Role role, Attribution creator,
                                          String supersedesId) throws IOException {
        Snapshot previous = expected(expectedRevision);
        Entry entry = new Entry(id, role, Stage.DRAFT, supersedesId, null, null, null,
                creator == null ? new Attribution(null, null, null, null) : creator,
                SaleIntent.UNSET, List.of(), List.of(), List.of());
        List<Entry> entries = new ArrayList<>(previous.manifest().entries());
        entries.add(entry);
        return commit(previous, withEntries(previous.manifest(), entries));
    }

    public synchronized Snapshot editDraft(int expectedRevision, String entryId, DraftEdit edit) throws IOException {
        Objects.requireNonNull(edit, "edit");
        Snapshot previous = expected(expectedRevision);
        draft(find(previous.manifest(), entryId));
        return commit(previous, replace(previous.manifest(), entryId, entry -> {
            String preview = edit.previewOriginalId() == null ? null : entry.originals().stream()
                    .filter(original -> original.id().equals(edit.previewOriginalId())).findFirst()
                    .orElseThrow(() -> new IllegalArgumentException("Preview must name an attached original ID")).originalUri();
            return new Entry(entry.id(), entry.role(), entry.stage(), entry.supersedesId(), edit.name(), edit.description(), preview,
                    edit.creator() == null ? new Attribution(null, null, null, null) : edit.creator(),
                    edit.saleIntent() == null ? SaleIntent.UNSET : edit.saleIntent(), edit.componentIds(), entry.originals(), entry.ideas());
        }));
    }

    public synchronized Snapshot appendIdea(int expectedRevision, String entryId, String text) throws IOException {
        Snapshot previous = expected(expectedRevision);
        return commit(previous, replace(previous.manifest(), entryId, entry -> CreatorRealmScaffold.appendIdea(entry, text)));
    }

    /** Copy explicitly supplied local bytes; no original filename becomes a creative name or public URL. */
    public synchronized Snapshot attachOriginal(int expectedRevision, String entryId, String originalId, Path source,
                                                String provenance, boolean useAsPreview) throws IOException {
        Snapshot previous = expected(expectedRevision);
        Entry entry = find(previous.manifest(), entryId);
        draft(entry);
        if (entry.role() == Role.IDEA) throw new IOException("Attach art to a separate asset/component/assembly entry");
        Original probe = new Original(originalId, "urn:sha256:" + "0".repeat(64), "0".repeat(64), provenance);
        requireValid(replace(previous.manifest(), entryId, value -> withOriginal(value, probe, useAsPreview)), header.reservedIds());
        String hash = preserve(source);
        Original original = new Original(originalId, "urn:sha256:" + hash, hash, provenance);
        return commit(previous, replace(previous.manifest(), entryId, value -> withOriginal(value, original, useAsPreview)));
    }

    /** Final source content is immutable, but still only produces review-required metadata and no sale authority. */
    public synchronized Snapshot finalizeSourceContent(int expectedRevision, String entryId) throws IOException {
        Snapshot previous = expected(expectedRevision);
        Entry entry = find(previous.manifest(), entryId);
        draft(entry);
        List<String> missing = missing(entry, false);
        if (entry.role() == Role.IDEA) missing.add("IDEA_CANNOT_BE_FINAL_CONTENT");
        if (!missing.isEmpty()) throw new IOException("Cannot finalize source: " + String.join(", ", missing));
        Entry finalized = new Entry(entry.id(), entry.role(), Stage.FINAL, entry.supersedesId(), entry.name(), entry.description(),
                entry.previewUri(), entry.creator(), entry.saleIntent(), entry.componentIds(), entry.originals(), entry.ideas());
        return commit(previous, replace(previous.manifest(), entryId, value -> finalized));
    }

    /** Export JSON only to a new local file outside the private store; originals are never copied to the export. */
    public synchronized ExportBundle export(int revision, Path destination) throws IOException {
        Snapshot snapshot = read(revision);
        Path target = destination.toAbsolutePath().normalize();
        if (target.getParent() == null || target.getFileName() == null || target.startsWith(root)) {
            throw new IOException("Export must name a new file outside the private intake store");
        }
        Path parent = target.getParent().toRealPath();
        directory(parent);
        target = parent.resolve(target.getFileName());
        if (target.startsWith(root)) throw new IOException("Export must be outside the private intake store");
        List<ExportEntry> entries = new ArrayList<>();
        for (Entry entry : snapshot.manifest().entries()) {
            IslandTokenMetadata metadata = CreatorRealmScaffold.metadataDraft(snapshot.manifest(), entry.id(), header.reservedIds()).orElse(null);
            entries.add(new ExportEntry(entry.id(), entry.role(), entry.stage(), CreatorRealmScaffold.saleEligibility(entry).name(),
                    CreatorRealmScaffold.labels(entry), metadata, missing(entry, true)));
        }
        ExportBundle bundle = new ExportBundle(1, revision, snapshot.sha256(), false, snapshot.manifest().marketplace(), entries);
        publish(target, JSON.writeValueAsBytes(bundle));
        return bundle;
    }

    private Snapshot expected(int revision) throws IOException {
        Snapshot current = current();
        if (revision != current.revision()) throw new IOException("Stale intake revision: expected " + revision + ", current " + current.revision());
        return current;
    }

    private Snapshot commit(Snapshot previous, Manifest next) throws IOException {
        requireValid(next, header.reservedIds());
        checkUpdate(previous.manifest(), next);
        if (previous.manifest().equals(next)) throw new IOException("Intake has no changes to save");
        verifyOriginals(next);
        return writeSnapshot(previous.revision() + 1, previous.sha256(), next);
    }

    private void checkUpdate(Manifest previous, Manifest next) throws IOException {
        List<String> errors = CreatorRealmScaffold.validateUpdate(previous, next, header.reservedIds());
        Map<String, Entry> nextEntries = new HashMap<>();
        for (Entry entry : next.entries()) nextEntries.put(entry.id(), entry);
        for (Entry before : previous.entries()) {
            Entry after = nextEntries.get(before.id());
            if (after != null && !Objects.equals(before.supersedesId(), after.supersedesId())) {
                throw new IOException("Preserve predecessor lineage for " + before.id());
            }
        }
        if (!errors.isEmpty()) throw new IOException(String.join("; ", errors));
    }

    private Snapshot writeSnapshot(int revision, String parent, Manifest manifest) throws IOException {
        if (revision > MAX_REVISIONS) throw new IOException("Intake revision limit reached");
        byte[] bytes = JSON.writeValueAsBytes(new Stored(1, revision, parent, manifest));
        if (bytes.length > MAX_METADATA_BYTES) throw new IOException("Manifest exceeds size limit");
        publish(snapshots.resolve(String.format(java.util.Locale.ROOT, "%08d.json", revision)), bytes);
        return new Snapshot(revision, hash(bytes), parent, manifest);
    }

    private Loaded load(int requestedRevision) throws IOException {
        requireOpen();
        List<Path> files;
        try (var stream = Files.list(snapshots)) {
            files = stream.filter(path -> path.getFileName().toString().matches("[0-9]{8}\\.json")).sorted().toList();
        }
        if (files.isEmpty() || files.size() > MAX_REVISIONS) throw new IOException("Missing or excessive intake history");
        Snapshot previous = null;
        Snapshot selected = null;
        List<Revision> revisions = new ArrayList<>();
        for (int index = 0; index < files.size(); index++) {
            int number = index + 1;
            if (!files.get(index).getFileName().toString().equals(String.format(java.util.Locale.ROOT, "%08d.json", number))) {
                throw new IOException("Intake history has a missing revision");
            }
            byte[] bytes = readBytes(files.get(index));
            Stored stored = JSON.readValue(bytes, Stored.class);
            if (stored.schemaVersion() != 1 || stored.revision() != number
                    || !Objects.equals(stored.parentSha256(), previous == null ? null : previous.sha256())) {
                throw new IOException("Intake history digest chain mismatch");
            }
            requireValid(stored.manifest(), header.reservedIds());
            if (previous != null) checkUpdate(previous.manifest(), stored.manifest());
            previous = new Snapshot(number, hash(bytes), stored.parentSha256(), stored.manifest());
            if (requestedRevision == number) selected = previous;
            revisions.add(new Revision(number, previous.sha256(), previous.parentSha256(), previous.manifest().entries().size()));
        }
        if (requestedRevision == 0) selected = previous;
        if (selected == null) throw new IOException("Unknown intake revision " + requestedRevision);
        verifyOriginals(previous.manifest());
        return new Loaded(selected, List.copyOf(revisions));
    }

    private String preserve(Path source) throws IOException {
        BasicFileAttributes before = regular(source);
        if (before.size() > MAX_ORIGINAL_BYTES) throw new IOException("Original exceeds size limit");
        Path temporary = Files.createTempFile(originals, "original-", ".pending");
        try {
            MessageDigest digest = digest();
            long count = 0;
            try (InputStream input = Files.newInputStream(source, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS);
                 FileChannel output = FileChannel.open(temporary, StandardOpenOption.WRITE)) {
                byte[] buffer = new byte[64 * 1024];
                for (int length; (length = input.read(buffer)) != -1;) {
                    count += length;
                    if (count > MAX_ORIGINAL_BYTES) throw new IOException("Original exceeds size limit");
                    digest.update(buffer, 0, length);
                    ByteBuffer bytes = ByteBuffer.wrap(buffer, 0, length);
                    while (bytes.hasRemaining()) output.write(bytes);
                }
                output.force(true);
            }
            BasicFileAttributes after = regular(source);
            if (count != before.size() || before.size() != after.size() || !before.lastModifiedTime().equals(after.lastModifiedTime())
                    || !Objects.equals(before.fileKey(), after.fileKey())) throw new IOException("Original changed while copying");
            String hash = HexFormat.of().formatHex(digest.digest());
            Path target = originals.resolve(hash);
            if (Files.exists(target, LinkOption.NOFOLLOW_LINKS)) {
                if (!hash.equals(hashFile(target))) throw new IOException("Stored original digest mismatch");
            } else {
                Files.createLink(target, temporary);
            }
            return hash;
        } finally { Files.deleteIfExists(temporary); }
    }

    private void verifyOriginals(Manifest manifest) throws IOException {
        Set<String> verified = new HashSet<>();
        for (Entry entry : manifest.entries()) for (Original original : entry.originals()) {
            if (verified.add(original.sha256()) && !original.sha256().equals(hashFile(originals.resolve(original.sha256())))) {
                throw new IOException("Stored original digest mismatch for " + original.id());
            }
        }
    }

    private static String hashFile(Path file) throws IOException {
        if (regular(file).size() > MAX_ORIGINAL_BYTES) throw new IOException("Original exceeds size limit");
        MessageDigest digest = digest();
        long count = 0;
        try (InputStream input = Files.newInputStream(file, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) {
            byte[] buffer = new byte[64 * 1024];
            for (int length; (length = input.read(buffer)) != -1;) {
                count += length;
                if (count > MAX_ORIGINAL_BYTES) throw new IOException("Original exceeds size limit");
                digest.update(buffer, 0, length);
            }
        }
        return HexFormat.of().formatHex(digest.digest());
    }

    /** Same-directory hard-link publication is atomic and refuses existing targets, unlike atomic replace. */
    private static void publish(Path target, byte[] bytes) throws IOException {
        Path temporary = Files.createTempFile(target.getParent(), ".intake-", ".pending");
        try {
            try (FileChannel output = FileChannel.open(temporary, StandardOpenOption.WRITE)) {
                ByteBuffer buffer = ByteBuffer.wrap(bytes);
                while (buffer.hasRemaining()) output.write(buffer);
                output.force(true);
            }
            Files.createLink(target, temporary);
        } finally { Files.deleteIfExists(temporary); }
    }

    private static byte[] readBytes(Path file) throws IOException {
        if (regular(file).size() > MAX_METADATA_BYTES) throw new IOException("Intake metadata exceeds size limit");
        try (InputStream input = Files.newInputStream(file, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) {
            byte[] bytes = input.readNBytes(MAX_METADATA_BYTES + 1);
            if (bytes.length > MAX_METADATA_BYTES) throw new IOException("Intake metadata exceeds size limit");
            return bytes;
        }
    }
    private static BasicFileAttributes regular(Path path) throws IOException {
        BasicFileAttributes attributes = Files.readAttributes(path, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        if (!attributes.isRegularFile()) throw new IOException("Expected a regular local file: " + path.getFileName());
        return attributes;
    }
    private static void directory(Path path) throws IOException {
        if (!Files.isDirectory(path, LinkOption.NOFOLLOW_LINKS)) throw new IOException("Expected an intake directory");
    }
    private static void requireValid(Manifest manifest, Set<String> reservedIds) throws IOException {
        if (manifest == null) throw new IOException("Missing intake manifest");
        List<String> errors = CreatorRealmScaffold.validate(manifest, reservedIds);
        if (!errors.isEmpty()) throw new IOException(String.join("; ", errors));
    }
    private static Entry find(Manifest manifest, String id) throws IOException {
        return manifest.entries().stream().filter(entry -> entry.id().equals(id)).findFirst()
                .orElseThrow(() -> new IOException("Unknown content ID: " + id));
    }
    private static Manifest replace(Manifest manifest, String id, UnaryOperator<Entry> operation) throws IOException {
        find(manifest, id);
        List<Entry> entries = new ArrayList<>();
        try {
            for (Entry entry : manifest.entries()) entries.add(entry.id().equals(id) ? operation.apply(entry) : entry);
        } catch (IllegalArgumentException e) { throw new IOException(e.getMessage(), e); }
        return withEntries(manifest, entries);
    }
    private static Manifest withEntries(Manifest manifest, List<Entry> entries) {
        return new Manifest(manifest.schemaVersion(), manifest.identity(), manifest.realmAttribution(), manifest.enabled(), manifest.ready(),
                manifest.creative(), manifest.connection(), manifest.marketplace(), entries);
    }
    private static Entry withOriginal(Entry entry, Original original, boolean preview) {
        List<Original> sources = new ArrayList<>(entry.originals());
        sources.add(original);
        return new Entry(entry.id(), entry.role(), entry.stage(), entry.supersedesId(), entry.name(), entry.description(),
                preview ? original.originalUri() : entry.previewUri(), entry.creator(), entry.saleIntent(), entry.componentIds(), sources, entry.ideas());
    }
    private static List<String> missing(Entry entry, boolean includeStage) {
        List<String> missing = new ArrayList<>();
        if (includeStage && entry.stage() != Stage.FINAL) missing.add("DRAFT_CONTENT");
        if (entry.name() == null || entry.name().isBlank()) missing.add("NAME");
        if (entry.description() == null || entry.description().isBlank()) missing.add("DESCRIPTION");
        if (entry.creator().handle() == null) missing.add("CREATOR_ATTRIBUTION");
        if (entry.originals().isEmpty()) missing.add("ORIGINAL");
        if (entry.originals().stream().noneMatch(original -> original.originalUri().equals(entry.previewUri()))) missing.add("PINNED_PREVIEW");
        return missing;
    }
    private static void draft(Entry entry) throws IOException {
        if (entry.stage() != Stage.DRAFT) throw new IOException("Final content requires a new ID and retained predecessor");
    }
    private static MessageDigest digest() {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch (NoSuchAlgorithmException e) { throw new IllegalStateException("SHA-256 unavailable", e); }
    }
    private static String hash(byte[] bytes) { return HexFormat.of().formatHex(digest().digest(bytes)); }
    private void requireOpen() throws IOException {
        if (closed || !lock.isValid()) throw new IOException("Intake store is closed");
        directory(root); directory(originals); directory(snapshots);
    }
    @Override public synchronized void close() throws IOException {
        closed = true;
        lockChannel.close();
    }
}
