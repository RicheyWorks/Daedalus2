// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.MelodyBrew;
import com.daedalus.world.brew.PitchTable;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.Principal;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;
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

/**
 * Server-authoritative Youtube Master Island melody brew (contest G25 bench, contract brew-melody-v1) for a trusted
 * engine host. A pure calculation over {@link MelodyBrew} and the packaged found tunes: it never consumes herbs,
 * grants items or remembers played records; the caller lists the records the player has played.
 */
@RestController
@RequestMapping("/api/v1/brew")
public class MelodyBrewController {
    public static final int MAX_RECORDS = 32;

    private final List<FoundTune> tunes;
    private final Set<String> records;
    private final String hostSubject;

    public record Request(List<String> herbs, List<Integer> stages, List<String> records) {
        public Request {
            herbs = herbs == null ? null : java.util.Collections.unmodifiableList(new ArrayList<>(herbs));
            stages = stages == null ? null : java.util.Collections.unmodifiableList(new ArrayList<>(stages));
            records = records == null ? null : java.util.Collections.unmodifiableList(new ArrayList<>(records));
        }
    }

    public record Response(String item, boolean cadence, String contour, String quality, int tier, String effect,
            int magnitude, int durationS, List<Integer> notes, String foundTune, String foundTuneBonus,
            String recordId, String why) {
        public Response {
            notes = List.copyOf(notes);
        }
    }

    public MelodyBrewController(@Value("${daedalus.brew.host-subject:}") String hostSubject) throws IOException {
        this.hostSubject = hostSubject;
        try (var input = MelodyBrewController.class.getResourceAsStream("/brew/found_tunes.csv")) {
            if (input == null) throw new IOException("Packaged found tunes missing");
            tunes = List.copyOf(FoundTune.parseCsv(new String(input.readAllBytes(), StandardCharsets.UTF_8)));
        }
        records = tunes.stream().map(FoundTune::learnedFrom).collect(Collectors.toUnmodifiableSet());
    }

    @PostMapping(value = "/melody", consumes = MediaType.APPLICATION_JSON_VALUE,
            produces = MediaType.APPLICATION_JSON_VALUE)
    @PerKeyRateLimit("melodyBrew")
    public Response brew(@RequestBody Request request, Principal principal) {
        if (hostSubject.isBlank() || !(principal instanceof Authentication auth) || !auth.isAuthenticated()
                || auth instanceof AnonymousAuthenticationToken || !hostSubject.equals(auth.getName())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Brew host not authorized");
        }
        if (request == null || request.herbs() == null || request.herbs().size() < MelodyBrew.MIN_HERBS
                || request.herbs().size() > MelodyBrew.MAX_HERBS
                || request.herbs().stream().anyMatch(h -> h == null || PitchTable.ISLAND_CANON.pitchOf(h).isEmpty())
                || (request.stages() != null && (request.stages().size() != request.herbs().size()
                        || request.stages().stream().anyMatch(s -> s == null || s < 1 || s > 4)))
                || (request.records() != null && (request.records().size() > MAX_RECORDS
                        || request.records().stream().anyMatch(r -> r == null || !records.contains(r))))) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid brew input");
        }
        List<MelodyBrew.Ingredient> items = new ArrayList<>();
        for (int i = 0; i < request.herbs().size(); i++) {
            items.add(new MelodyBrew.Ingredient(request.herbs().get(i),
                    request.stages() == null ? 3 : request.stages().get(i)));
        }
        BrewBench bench = new BrewBench(PitchTable.ISLAND_CANON, tunes);
        if (request.records() != null) {
            request.records().forEach(bench::playRecord);
        }
        MelodyBrew.Tonic t = MelodyBrew.brew(items, PitchTable.ISLAND_CANON);
        FoundTune tune = t.noise() ? null : bench.match(items);
        String contour = t.noise() ? "Noise" : t.melody().replace(" Cadence", "");
        String quality = t.noise() ? "Noise" : t.purifiesWater() ? "Seventh"
                : MelodyBrew.CONTOUR.get(contour)[0];
        return new Response(tune != null ? tune.tonic() : t.tonic(), t.purifiesWater(), contour, quality, t.tier(),
                t.effect(), t.magnitude(), t.durationS(), t.notes(), tune == null ? null : tune.name(),
                tune == null ? null : tune.bonus(), tune == null ? null : tune.learnedFrom(), t.why());
    }
}
