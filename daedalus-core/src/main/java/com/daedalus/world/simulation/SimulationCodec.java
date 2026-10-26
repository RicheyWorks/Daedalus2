// SPDX-License-Identifier: MIT
package com.daedalus.world.simulation;

import com.daedalus.world.WorldId;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.TreeMap;

/** Versioned deterministic sidecar bytes; no database, JSON framework, or renderer dependency. */
public final class SimulationCodec {
    public static final int MAX_BYTES = 1_048_576;
    private static final int MAGIC = 0x444c5731;
    private SimulationCodec() { }

    public record Stored(long epochMillis, long tickMillis, String steward, SimulationTimeline timeline) {
        public Stored {
            if (epochMillis < 0 || tickMillis < 1 || tickMillis > 86_400_000 || steward == null
                    || !steward.matches("[A-Za-z0-9_.:@-]{1,128}") || timeline == null) {
                throw new IllegalArgumentException("Invalid simulation metadata");
            }
        }
    }
    public static String hash(LivingWorld.State state) {
        try {
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            try (DataOutputStream out = new DataOutputStream(bytes)) { writeState(out, state); }
            return HexFormat.of().formatHex(digest(bytes.toByteArray()));
        } catch (IOException impossible) { throw new UncheckedIOException(impossible); }
    }
    public static byte[] encode(Stored stored) {
        try {
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            try (DataOutputStream out = new DataOutputStream(bytes)) {
                out.writeInt(MAGIC);
                out.writeInt(LivingWorld.VERSION);
                out.writeLong(stored.epochMillis());
                out.writeLong(stored.tickMillis());
                out.writeUTF(stored.steward());
                writeState(out, stored.timeline().checkpoint());
                out.writeInt(stored.timeline().entries().size());
                for (SimulationTimeline.Entry entry : stored.timeline().entries()) {
                    out.writeUTF(entry.input().kind().name());
                    out.writeLong(entry.input().value());
                    out.writeUTF(entry.input().requestId());
                    out.writeUTF(entry.input().actor());
                    out.writeUTF(entry.stateHash());
                }
            }
            byte[] body = bytes.toByteArray();
            bytes.write(digest(body));
            if (bytes.size() > MAX_BYTES) throw new IllegalArgumentException("Snapshot too large");
            return bytes.toByteArray();
        } catch (IOException impossible) { throw new UncheckedIOException(impossible); }
    }
    public static Stored decode(byte[] bytes) throws IOException {
        if (bytes.length < 40 || bytes.length > MAX_BYTES) throw new IOException("Invalid snapshot size");
        byte[] body = Arrays.copyOf(bytes, bytes.length - 32);
        if (!MessageDigest.isEqual(digest(body), Arrays.copyOfRange(bytes, bytes.length - 32, bytes.length))) {
            throw new IOException("Snapshot checksum mismatch");
        }
        try (DataInputStream in = new DataInputStream(new ByteArrayInputStream(body))) {
            if (in.readInt() != MAGIC || in.readInt() != LivingWorld.VERSION) throw new IOException("Unsupported simulation format");
            long epoch = in.readLong();
            long tickMillis = in.readLong();
            String steward = in.readUTF();
            LivingWorld.State base = readState(in);
            int count = count(in, SimulationTimeline.MAX_TAIL);
            var entries = new ArrayList<SimulationTimeline.Entry>();
            for (int i = 0; i < count; i++) {
                var input = new LivingWorld.Input(LivingWorld.Kind.valueOf(in.readUTF()), in.readLong(), in.readUTF(), in.readUTF());
                entries.add(new SimulationTimeline.Entry(input, in.readUTF()));
            }
            if (in.available() != 0) throw new IOException("Trailing simulation data");
            return new Stored(epoch, tickMillis, steward, SimulationTimeline.recover(base, entries));
        } catch (IllegalArgumentException | ArithmeticException e) {
            throw new IOException("Invalid simulation state or replay", e);
        }
    }
    private static void writeState(DataOutputStream out, LivingWorld.State s) throws IOException {
        out.writeInt(s.version()); out.writeUTF(s.worldId().value()); out.writeLong(s.seed());
        out.writeLong(s.tick()); out.writeLong(s.revision()); out.writeInt(s.water()); out.writeInt(s.keeperWater());
        out.writeBoolean(s.questCompleted()); out.writeUTF(s.rememberedActor()); out.writeBoolean(s.active());
        out.writeLong(s.eventSequence()); out.writeInt(s.receipts().size());
        for (var entry : s.receipts().entrySet()) {
            out.writeUTF(entry.getKey());
            var r = entry.getValue();
            out.writeUTF(r.actor()); out.writeInt(r.water()); out.writeLong(r.tick());
            out.writeLong(r.revision()); out.writeBoolean(r.questCompleted());
        }
        out.writeInt(s.events().size());
        for (var event : s.events()) {
            out.writeLong(event.sequence()); out.writeLong(event.tick());
            out.writeUTF(event.kind().name()); out.writeUTF(event.detail());
        }
    }
    private static LivingWorld.State readState(DataInputStream in) throws IOException {
        int version = in.readInt(); WorldId id = new WorldId(in.readUTF()); long seed = in.readLong();
        long tick = in.readLong(); long revision = in.readLong(); int water = in.readInt(); int keeper = in.readInt();
        boolean quest = in.readBoolean(); String memory = in.readUTF(); boolean active = in.readBoolean();
        long sequence = in.readLong(); int receiptCount = count(in, LivingWorld.MAX_RECEIPTS);
        var receipts = new TreeMap<String, LivingWorld.Receipt>();
        for (int i = 0; i < receiptCount; i++) {
            String key = in.readUTF();
            var receipt = new LivingWorld.Receipt(in.readUTF(), in.readInt(), in.readLong(), in.readLong(), in.readBoolean());
            if (receipts.put(key, receipt) != null) throw new IOException("Duplicate receipt id");
        }
        int eventCount = count(in, LivingWorld.MAX_EVENTS);
        var events = new ArrayList<LivingWorld.Event>();
        for (int i = 0; i < eventCount; i++) {
            events.add(new LivingWorld.Event(in.readLong(), in.readLong(), LivingWorld.EventKind.valueOf(in.readUTF()), in.readUTF()));
        }
        return new LivingWorld.State(version, id, seed, tick, revision, water, keeper, quest, memory, active, sequence, receipts, events);
    }
    private static int count(DataInputStream in, int maximum) throws IOException {
        int count = in.readInt();
        if (count < 0 || count > maximum) throw new IOException("Invalid collection size");
        return count;
    }
    private static byte[] digest(byte[] bytes) {
        try { return MessageDigest.getInstance("SHA-256").digest(bytes); }
        catch (NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
    }
}
