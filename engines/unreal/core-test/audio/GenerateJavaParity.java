// SPDX-License-Identifier: MIT
// Test fixture generator. Compile with the repository's existing world/audio Java sources.
// It invokes Java CallSynth directly; it is not a replacement design API or a renderer port.
import com.daedalus.world.audio.CallSpec;
import com.daedalus.world.audio.CallSynth;
import com.daedalus.world.audio.Genome;
import com.daedalus.world.audio.Rng;
import com.daedalus.world.audio.Species;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

public final class GenerateJavaParity {
    private static final int SAMPLE_RATE = 22050;

    private static long checksum(byte[] bytes) {
        long hash = 0xcbf29ce484222325L;
        for (byte value : bytes) {
            hash ^= value & 0xff;
            hash *= 0x100000001b3L;
        }
        return hash;
    }

    private static void fixture(Path output, String name, Species species, String hex) throws Exception {
        Genome genome = Genome.ofHex(hex);
        CallSpec call = CallSynth.design(species, genome);
        short[] samples = CallSynth.render(call, SAMPLE_RATE, genome.seed());
        ByteBuffer pcm = ByteBuffer.allocate(samples.length * 2).order(ByteOrder.LITTLE_ENDIAN);
        for (short sample : samples) pcm.putShort(sample);
        Files.write(output.resolve(name + ".pcm"), pcm.array());
        StringBuilder text = new StringBuilder("JAVA_PCM 1\n");
        text.append("genome ").append(hex).append('\n');
        text.append(String.format(Locale.ROOT, "seed %016x\n", genome.seed()));
        Rng random = new Rng(genome.seed());
        text.append("rng");
        for (int i = 0; i < 8; ++i) text.append(String.format(Locale.ROOT, " %016x", random.nextLong()));
        text.append('\n').append(call.toLine()).append('\n');
        text.append("sample_rate ").append(SAMPLE_RATE).append('\n');
        text.append("samples ").append(samples.length).append('\n');
        text.append(String.format(Locale.ROOT, "checksum %016x\n", checksum(pcm.array())));
        int pulseN = call.pulseMs() * SAMPLE_RATE / 1000;
        int[] selected = {0, 1, 17, pulseN / 2, pulseN - 1, samples.length / 2, samples.length - 1};
        text.append("selected");
        for (int index : selected) text.append(' ').append(index).append(':').append(samples[index]);
        text.append("\nend\n");
        Files.writeString(output.resolve(name + ".txt"), text.toString(), StandardCharsets.US_ASCII);
        System.out.println(name + ": " + samples.length + " Java samples, seed=" + Long.toUnsignedString(genome.seed(), 16));
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("output fixture directory required");
        Path output = Path.of(args[0]);
        Files.createDirectories(output);
        fixture(output, "canid-zero", Species.CANID, "00");
        fixture(output, "goat-varied", Species.GOAT, "3fa29c1e7b44d0815e6a");
        fixture(output, "songbird-max", Species.SONGBIRD, "ff");
        fixture(output, "bovine-max", Species.BOVINE, "ff");
    }
}
