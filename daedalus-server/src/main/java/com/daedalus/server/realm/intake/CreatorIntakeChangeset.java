// SPDX-License-Identifier: MIT
package com.daedalus.server.realm.intake;

import com.daedalus.server.realm.CreatorRealmScaffold.Attribution;
import com.daedalus.server.realm.CreatorRealmScaffold.Role;
import com.daedalus.server.realm.intake.CreatorIntakeHostSession.HostBinding;
import com.fasterxml.jackson.annotation.JsonSubTypes;
import com.fasterxml.jackson.annotation.JsonTypeInfo;
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
import java.util.HashSet;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.Set;

/**
 * Ordered local authoring through one caller-owned host session. Each step commits separately: this is not
 * a rollback transaction or universal exactly-once service. The caller must not concurrently use that session.
 * Private, new-only receipt files record request, frozen inputs, intent before delegation and actual result
 * before the next operation. A stopped/incomplete receipt requires explicit reconciliation, never auto-replay.
 * Only a verified completed receipt can return its historical result without reapplying commands.
 * Receipt directories retain private original bytes (up to 1 GiB); they are not public metadata exports.
 */
public final class CreatorIntakeChangeset {
    public static final int MAX_OPERATIONS = 128;
    public static final long MAX_INPUT_BYTES = 1024L * 1024 * 1024;
    private static final String HASH = "[0-9a-f]{64}";
    private static final ObjectMapper JSON = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT)
            .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION).enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);

    @JsonTypeInfo(use = JsonTypeInfo.Id.NAME, property = "type")
    @JsonSubTypes({@JsonSubTypes.Type(value = Add.class, name = "add"), @JsonSubTypes.Type(value = Revise.class, name = "revise"),
            @JsonSubTypes.Type(value = Edit.class, name = "edit"), @JsonSubTypes.Type(value = Idea.class, name = "idea"),
            @JsonSubTypes.Type(value = Attach.class, name = "attach"), @JsonSubTypes.Type(value = Finalize.class, name = "finalize-source")})
    public sealed interface Operation permits Add, Revise, Edit, Idea, Attach, Finalize { String commandId(); }
    public record Add(String commandId, String id, Role role, Attribution creator, String supersedesId) implements Operation { }
    public record Revise(String commandId, String id, String predecessorId, Attribution creator) implements Operation { }
    public record Edit(String commandId, String id, CreatorIntakeStore.DraftEdit edit) implements Operation { }
    public record Idea(String commandId, String id, String text) implements Operation { }
    public record Attach(String commandId, String id, String originalId, String sourcePath, String provenance,
                         boolean useAsPreview) implements Operation { }
    public record Finalize(String commandId, String id) implements Operation { }
    public record Request(int schemaVersion, String operationId, int expectedRevision, String expectedSha256,
                          HostBinding host, List<Operation> operations) {
        public Request { operations = List.copyOf(operations); }
    }
    public record SnapshotRef(int revision, String sha256) { }
    public enum Status { COMPLETE, PARTIAL, UNCERTAIN }
    public enum StepStatus { APPLIED, REFUSED, UNCERTAIN }
    /** The copy flag concerns the delegated intake attachment; frozen private receipt inputs are retained separately. */
    public record StepResult(int index, String commandId, StepStatus status, SnapshotRef before, SnapshotRef after,
                             boolean attachmentBytesMayExist, String error) { }
    /** Indices are zero-based. For UNCERTAIN, end is the last observed snapshot and does not rule out later unobserved effects. */
    public record Outcome(int schemaVersion, String operationId, String requestSha256, HostBinding host, Status status,
                          boolean replayed, SnapshotRef base, SnapshotRef end, List<StepResult> steps,
                          Integer uncertainStepIndex, Integer nextUnexecutedIndex, String receiptDirectory, String error) {
        public Outcome { steps = List.copyOf(steps); }
    }
    private record InputPin(String commandId, String sourcePath, String sha256, long size) { }
    private record Header(int schemaVersion, String requestSha256, Request request, String attachmentBase, List<InputPin> inputs) {
        private Header { inputs = List.copyOf(inputs); }
    }
    private record Intent(int schemaVersion, String requestSha256, int index, String commandId, SnapshotRef before) { }
    @FunctionalInterface interface CommitBoundary {
        void beforeResult(int index, CreatorIntakeStore.Snapshot committed) throws IOException;
    }

    private CreatorIntakeChangeset() { }

    public static Outcome apply(CreatorIntakeHostSession session, Request request, Path attachmentBase,
                                Path privateReceiptDirectory) throws IOException {
        return apply(session, request, attachmentBase, privateReceiptDirectory, (index, committed) -> { });
    }

    // A local fault seam exercises the real commit/result boundary without replacing the store or inventing outcomes.
    static Outcome apply(CreatorIntakeHostSession session, Request request, Path attachmentBase,
                         Path privateReceiptDirectory, CommitBoundary boundary) throws IOException {
        validate(request);
        if (!request.host().equals(session.binding())) throw new IOException("Changeset host context differs from the opened session");
        String requestSha = hash(JSON.writeValueAsBytes(request));
        Path base = directory(attachmentBase);
        Path receipt = target(privateReceiptDirectory);
        boolean existing = Files.exists(receipt, LinkOption.NOFOLLOW_LINKS);
        if (!existing) {
            requireBase(session.current(), request);
            Files.createDirectory(receipt);
        }
        directory(receipt);
        try (FileChannel channel = receiptChannel(receipt, existing); FileLock lock = acquire(channel)) {
            if (!lock.isValid()) throw new IOException("Changeset receipt lock is invalid");
            if (existing) return replay(session, request, requestSha, base, receipt);
            try {
                Files.createDirectory(receipt.resolve("inputs"));
                List<InputPin> pins = freeze(request, base, receipt.resolve("inputs"));
                Header header = new Header(1, requestSha, request, base.toString(), pins);
                publish(receipt.resolve("request.json"), header);
                return execute(session, header, receipt, boundary);
            } catch (IOException | RuntimeException failure) {
                throw new IOException("Changeset stopped; preserve and reconcile private receipt at " + receipt + ": " + detail(failure), failure);
            }
        }
    }

    private static Outcome execute(CreatorIntakeHostSession session, Header header, Path receipt,
                                   CommitBoundary boundary) throws IOException {
        Request request = header.request();
        SnapshotRef base = new SnapshotRef(request.expectedRevision(), request.expectedSha256());
        SnapshotRef previous = base;
        List<StepResult> results = new ArrayList<>();
        for (int index = 0; index < request.operations().size(); index++) {
            Operation operation = request.operations().get(index);
            try {
                SnapshotRef actual = ref(session.current());
                if (!actual.equals(previous)) throw new IOException("Intake advanced between changeset steps; no next operation delegated");
                publish(step(receipt, index, "intent"), new Intent(1, header.requestSha256(), index, operation.commandId(), previous));
            } catch (IOException | RuntimeException failure) {
                return finish(header, receipt, Status.PARTIAL, base, previous, results, null, index,
                        "Next step was not delegated: " + detail(failure));
            }
            CreatorIntakeStore.Snapshot committed;
            try {
                committed = delegate(session, operation, previous.revision(), header.inputs(), receipt.resolve("inputs"));
            } catch (IOException | RuntimeException failure) {
                SnapshotRef observed = null;
                String error = detail(failure);
                try { observed = ref(session.current()); }
                catch (IOException | RuntimeException readFailure) { error += "; readback unavailable: " + detail(readFailure); }
                boolean unchanged = previous.equals(observed);
                StepResult result = new StepResult(index, operation.commandId(), unchanged ? StepStatus.REFUSED : StepStatus.UNCERTAIN,
                        previous, observed, operation instanceof Attach, error);
                results.add(result);
                try { publish(step(receipt, index, "result"), result); }
                catch (IOException | RuntimeException writeFailure) {
                    return uncertain(header, receipt, base, observed == null ? previous : observed, results, index,
                            "Failed-step result was not confirmed durable: " + detail(writeFailure));
                }
                return finish(header, receipt, unchanged ? Status.PARTIAL : Status.UNCERTAIN, base,
                        observed == null ? previous : observed, results, unchanged ? null : index, next(request, index), error);
            }
            SnapshotRef after = ref(committed);
            if (!Objects.equals(committed.parentSha256(), previous.sha256())) {
                results.add(new StepResult(index, operation.commandId(), StepStatus.UNCERTAIN, previous, after,
                        operation instanceof Attach, "Returned snapshot is not a direct child of the intended before state"));
                return uncertain(header, receipt, base, after, results, index, "Unexpected authoring parent digest");
            }
            StepResult applied = new StepResult(index, operation.commandId(), StepStatus.APPLIED, previous, after,
                    operation instanceof Attach, null);
            try {
                boundary.beforeResult(index, committed);
                publish(step(receipt, index, "result"), applied);
            } catch (IOException | RuntimeException failure) {
                results.add(new StepResult(index, operation.commandId(), StepStatus.UNCERTAIN, previous, after,
                        operation instanceof Attach, "Commit returned, but result receipt was not confirmed durable: " + detail(failure)));
                return uncertain(header, receipt, base, after, results, index, detail(failure));
            }
            results.add(applied);
            previous = after;
        }
        return finish(header, receipt, Status.COMPLETE, base, previous, results, null, null, null);
    }

    private static Outcome uncertain(Header header, Path receipt, SnapshotRef base, SnapshotRef end,
                                     List<StepResult> results, int index, String error) {
        // The durable intent (and any prefix results) is the evidence. No replay, rollback or best-effort continuation occurs.
        return new Outcome(1, header.request().operationId(), header.requestSha256(), header.request().host(), Status.UNCERTAIN,
                false, base, end, results, index, next(header.request(), index), receipt.toString(), error);
    }

    private static Outcome finish(Header header, Path receipt, Status status, SnapshotRef base, SnapshotRef end,
                                  List<StepResult> results, Integer uncertain, Integer next, String error) {
        Outcome outcome = new Outcome(1, header.request().operationId(), header.requestSha256(), header.request().host(), status,
                false, base, end, results, uncertain, next, receipt.toString(), error);
        try { publish(receipt.resolve("outcome.json"), outcome); }
        catch (IOException | RuntimeException failure) {
            return new Outcome(1, outcome.operationId(), outcome.requestSha256(), outcome.host(), Status.UNCERTAIN, false,
                    base, end, results, uncertain, next, receipt.toString(), "Final receipt was not confirmed durable: " + detail(failure));
        }
        return outcome;
    }

    private static Outcome replay(CreatorIntakeHostSession session, Request request, String sha, Path base, Path receipt) throws IOException {
        Header header = read(receipt.resolve("request.json"), Header.class);
        if (header.schemaVersion() != 1 || !header.requestSha256().equals(sha) || !header.request().equals(request)
                || !header.attachmentBase().equals(base.toString())) throw new IOException("Receipt request/context/input-base identity conflict");
        validatePins(header);
        Outcome outcome;
        try { outcome = read(receipt.resolve("outcome.json"), Outcome.class); }
        catch (IOException | RuntimeException failure) {
            throw new IOException("Incomplete or uncertain receipt requires explicit reconciliation; no replay: " + receipt, failure);
        }
        if (outcome.schemaVersion() != 1 || outcome.status() != Status.COMPLETE || outcome.replayed()
                || !outcome.operationId().equals(request.operationId()) || !outcome.requestSha256().equals(sha)
                || !outcome.host().equals(request.host()) || outcome.steps().size() != request.operations().size()
                || outcome.uncertainStepIndex() != null || outcome.nextUnexecutedIndex() != null) {
            throw new IOException("Partial, uncertain or invalid receipt requires explicit reconciliation; no replay: " + receipt);
        }
        Set<String> expectedFiles = new HashSet<>(Set.of(".receipt.lock", "request.json", "outcome.json", "inputs"));
        SnapshotRef previous = new SnapshotRef(request.expectedRevision(), request.expectedSha256());
        if (!outcome.base().equals(previous)) throw new IOException("Completed receipt base mismatch");
        verifyHistorical(session, previous);
        for (int index = 0; index < request.operations().size(); index++) {
            Intent intent = read(step(receipt, index, "intent"), Intent.class);
            StepResult result = read(step(receipt, index, "result"), StepResult.class);
            String command = request.operations().get(index).commandId();
            if (intent.schemaVersion() != 1 || !intent.requestSha256().equals(sha) || intent.index() != index
                    || !intent.commandId().equals(command) || !intent.before().equals(previous)
                    || result.index() != index || !result.commandId().equals(command) || result.status() != StepStatus.APPLIED
                    || !result.before().equals(previous) || result.after() == null || result.after().revision() <= previous.revision()
                    || !result.equals(outcome.steps().get(index))) throw new IOException("Completed receipt step chain mismatch");
            CreatorIntakeStore.Snapshot historical = verifyHistorical(session, result.after());
            if (!Objects.equals(historical.parentSha256(), previous.sha256())) throw new IOException("Receipt step skips intake history");
            if (request.operations().get(index) instanceof Attach attachment) {
                verifyAttached(historical, attachment, pin(header.inputs(), command));
            }
            previous = result.after();
            expectedFiles.add(name(step(receipt, index, "intent")));
            expectedFiles.add(name(step(receipt, index, "result")));
        }
        if (!outcome.end().equals(previous)) throw new IOException("Completed receipt ending snapshot mismatch");
        try (var files = Files.list(receipt)) {
            Set<String> actual = new HashSet<>();
            for (Path path : files.toList()) actual.add(name(path));
            if (!actual.equals(expectedFiles)) throw new IOException("Unknown files in completed receipt");
        }
        verifyFrozen(header.inputs(), receipt.resolve("inputs"));
        return new Outcome(1, outcome.operationId(), sha, outcome.host(), Status.COMPLETE, true, outcome.base(), outcome.end(),
                outcome.steps(), null, null, receipt.toString(), null);
    }

    private static CreatorIntakeStore.Snapshot delegate(CreatorIntakeHostSession session, Operation operation, int expected,
                                                        List<InputPin> pins, Path inputs) throws IOException {
        return switch (operation) {
            case Add value -> session.addEntry(expected, value.id(), value.role(), value.creator(), value.supersedesId());
            case Revise value -> session.reviseEntry(expected, value.id(), value.predecessorId(), value.creator());
            case Edit value -> session.editDraft(expected, value.id(), value.edit());
            case Idea value -> session.appendIdea(expected, value.id(), value.text());
            case Attach value -> {
                InputPin pin = pin(pins, value.commandId());
                Path source = inputs.resolve(pin.sha256());
                if (regular(source).size() != pin.size() || !fileHash(source).equals(pin.sha256())) throw new IOException("Frozen input changed");
                CreatorIntakeStore.Snapshot saved = session.attachOriginal(expected, value.id(), value.originalId(), source,
                        value.provenance(), value.useAsPreview());
                verifyAttached(saved, value, pin);
                yield saved;
            }
            case Finalize value -> session.finalizeSourceContent(expected, value.id());
        };
    }

    private static List<InputPin> freeze(Request request, Path base, Path inputs) throws IOException {
        List<InputPin> pins = new ArrayList<>();
        long total = 0;
        for (Operation operation : request.operations()) if (operation instanceof Attach attachment) {
            Path source = relativeSource(base, attachment.sourcePath());
            BasicFileAttributes before = regular(source);
            total += before.size();
            if (before.size() > CreatorIntakeStore.MAX_ORIGINAL_BYTES || total > MAX_INPUT_BYTES) throw new IOException("Attachment byte budget exceeded");
            Path temporary = Files.createTempFile(inputs, ".input-", ".pending");
            MessageDigest digest = digest();
            long count = 0;
            try (InputStream input = Files.newInputStream(source, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS);
                 FileChannel output = FileChannel.open(temporary, StandardOpenOption.WRITE)) {
                byte[] buffer = new byte[64 * 1024];
                for (int length; (length = input.read(buffer)) != -1;) {
                    count += length;
                    if (count > before.size()) throw new IOException("Attachment changed while freezing");
                    digest.update(buffer, 0, length);
                    ByteBuffer bytes = ByteBuffer.wrap(buffer, 0, length);
                    while (bytes.hasRemaining()) output.write(bytes);
                }
                output.force(true);
            }
            BasicFileAttributes after = regular(source);
            if (count != before.size() || before.size() != after.size() || !before.lastModifiedTime().equals(after.lastModifiedTime())
                    || !Objects.equals(before.fileKey(), after.fileKey())) throw new IOException("Attachment changed while freezing");
            String sha = HexFormat.of().formatHex(digest.digest());
            Path target = inputs.resolve(sha);
            if (Files.exists(target, LinkOption.NOFOLLOW_LINKS)) {
                if (!fileHash(target).equals(sha)) throw new IOException("Frozen input digest mismatch");
            } else { Files.createLink(target, temporary); }
            Files.delete(temporary);
            pins.add(new InputPin(attachment.commandId(), attachment.sourcePath(), sha, count));
        }
        return List.copyOf(pins);
    }

    private static void verifyFrozen(List<InputPin> pins, Path inputs) throws IOException {
        directory(inputs);
        Set<String> expected = new HashSet<>();
        for (InputPin pin : pins) {
            if (pin.sha256() == null || !pin.sha256().matches(HASH) || pin.size() < 0
                    || pin.size() > CreatorIntakeStore.MAX_ORIGINAL_BYTES) throw new IOException("Invalid frozen input pin");
            Path file = inputs.resolve(pin.sha256());
            if (regular(file).size() != pin.size() || !fileHash(file).equals(pin.sha256())) throw new IOException("Frozen receipt input mismatch");
            expected.add(pin.sha256());
        }
        try (var files = Files.list(inputs)) {
            Set<String> actual = new HashSet<>();
            for (Path file : files.toList()) actual.add(name(file));
            if (!actual.equals(expected)) throw new IOException("Unknown or missing frozen receipt input");
        }
    }

    private static InputPin pin(List<InputPin> pins, String commandId) throws IOException {
        return pins.stream().filter(input -> input.commandId().equals(commandId)).findFirst()
                .orElseThrow(() -> new IOException("Missing frozen attachment pin"));
    }

    private static void validatePins(Header header) throws IOException {
        List<Attach> attachments = header.request().operations().stream().filter(Attach.class::isInstance).map(Attach.class::cast).toList();
        if (header.inputs().size() != attachments.size()) throw new IOException("Receipt attachment pin count mismatch");
        Set<String> commands = new HashSet<>();
        long total = 0;
        for (InputPin input : header.inputs()) {
            if (!commands.add(input.commandId()) || input.sha256() == null || !input.sha256().matches(HASH)
                    || input.size() < 0 || input.size() > CreatorIntakeStore.MAX_ORIGINAL_BYTES
                    || attachments.stream().noneMatch(value -> value.commandId().equals(input.commandId())
                    && value.sourcePath().equals(input.sourcePath()))) throw new IOException("Receipt attachment pin identity mismatch");
            total += input.size();
            if (total > MAX_INPUT_BYTES) throw new IOException("Receipt attachment byte budget exceeded");
        }
    }

    private static void verifyAttached(CreatorIntakeStore.Snapshot snapshot, Attach attachment, InputPin pin) throws IOException {
        boolean matches = snapshot.manifest().entries().stream().filter(entry -> entry.id().equals(attachment.id()))
                .flatMap(entry -> entry.originals().stream()).anyMatch(original -> original.id().equals(attachment.originalId())
                && original.sha256().equals(pin.sha256()) && original.provenance().equals(attachment.provenance()));
        if (!matches) throw new IOException("Attached content differs from frozen request; a revision may already have committed");
    }

    private static void validate(Request request) throws IOException {
        if (request == null || request.schemaVersion() != 1 || !label(request.operationId()) || request.expectedRevision() < 1
                || request.expectedSha256() == null || !request.expectedSha256().matches(HASH) || request.host() == null
                || request.operations().isEmpty() || request.operations().size() > MAX_OPERATIONS) throw new IOException("Invalid versioned changeset request");
        Set<String> commands = new HashSet<>();
        for (Operation operation : request.operations()) {
            if (operation == null || !label(operation.commandId()) || !commands.add(operation.commandId())) {
                throw new IOException("Invalid/duplicate command ID");
            }
            boolean valid = switch (operation) {
                case Add value -> id(value.id()) && value.role() != null && (value.supersedesId() == null || id(value.supersedesId()));
                case Revise value -> id(value.id()) && id(value.predecessorId());
                case Edit value -> id(value.id()) && value.edit() != null;
                case Idea value -> id(value.id()) && value.text() != null && !value.text().isBlank();
                case Attach value -> id(value.id()) && id(value.originalId()) && relative(value.sourcePath())
                        && value.provenance() != null && !value.provenance().isBlank();
                case Finalize value -> id(value.id());
            };
            if (!valid) throw new IOException("Invalid parameters for command " + operation.commandId());
        }
        if (JSON.writeValueAsBytes(request).length > CreatorIntakeStore.MAX_METADATA_BYTES) throw new IOException("Changeset exceeds metadata byte budget");
    }

    private static boolean relative(String value) {
        if (value == null || value.isBlank() || value.contains("\\") || value.contains(":")) return false;
        Path path = Path.of(value);
        if (path.isAbsolute()) return false;
        for (Path part : path) if (part.toString().equals(".") || part.toString().equals("..")) return false;
        return true;
    }
    private static Path relativeSource(Path base, String value) throws IOException {
        if (!relative(value)) throw new IOException("Attachment must be an explicit relative local path without traversal");
        Path requested = base.resolve(value);
        regular(requested);
        Path source = requested.toRealPath();
        if (!source.startsWith(base)) throw new IOException("Attachment escapes the explicit input base");
        return source;
    }
    private static boolean id(String value) { return value != null && value.length() <= 48 && value.matches("deathhimself_[a-z0-9_-]+"); }
    private static boolean label(String value) { return value != null && value.matches("[A-Za-z0-9][A-Za-z0-9_.-]{0,63}"); }
    private static void requireBase(CreatorIntakeStore.Snapshot snapshot, Request request) throws IOException {
        if (snapshot.revision() != request.expectedRevision() || !snapshot.sha256().equals(request.expectedSha256())) {
            throw new IOException("Stale changeset base revision/digest");
        }
    }
    private static CreatorIntakeStore.Snapshot verifyHistorical(CreatorIntakeHostSession session, SnapshotRef reference) throws IOException {
        if (reference == null) throw new IOException("Missing receipt historical reference");
        CreatorIntakeStore.Snapshot historical = session.read(reference.revision());
        if (!ref(historical).equals(reference)) throw new IOException("Receipt/intake historical digest mismatch");
        return historical;
    }
    private static SnapshotRef ref(CreatorIntakeStore.Snapshot snapshot) { return new SnapshotRef(snapshot.revision(), snapshot.sha256()); }
    private static Integer next(Request request, int index) { return index + 1 < request.operations().size() ? index + 1 : null; }
    private static Path step(Path receipt, int index, String kind) { return receipt.resolve(String.format(Locale.ROOT, "%04d-%s.json", index + 1, kind)); }
    private static FileLock acquire(FileChannel channel) throws IOException {
        try {
            FileLock lock = channel.tryLock();
            if (lock == null) throw new IOException("Changeset receipt has another writer");
            return lock;
        } catch (OverlappingFileLockException failure) { throw new IOException("Changeset receipt has another writer", failure); }
    }
    private static FileChannel receiptChannel(Path receipt, boolean existing) throws IOException {
        Path lock = receipt.resolve(".receipt.lock");
        if (existing) {
            regular(lock);
            return FileChannel.open(lock, StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS);
        }
        return FileChannel.open(lock, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS);
    }
    private static void publish(Path target, Object value) throws IOException {
        byte[] bytes = JSON.writeValueAsBytes(value);
        if (bytes.length > CreatorIntakeStore.MAX_METADATA_BYTES) throw new IOException("Receipt metadata exceeds byte budget");
        Path parent = target.getParent();
        if (parent == null) throw new IOException("Receipt publication requires a parent");
        Path temporary = Files.createTempFile(parent, ".receipt-", ".pending");
        try (FileChannel output = FileChannel.open(temporary, StandardOpenOption.WRITE)) {
            ByteBuffer buffer = ByteBuffer.wrap(bytes);
            while (buffer.hasRemaining()) output.write(buffer);
            output.force(true);
        }
        Files.createLink(target, temporary);
        Files.delete(temporary);
    }
    private static <T> T read(Path file, Class<T> type) throws IOException {
        if (regular(file).size() > CreatorIntakeStore.MAX_METADATA_BYTES) throw new IOException("Receipt metadata exceeds byte budget");
        try (InputStream input = Files.newInputStream(file, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) {
            byte[] bytes = input.readNBytes(CreatorIntakeStore.MAX_METADATA_BYTES + 1);
            if (bytes.length > CreatorIntakeStore.MAX_METADATA_BYTES) throw new IOException("Receipt metadata exceeds byte budget");
            T value = JSON.readValue(bytes, type);
            if (value == null) throw new IOException("Missing receipt metadata");
            return value;
        }
    }
    private static String fileHash(Path file) throws IOException {
        if (regular(file).size() > CreatorIntakeStore.MAX_ORIGINAL_BYTES) throw new IOException("Frozen original exceeds byte budget");
        MessageDigest digest = digest();
        long count = 0;
        try (InputStream input = Files.newInputStream(file, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) {
            byte[] buffer = new byte[64 * 1024];
            for (int length; (length = input.read(buffer)) != -1;) {
                count += length;
                if (count > CreatorIntakeStore.MAX_ORIGINAL_BYTES) throw new IOException("Frozen original exceeds byte budget");
                digest.update(buffer, 0, length);
            }
        }
        return HexFormat.of().formatHex(digest.digest());
    }
    private static BasicFileAttributes regular(Path file) throws IOException {
        BasicFileAttributes attributes = Files.readAttributes(file, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        if (!attributes.isRegularFile()) throw new IOException("Expected a regular local input/receipt file");
        return attributes;
    }
    private static Path directory(Path path) throws IOException {
        if (!Files.isDirectory(path, LinkOption.NOFOLLOW_LINKS)) throw new IOException("Expected an existing local directory");
        return path.toRealPath();
    }
    private static Path target(Path path) throws IOException {
        Path requested = path.toAbsolutePath().normalize();
        Path parent = requested.getParent();
        Path name = requested.getFileName();
        if (parent == null || name == null) throw new IOException("Receipt must name a directory under an existing parent");
        return directory(parent).resolve(name);
    }
    private static String name(Path path) throws IOException {
        Path name = path.getFileName();
        if (name == null) throw new IOException("Missing receipt file name");
        return name.toString();
    }
    private static MessageDigest digest() {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch (NoSuchAlgorithmException failure) { throw new IllegalStateException("SHA-256 unavailable", failure); }
    }
    private static String hash(byte[] bytes) { return HexFormat.of().formatHex(digest().digest(bytes)); }
    private static String detail(Exception failure) {
        String text = failure.getClass().getSimpleName() + ": " + failure.getMessage();
        return text.length() > 4096 ? text.substring(0, 4096) : text;
    }
}
