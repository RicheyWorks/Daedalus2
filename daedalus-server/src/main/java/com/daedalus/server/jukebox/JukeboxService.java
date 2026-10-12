// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import com.daedalus.server.config.JukeboxProperties;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/** The jukebox's server side: holder lookups, token HTML, guest seed songs and the rd-studio seam. */
@Service
public class JukeboxService {

    /** A seed-song file name: lowercase slug + extension. Nothing else is ever served from the directory. */
    static final Pattern SEED_FILE = Pattern.compile("[a-z0-9][a-z0-9-]{0,80}\\.(mp3|webp)");

    private final JukeboxProperties props;
    private final RdSongReader reader;
    private final StudioArranger arranger;

    @Autowired
    public JukeboxService(JukeboxProperties props) {
        this(props, props.hasContract() ? new HttpJsonRpc(props.rpcUrl()) : null, StudioArranger.STUB);
    }

    public JukeboxService(JukeboxProperties props, JsonRpc rpc, StudioArranger arranger) {
        this.props = props;
        this.reader = rpc == null ? null : new RdSongReader(rpc, props.contract(), props.scanBatch(), props.maxScan(),
                props.cacheSeconds() * 1000L, System::currentTimeMillis);
        this.arranger = arranger;
    }

    public JukeboxProperties props() { return props; }

    public boolean onChain() { return props.enabled() && reader != null; }

    public List<Long> tokensOf(String address) {
        return onChain() ? reader.tokensOf(address) : List.of();
    }

    public Optional<byte[]> tokenHtml(long id) {
        return onChain() ? Optional.ofNullable(reader.tokenHtml(id)) : Optional.empty();
    }

    public record Seed(String name, String title, String audio, String cover) {}

    public List<Seed> seeds() {
        Path dir = seedDir();
        if (dir == null) return List.of();
        List<Seed> out = new ArrayList<>();
        try (Stream<Path> files = Files.list(dir)) {
            for (Path p : files.sorted().toList()) {
                String f = p.getFileName().toString();
                if (!f.endsWith(".mp3") || !SEED_FILE.matcher(f).matches()) continue;
                String name = f.substring(0, f.length() - 4);
                boolean cover = Files.isRegularFile(dir.resolve(name + ".webp"));
                out.add(new Seed(name, title(name), "/api/v1/jukebox/seeds/" + f,
                        cover ? "/api/v1/jukebox/seeds/" + name + ".webp" : null));
            }
        } catch (IOException e) {
            return List.of();
        }
        return out;
    }

    /** The seed file, only if its name is a plain slug inside the configured directory. */
    public Optional<Path> seedFile(String file) {
        Path dir = seedDir();
        if (dir == null || file == null || !SEED_FILE.matcher(file).matches()) return Optional.empty();
        Path p = dir.resolve(file).normalize();
        return p.startsWith(dir) && Files.isRegularFile(p) ? Optional.of(p) : Optional.empty();
    }

    public StudioArranger.Arrangement arrange(String source, String genre, boolean studio) {
        String g = genre == null ? "original" : genre.toLowerCase();
        if (!StudioArranger.GENRES.contains(g)) throw new IllegalArgumentException("unknown genre: " + genre);
        if (source == null || !source.matches("seed:[a-z0-9-]{1,80}|token:\\d{1,9}"))
            throw new IllegalArgumentException("source must be seed:<name> or token:<id>");
        return arranger.arrange(source, g, studio);
    }

    static String title(String slug) {
        StringBuilder b = new StringBuilder();
        for (String w : slug.split("-")) {
            if (w.isEmpty()) continue;
            if (!b.isEmpty()) b.append(' ');
            b.append(Character.toUpperCase(w.charAt(0))).append(w.substring(1));
        }
        return b.toString();
    }

    private Path seedDir() {
        if (!props.enabled() || props.seedSongsDir().isEmpty()) return null;
        Path dir = Path.of(props.seedSongsDir()).toAbsolutePath().normalize();
        return Files.isDirectory(dir) ? dir : null;
    }
}
