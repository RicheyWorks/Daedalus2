// SPDX-License-Identifier: MIT
package com.daedalus.server.service.simulation;

import com.daedalus.world.simulation.SimulationCodec;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;

/** Exclusive writer, forced temp file, then atomic replace. Unsupported atomic moves fail closed. */
public final class FileSimulationRepository implements SimulationRepository {
    private final Path file;
    private final Path directory;
    private final String fileName;
    private final FileChannel lockChannel;
    private final FileLock lock;
    private boolean closed;

    public FileSimulationRepository(Path file) throws IOException {
        this.file = file.toAbsolutePath().normalize();
        Path parent = this.file.getParent();
        Path name = this.file.getFileName();
        if (parent == null || name == null) throw new IOException("Simulation sidecar path must name a file");
        directory = parent;
        fileName = name.toString();
        Files.createDirectories(directory);
        lockChannel = FileChannel.open(directory.resolve(fileName + ".lock"),
                StandardOpenOption.CREATE, StandardOpenOption.WRITE);
        try {
            lock = lockChannel.tryLock();
            if (lock == null) throw new IOException("Simulation already has a writer");
        } catch (IOException | OverlappingFileLockException e) {
            lockChannel.close();
            throw new IOException("Cannot acquire simulation writer lease", e);
        }
    }
    @Override public synchronized SimulationCodec.Stored load() throws IOException {
        requireOpen();
        if (!Files.exists(file)) return null;
        if (Files.size(file) > SimulationCodec.MAX_BYTES) throw new IOException("Snapshot exceeds size limit");
        return SimulationCodec.decode(Files.readAllBytes(file));
    }
    @Override public synchronized void save(SimulationCodec.Stored state) throws IOException {
        requireOpen();
        byte[] bytes = SimulationCodec.encode(state);
        Path temporary = Files.createTempFile(directory, fileName + ".", ".pending");
        try {
            try (FileChannel out = FileChannel.open(temporary, StandardOpenOption.WRITE)) {
                ByteBuffer buffer = ByteBuffer.wrap(bytes);
                while (buffer.hasRemaining()) out.write(buffer);
                out.force(true);
            }
            Files.move(temporary, file, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } finally { Files.deleteIfExists(temporary); }
    }
    private void requireOpen() throws IOException {
        if (closed || !lock.isValid()) throw new IOException("Simulation writer is closed");
    }
    @Override public synchronized void close() throws IOException {
        closed = true;
        lockChannel.close();
    }
}
