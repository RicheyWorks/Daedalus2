// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.world.audio.AmbienceState;
import com.daedalus.world.audio.Biome;
import com.daedalus.world.audio.BiomeAmbience;
import com.daedalus.world.audio.CallSynth;
import com.daedalus.world.audio.Genome;
import com.daedalus.world.audio.Herb;
import com.daedalus.world.audio.HerbChord;
import com.daedalus.world.audio.Species;
import java.security.Principal;
import java.util.List;
import java.util.Locale;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/** Engine-neutral audio parameters; playback and asset resolution remain native. */
@RestController
@RequestMapping("/api/v1/audio")
public class IslandAudioController {
    private static final int MAX_HERBS = 8;
    private final String hostSubject;

    public enum MusicCue { FIELD, TOWN, CASTLE, CAVE, BATTLE, BOSS, VICTORY, DEFEAT, INN }

    public record Request(Biome biome, Double hour, Double rain, Double wind, Double waterNear,
                          Species species, String genome, MusicCue musicCue) { }

    /** One herb in an HRB 1 request: ASCII id (lower-case letters, digits, underscore, hyphen) and potency 0..1. */
    public record HerbIn(String id, Double potency) { }

    public record HerbRequest(List<HerbIn> herbs) { }

    public IslandAudioController(@Value("${daedalus.audio.host-subject:}") String hostSubject) {
        this.hostSubject = hostSubject;
    }

    @PostMapping(value = "/design", produces = MediaType.TEXT_PLAIN_VALUE)
    @PerKeyRateLimit("audioDesign")
    public String design(@RequestBody Request request, Principal principal) {
        authorizeHost(principal);
        if (request == null || request.biome() == null || request.species() == null || request.musicCue() == null
                || !range(request.hour(), 24) || !range(request.rain(), 1) || !range(request.wind(), 1)
                || !range(request.waterNear(), 1) || request.genome() == null
                || !request.genome().matches("[0-9a-fA-F]{2,128}") || request.genome().length() % 2 != 0) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid audio design input");
        }
        var state = new AmbienceState(request.biome(), request.hour(), request.rain(), request.wind(), request.waterNear());
        var wire = new StringBuilder("AUD 1\n");
        wire.append("jukebox ").append(request.musicCue().name()).append('\n');
        for (var layer : BiomeAmbience.mix(state)) {
            wire.append(String.format(Locale.ROOT, "layer %s %.3f %.3f %.3f",
                    layer.id(), layer.gain(), layer.lowpassHz(), layer.density())).append('\n');
        }
        wire.append(CallSynth.design(request.species(), Genome.ofHex(request.genome())).toLine()).append("\nend\n");
        return wire.toString();
    }

    /**
     * HRB 1: the herb-chord record that AUD 1 does not carry. Reuses {@link HerbChord#sound}; additive, AUD 1 is unchanged.
     * Wire: header, one chord line (root pitch class 0-11, quality, effect, strength), one freq line per note, end.
     */
    @PostMapping(value = "/herb-chord", produces = MediaType.TEXT_PLAIN_VALUE)
    @PerKeyRateLimit("audioDesign")
    public String herbChord(@RequestBody HerbRequest request, Principal principal) {
        authorizeHost(principal);
        if (request == null || request.herbs() == null || request.herbs().isEmpty() || request.herbs().size() > MAX_HERBS) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid herb chord input");
        }
        var herbs = new java.util.ArrayList<Herb>();
        for (var in : request.herbs()) {
            if (in == null || in.id() == null || !in.id().matches("[a-z0-9_-]{1,32}") || !range(in.potency(), 1)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid herb chord input");
            }
            herbs.add(new Herb(in.id(), in.potency()));
        }
        var chord = HerbChord.sound(herbs);
        var wire = new StringBuilder("HRB 1\n");
        wire.append(String.format(Locale.ROOT, "chord %d %s %s %.3f", chord.root(), chord.quality(),
                chord.effect().name(), chord.strength())).append('\n');
        for (double hz : chord.frequencies()) {
            wire.append(String.format(Locale.ROOT, "freq %.3f", hz)).append('\n');
        }
        return wire.append("end\n").toString();
    }

    private void authorizeHost(Principal principal) {
        if (hostSubject.isBlank() || !(principal instanceof Authentication auth) || !auth.isAuthenticated()
                || auth instanceof AnonymousAuthenticationToken || !hostSubject.equals(auth.getName())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Audio host not authorized");
        }
    }
    private static boolean range(Double value, double max) {
        return value != null && Double.isFinite(value) && value >= 0 && value <= max;
    }
}
