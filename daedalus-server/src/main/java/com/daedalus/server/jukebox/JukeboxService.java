// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import com.daedalus.server.config.JukeboxProperties;
import com.daedalus.server.jukebox.radio.RadioArea;
import com.daedalus.server.jukebox.radio.RadioBrowserDirectory;
import com.daedalus.server.jukebox.radio.RadioRelay;
import com.daedalus.server.jukebox.radio.RelayGuard;
import com.daedalus.server.jukebox.radio.RadioService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * The jukebox's server side: holder look-ups and token HTML/hash (read-only RDSong), guest seed songs,
 * the radio, and the rd-studio seam (arrangements, audio, coats).
 */
@Service
public class JukeboxService {

    /** A seed-song file name: lowercase slug + extension. Nothing else is ever served from the directory. */
    static final Pattern SEED_FILE = Pattern.compile("[a-z0-9][a-z0-9-]{0,80}\\.(mp3|webp)");

    private final JukeboxProperties props;
    private final RdSongReader reader;
    private final StudioArranger arranger;
    private final RadioService radio;
    private final RadioRelay relay;

    @Autowired
    public JukeboxService(JukeboxProperties props) {
        this(props, props.hasContract() ? new HttpJsonRpc(props.rpcUrl()) : null,
                props.studioUrl().isEmpty() ? StudioArranger.STUB : new HttpStudioArranger(props.studioUrl(), System::currentTimeMillis),
                new RadioService(new RadioBrowserDirectory(List.of()), System::currentTimeMillis));
    }

    public JukeboxService(JukeboxProperties props, JsonRpc rpc, StudioArranger arranger, RadioService radio) {
        this(props, rpc, arranger, radio, new RadioRelay(new RelayGuard(java.net.InetAddress::getAllByName,
                System.getenv().getOrDefault("DAEDALUS_JUKEBOX_RELAY_FAKE_IP_CIDRS", "")), RadioRelay.Limits.DEFAULT));
    }

    public JukeboxService(JukeboxProperties props, JsonRpc rpc, StudioArranger arranger, RadioService radio, RadioRelay relay) {
        this.props = props;
        this.reader = rpc == null ? null : new RdSongReader(rpc, props.contract(), props.scanBatch(), props.maxScan(),
                props.cacheSeconds() * 1000L, System::currentTimeMillis);
        if (reader != null && props.enabled() && props.indexer()) {
            Path file = props.indexFile().isEmpty()
                    ? Path.of(System.getProperty("java.io.tmpdir"), "daedalus-jukebox-index-" + props.chainId() + "-" + props.contract() + ".json")
                    : Path.of(props.indexFile());
            reader.withIndexer(new TransferIndexer(rpc, props.contract(), props.chainId(), props.deployBlock(), props.confirmations(),
                    props.logChunk(), file, 5_000, System::currentTimeMillis), props.scanFallbackMax());
        }
        this.arranger = arranger;
        this.radio = radio;
        this.relay = relay;
    }

    public RadioRelay relay() { return relay; }

    /** Studio health for the UI (state UP / DEGRADED / DOWN / OFF, breaker, engine, last latency and error). */
    public Map<String, Object> studioHealth() {
        return props.enabled() ? arranger.health() : Map.of("state", "OFF");
    }

    /** Where holder look-ups come from ("index" or "scan") and how far the index has got. */
    public Map<String, Object> holders() {
        Map<String, Object> m = new LinkedHashMap<>();
        if (!onChain()) { m.put("source", "off"); return m; }
        m.put("source", reader.holderSource());
        TransferIndexer ix = reader.indexer();
        if (ix != null) {
            m.put("indexedBlock", ix.indexedBlock());
            m.put("indexedTokens", ix.size());
            if (!ix.lastError().isEmpty()) m.put("indexError", ix.lastError());
        }
        return m;
    }

    public JukeboxProperties props() { return props; }

    public boolean onChain() { return props.enabled() && reader != null; }

    public boolean studio() { return props.enabled() && arranger instanceof HttpStudioArranger; }

    public List<Long> tokensOf(String address) {
        return onChain() ? reader.tokensOf(address) : List.of();
    }

    public Optional<byte[]> tokenHtml(long id) {
        return onChain() ? Optional.ofNullable(reader.tokenHtml(id)) : Optional.empty();
    }

    public Optional<String> tokenHash(long id) {
        return onChain() ? Optional.ofNullable(reader.tokenHash(id)) : Optional.empty();
    }

    /** A guest song: a file seed ({@code audio} set) or an rd-studio engine seed ({@code studio}, played via arrangement). */
    public record Seed(String name, String title, String audio, String cover, boolean studio) {}

    public List<Seed> seeds() {
        if (!props.enabled()) return List.of();
        List<Seed> out = new ArrayList<>();
        for (String s : arranger.seeds()) out.add(new Seed(s, "Engine seed " + s, null, null, true));
        Path dir = seedDir();
        if (dir == null) return out;
        try (Stream<Path> files = Files.list(dir)) {
            for (Path p : files.sorted().toList()) {
                String f = p.getFileName().toString();
                if (!f.endsWith(".mp3") || !SEED_FILE.matcher(f).matches()) continue;
                String name = f.substring(0, f.length() - 4);
                boolean cover = Files.isRegularFile(dir.resolve(name + ".webp"));
                out.add(new Seed(name, title(name), "/api/v1/jukebox/seeds/" + f,
                        cover ? "/api/v1/jukebox/seeds/" + name + ".webp" : null, false));
            }
        } catch (IOException e) {
            return out;    // an unreadable directory is "no file seeds", not an error page
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
        return arrange(source, genre, studio, StudioArranger.Render.DEFAULT);
    }

    public StudioArranger.Arrangement arrange(String source, String genre, boolean studio, StudioArranger.Render render) {
        String g = genre == null ? "original" : genre.toLowerCase();
        if (!StudioArranger.GENRES.contains(g)) throw new IllegalArgumentException("unknown genre: " + genre);
        if (source == null || !source.matches("seed:[a-z0-9][a-z0-9_-]{0,80}|token:\\d{1,9}"))
            throw new IllegalArgumentException("source must be seed:<name> or token:<id>");
        return arranger.arrange(source, g, studio, render);
    }

    public Optional<HttpStudioArranger.Upstream> studioAudio(String key, String ifNoneMatch) {
        return studio() ? ((HttpStudioArranger) arranger).audio(key, ifNoneMatch) : Optional.empty();
    }

    public Optional<String> studioVoices() {
        return studio() ? ((HttpStudioArranger) arranger).voices() : Optional.empty();
    }

    /** IllegalArgumentException on bad params (even with no studio, so callers learn the schema). */
    public Optional<Map<String, Object>> studioNote(Map<String, String> q) {
        if (!studio()) { HttpStudioArranger.validateNote(q); return Optional.empty(); }
        return ((HttpStudioArranger) arranger).note(q);
    }

    public Optional<byte[]> coatPng(String hash, int size) {
        return studio() ? ((HttpStudioArranger) arranger).coatPng(hash, size) : Optional.empty();
    }

    public Optional<String> coat(String hash) {
        return studio() ? ((HttpStudioArranger) arranger).coat(hash) : Optional.empty();
    }

    public RadioService.Lineup radio(RadioArea area) {
        if (!props.enabled()) throw new IllegalStateException("the jukebox is off");
        return radio.lineup(area);
    }

    public Optional<String> radioStream(String id) {
        return props.enabled() ? radio.streamOf(id) : Optional.empty();
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
