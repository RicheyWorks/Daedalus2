// SPDX-License-Identifier: MIT
package com.daedalus.server.service.tactics;

import com.daedalus.world.tactics.AdaptiveTacticsBrain;
import com.daedalus.world.tactics.TacticalMemory;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/** Bounded single-writer DTM sidecars; forced temporary writes and atomic replacement, as for simulation. */
public final class FileTacticalCheckpoints implements AdaptiveTacticsBrain.Checkpoints, AutoCloseable {
    public static final int MAX_FILES = 4096;
    private final Path directory;
    private final FileChannel lease;
    private final FileLock lock;

    public FileTacticalCheckpoints(Path directory) throws IOException {
        this.directory = directory.toAbsolutePath().normalize();
        Files.createDirectories(this.directory);
        lease = FileChannel.open(this.directory.resolve("writer.lock"), StandardOpenOption.CREATE, StandardOpenOption.WRITE);
        try {
            lock = lease.tryLock();
            if (lock == null) throw new IOException("Tactical store already has a writer");
        } catch (IOException | OverlappingFileLockException failure) {
            lease.close();
            throw new IOException("Cannot acquire tactical writer lease", failure);
        }
    }

    private Path file(AdaptiveTacticsBrain.Key key) {
        String identity = key.session() + "\n" + key.squad() + "\n" + key.faction();
        for (String value : new String[] {key.session(), key.squad(), key.faction()}) {
            if (value == null || !value.matches("[A-Za-z0-9_.-]{1,64}")) throw new IllegalArgumentException("Invalid checkpoint key");
        }
        try {
            String name = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(identity.getBytes(StandardCharsets.US_ASCII)));
            return directory.resolve(name + ".dtm");
        } catch (NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
    }

    private void open() throws IOException {
        if (!lease.isOpen() || !lock.isValid()) throw new IOException("Tactical store is closed");
    }

    private static void validate(AdaptiveTacticsBrain.Key key, byte[] bytes) {
        var memory = TacticalMemory.decode(bytes);
        if (!key.session().equals(memory.session()) || !key.faction().equals(memory.faction())) {
            throw new IllegalArgumentException("Checkpoint identity mismatch");
        }
    }

    @Override public synchronized byte[] load(AdaptiveTacticsBrain.Key key) {
        try {
            open();
            Path file = file(key);
            if (!Files.exists(file, LinkOption.NOFOLLOW_LINKS)) return null;
            byte[] bytes;
            try (var in = Files.newInputStream(file, LinkOption.NOFOLLOW_LINKS)) {
                bytes = in.readNBytes(TacticalMemory.MAX_BYTES + 1);
            }
            validate(key, bytes);
            return bytes;
        } catch (IOException failure) { throw new UncheckedIOException(failure); }
    }

    @Override public synchronized void save(AdaptiveTacticsBrain.Key key, byte[] bytes) {
        validate(key, bytes);
        try {
            open();
            Path file = file(key);
            if (!Files.exists(file, LinkOption.NOFOLLOW_LINKS)) {
                try (var files = Files.list(directory)) {
                    if (files.filter(p -> p.toString().endsWith(".dtm")).limit(MAX_FILES).count() >= MAX_FILES) {
                        throw new IOException("Tactical checkpoint capacity reached; archive retired sessions offline");
                    }
                }
            }
            Path temporary = Files.createTempFile(directory, "tactical-", ".pending");
            try {
                try (var out = FileChannel.open(temporary, StandardOpenOption.WRITE)) {
                    ByteBuffer buffer = ByteBuffer.wrap(bytes);
                    while (buffer.hasRemaining()) out.write(buffer);
                    out.force(true);
                }
                Files.move(temporary, file, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            } finally { Files.deleteIfExists(temporary); }
        } catch (IOException failure) { throw new UncheckedIOException(failure); }
    }

    @Override public synchronized void close() throws IOException { lease.close(); }
}
