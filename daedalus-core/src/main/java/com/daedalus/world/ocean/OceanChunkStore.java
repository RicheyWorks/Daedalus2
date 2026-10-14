// SPDX-License-Identifier: MIT
package com.daedalus.world.ocean;

import com.daedalus.world.*;
import java.io.IOException;
import java.io.InputStream;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.*;
import java.util.Map;
import java.util.Objects;
import java.util.Properties;

/**
 * Single-writer Ocean sector storage. Existing files always win over generation,
 * even when their saved world contains no blocks. No resident chunk cache.
 * Owners must save edits before eviction. One instance owns a directory until closed.
 */
public final class OceanChunkStore implements AutoCloseable {
    private static final WorldId ID = new WorldId("ocean");
    private static final long MAX_RECORD_BYTES = 65536;
    private final Path directory;
    private final long seed;
    private final FileChannel channel;
    private final FileLock lock;
    private boolean closed;

    public OceanChunkStore(Path directory, long seed) throws IOException {
        this.directory = Objects.requireNonNull(directory, "directory").toAbsolutePath().normalize();
        this.seed = seed;
        Files.createDirectories(this.directory);
        channel = FileChannel.open(this.directory.resolve("store.lock"), StandardOpenOption.CREATE, StandardOpenOption.WRITE);
        FileLock acquired = null;
        try {
            acquired = channel.tryLock();
            if (acquired == null) throw new IOException("Ocean directory already owned");
            metadata();
        } catch (IOException | RuntimeException failure) {
            channel.close();
            if (failure instanceof OverlappingFileLockException) throw new IOException("Ocean directory already owned", failure);
            throw failure;
        }
        lock = acquired;
    }

    /** Missing is generated and saved before return; malformed existing records refuse. */
    public synchronized Chunk loadOrGenerate(ChunkCoordinate at) throws IOException {
        requireOpen();
        Path file = file(at);
        if (Files.exists(file, LinkOption.NOFOLLOW_LINKS)) return read(file, at);
        Chunk generated = OceanTerrain.chunk(seed, at);
        write(file, at, generated);
        return generated;
    }

    /** Persist even an empty chunk, so cleared terrain cannot reappear on restart. */
    public synchronized void save(ChunkCoordinate at, Chunk chunk) throws IOException {
        requireOpen();
        Objects.requireNonNull(chunk, "chunk");
        Path file = file(at);
        // Do not replace an existing corrupt/foreign record during routine saving.
        if (Files.exists(file, LinkOption.NOFOLLOW_LINKS)) read(file, at);
        write(file, at, chunk.copy());
    }

    private Chunk read(Path file, ChunkCoordinate at) throws IOException {
        if (!Files.isRegularFile(file, LinkOption.NOFOLLOW_LINKS) || Files.size(file) > MAX_RECORD_BYTES) {
            throw new IOException("Invalid Ocean chunk record: " + file.getFileName());
        }
        World saved = WorldStore.load(file);
        if (!ID.equals(saved.id()) || saved.chunkCount() > 1
                || saved.chunkKeys().stream().anyMatch(key -> !key.equals(at))) {
            throw new IOException("Ocean chunk identity mismatch: " + file.getFileName());
        }
        Chunk result = saved.chunk(at);
        return result == null ? new Chunk() : result;
    }

    private void write(Path file, ChunkCoordinate at, Chunk chunk) throws IOException {
        // WorldStore's compatibility fallback may overwrite non-atomically. Keep
        // that operation private to staging, then require atomic publication here.
        World image = World.from(new WorldSnapshot(ID, new WorldRevision(0),
                chunk.isEmpty() ? Map.of() : Map.of(at, chunk)));
        Path pending = Files.createTempFile(directory, "ocean-chunk-", ".tmp");
        try {
            WorldStore.save(image, pending);
            force(pending);
            Files.move(pending, file, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } finally {
            Files.deleteIfExists(pending);
        }
    }

    private Path file(ChunkCoordinate at) {
        Objects.requireNonNull(at, "chunk address");
        for (int axis : new int[]{at.x(), at.y(), at.z()}) {
            long first = (long) axis * Chunk.SIZE;
            if (first < Integer.MIN_VALUE || first + Chunk.SIZE - 1 > Integer.MAX_VALUE) {
                throw new IllegalArgumentException("Ocean chunk outside signed block coordinates");
            }
        }
        return directory.resolve(at.x() + "_" + at.y() + "_" + at.z() + ".daew");
    }

    private void metadata() throws IOException {
        Path file = directory.resolve("ocean.properties");
        if (Files.exists(file, LinkOption.NOFOLLOW_LINKS)) {
            if (!Files.isRegularFile(file, LinkOption.NOFOLLOW_LINKS) || Files.size(file) > 4096) {
                throw new IOException("Invalid Ocean metadata");
            }
            Properties p = new Properties();
            try (InputStream input = Files.newInputStream(file)) { p.load(input); }
            if (!Long.toString(seed).equals(p.getProperty("seed"))
                    || !Integer.toString(OceanTerrain.VERSION).equals(p.getProperty("generator"))
                    || !"1".equals(p.getProperty("format"))) {
                throw new IOException("Ocean seed, generator or format mismatch");
            }
            return;
        }
        try (var files = Files.list(directory)) {
            if (files.anyMatch(path -> !path.getFileName().toString().equals("store.lock"))) {
                throw new IOException("Refusing to adopt Ocean data without metadata");
            }
        }
        Path pending = Files.createTempFile(directory, "ocean-metadata-", ".tmp");
        Files.writeString(pending, "format=1\ngenerator=" + OceanTerrain.VERSION + "\nseed=" + seed + "\n");
        try {
            force(pending);
            Files.move(pending, file, StandardCopyOption.ATOMIC_MOVE);
        } finally {
            Files.deleteIfExists(pending);
        }
    }

    private static void force(Path file) throws IOException {
        try (var output = FileChannel.open(file, StandardOpenOption.WRITE)) { output.force(true); }
    }

    private void requireOpen() throws IOException {
        if (closed || !lock.isValid()) throw new IOException("Ocean chunk store is closed");
    }

    @Override public synchronized void close() throws IOException {
        if (closed) return;
        closed = true;
        channel.close(); // Also releases the lifetime writer lock.
    }
}
