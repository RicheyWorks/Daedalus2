// SPDX-License-Identifier: MIT
package com.daedalus.world.persistence;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.NoSuchFileException;
import java.nio.file.attribute.BasicFileAttributes;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.Optional;

/** Local host record storage for versioned native snapshots. Follows OceanChunkStore's
 * lifetime directory lock and same-directory atomic replacement pattern.
 * Not a distributed database, permission check, inventory validator or a multi-record transaction.
 * Store coupled run/household/ecosystem/ledger state as one validated payload.
 */
public final class RealmRecordStore implements AutoCloseable {
    public static final int MAX_PAYLOAD_BYTES = 16 * 1024 * 1024;
    private static final int MAX_FILE_BYTES = MAX_PAYLOAD_BYTES + 4096;
    private static final int MAGIC = 0x44524543; // DREC
    private final Path directory;
    private final FileChannel ownership;
    private final FileLock lock;
    private boolean closed;

    public record Stored(String realm, String key, long revision, byte[] payload, String sha256) {
        public Stored { payload = payload.clone(); }
        @Override public byte[] payload() { return payload.clone(); }
    }
    public enum WriteResult { UPDATED, REPLAY, CONFLICT }
    public record Write(WriteResult result, Stored record) {}

    public RealmRecordStore(Path directory) throws IOException {
        Files.createDirectories(directory);
        this.directory = directory.toRealPath();
        Path lockFile = this.directory.resolve("records.lock");
        if (Files.isSymbolicLink(lockFile)) throw new IOException("Record lock is a link");
        ownership = FileChannel.open(lockFile, StandardOpenOption.CREATE, StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS);
        FileLock acquired;
        try {
            acquired = ownership.tryLock();
            if (acquired == null) throw new IOException("Record directory already owned");
        } catch (IOException | OverlappingFileLockException failure) {
            ownership.close();
            throw new IOException("Cannot own record directory", failure);
        }
        lock = acquired;
    }

    private void requireOpen() throws IOException {
        if (closed || !lock.isValid()) throw new IOException("Record store closed");
    }
    private static void identity(String realm, String key) {
        if (realm == null || !realm.matches("[A-Z][A-Z0-9-]{0,39}")
                || key == null || !key.matches("[A-Za-z0-9][A-Za-z0-9._:-]{0,99}"))
            throw new IllegalArgumentException("Invalid realm record identity");
    }
    private static byte[] digest(byte[] bytes) {
        try { return MessageDigest.getInstance("SHA-256").digest(bytes); }
        catch (NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
    }
    private static byte[] digestRecord(String realm, String key, long revision, byte[] payload) {
        try {
            var digest = MessageDigest.getInstance("SHA-256");
            digest.update(ByteBuffer.allocate(16).putInt(MAGIC).putInt(1).putLong(revision).array());
            digest.update(realm.getBytes(java.nio.charset.StandardCharsets.UTF_8));digest.update((byte) 0);
            digest.update(key.getBytes(java.nio.charset.StandardCharsets.UTF_8));digest.update((byte) 0);
            digest.update(ByteBuffer.allocate(4).putInt(payload.length).array());digest.update(payload);
            return digest.digest();
        } catch (NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
    }
    private Path file(String realm, String key) {
        identity(realm, key);
        byte[] address = (realm + "\n" + key).getBytes(java.nio.charset.StandardCharsets.UTF_8);
        return directory.resolve(HexFormat.of().formatHex(digest(address)) + ".drec");
    }

    public synchronized Optional<Stored> read(String realm, String key) throws IOException {
        requireOpen();Path file = file(realm, key);
        BasicFileAttributes attrs;
        try { attrs = Files.readAttributes(file, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS); }
        catch (NoSuchFileException absent) { return Optional.empty(); }
        if (!attrs.isRegularFile()) throw new IOException("Record is not a regular file");
        byte[] bytes;
        try (var in = Files.newInputStream(file, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS)) { bytes = in.readNBytes(MAX_FILE_BYTES + 1); }
        if (bytes.length > MAX_FILE_BYTES) throw new IOException("Record exceeds size limit");
        try (var in = new DataInputStream(new ByteArrayInputStream(bytes))) {
            if (in.readInt() != MAGIC || in.readInt() != 1) throw new IOException("Unknown record format");
            String storedRealm = in.readUTF(), storedKey = in.readUTF();long revision = in.readLong();
            int length = in.readInt();byte[] expectedHash = new byte[32];in.readFully(expectedHash);
            if (!realm.equals(storedRealm) || !key.equals(storedKey) || revision < 1
                    || length < 1 || length > MAX_PAYLOAD_BYTES) throw new IOException("Invalid record header");
            byte[] payload = new byte[length];in.readFully(payload);
            if (in.read() != -1 || !MessageDigest.isEqual(expectedHash, digestRecord(realm, key, revision, payload)))
                throw new IOException("Record checksum or trailing bytes mismatch");
            return Optional.of(new Stored(realm, key, revision, payload, HexFormat.of().formatHex(digest(payload))));
        }
    }

    /** Expected zero creates a new record; updates require exactly the stored revision.
     * A retry of the same immediate revision and bytes is observable as REPLAY.
     */
    public synchronized Write compareAndSet(String realm, String key, long expectedRevision, byte[] payload) throws IOException {
        requireOpen();identity(realm, key);
        if (expectedRevision < 0 || expectedRevision == Long.MAX_VALUE || payload == null
                || payload.length < 1 || payload.length > MAX_PAYLOAD_BYTES) throw new IllegalArgumentException("Invalid record update");
        byte[] candidate = payload.clone();Optional<Stored> previous = read(realm, key);
        long current = previous.map(Stored::revision).orElse(0L);
        if (current != expectedRevision) {
            if (current == expectedRevision + 1 && previous.isPresent() && Arrays.equals(candidate, previous.get().payload()))
                return new Write(WriteResult.REPLAY, previous.get());
            return new Write(WriteResult.CONFLICT, previous.orElse(null));
        }
        byte[] hash = digestRecord(realm, key, current + 1, candidate);ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (var out = new DataOutputStream(bytes)) {
            out.writeInt(MAGIC);out.writeInt(1);out.writeUTF(realm);out.writeUTF(key);
            out.writeLong(current + 1);out.writeInt(candidate.length);out.write(hash);out.write(candidate);
        }
        Path target = file(realm, key), pending = Files.createTempFile(directory, "record-", ".tmp");
        try {
            try (FileChannel out = FileChannel.open(pending, StandardOpenOption.WRITE)) {
                ByteBuffer buffer = ByteBuffer.wrap(bytes.toByteArray());while (buffer.hasRemaining()) out.write(buffer);out.force(true);
            }
            // No non-atomic fallback: preserve the existing record if this filesystem cannot replace atomically.
            Files.move(pending, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } finally { Files.deleteIfExists(pending); }
        return new Write(WriteResult.UPDATED, new Stored(realm, key, current + 1, candidate, HexFormat.of().formatHex(digest(candidate))));
    }

    @Override public synchronized void close() throws IOException {
        if (closed) return;closed = true;ownership.close();
    }
}
