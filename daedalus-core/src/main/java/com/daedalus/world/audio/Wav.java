package com.daedalus.world.audio;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;

/** Minimal PCM16 mono WAV writer (JDK only, no javax.sound) so core stays portable. */
public final class Wav {
    private Wav() {
    }

    /** Encodes samples as a RIFF/WAVE byte array. */
    public static byte[] encode(short[] samples, int sampleRate) {
        int data = samples.length * 2;
        ByteBuffer b = ByteBuffer.allocate(44 + data).order(ByteOrder.LITTLE_ENDIAN);
        b.put("RIFF".getBytes(StandardCharsets.US_ASCII)).putInt(36 + data);
        b.put("WAVE".getBytes(StandardCharsets.US_ASCII));
        b.put("fmt ".getBytes(StandardCharsets.US_ASCII)).putInt(16).putShort((short) 1).putShort((short) 1);
        b.putInt(sampleRate).putInt(sampleRate * 2).putShort((short) 2).putShort((short) 16);
        b.put("data".getBytes(StandardCharsets.US_ASCII)).putInt(data);
        for (short s : samples) {
            b.putShort(s);
        }
        return b.array();
    }
}
