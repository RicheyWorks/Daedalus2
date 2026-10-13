// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.world.audio.AmbienceState;
import com.daedalus.world.audio.Biome;
import com.daedalus.world.audio.BiomeAmbience;
import com.daedalus.world.audio.CallSynth;
import com.daedalus.world.audio.Genome;
import com.daedalus.world.audio.Species;
import java.security.Principal;
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
    private final String hostSubject;

    public enum MusicCue { FIELD, TOWN, CASTLE, CAVE, BATTLE, BOSS, VICTORY, DEFEAT, INN }

    public record Request(Biome biome, Double hour, Double rain, Double wind, Double waterNear,
                          Species species, String genome, MusicCue musicCue) { }

    public IslandAudioController(@Value("${daedalus.audio.host-subject:}") String hostSubject) {
        this.hostSubject = hostSubject;
    }

    @PostMapping(value = "/design", produces = MediaType.TEXT_PLAIN_VALUE)
    @PerKeyRateLimit("audioDesign")
    public String design(@RequestBody Request request, Principal principal) {
        if (hostSubject.isBlank() || !(principal instanceof Authentication auth) || !auth.isAuthenticated()
                || auth instanceof AnonymousAuthenticationToken || !hostSubject.equals(auth.getName())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Audio host not authorized");
        }
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

    private static boolean range(Double value, double max) {
        return value != null && Double.isFinite(value) && value >= 0 && value <= max;
    }
}
