// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.world.companion.TonicBook;
import com.daedalus.world.companion.TonicBrewer;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.Principal;
import java.util.List;
import java.util.Set;
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

/** Pure brew calculation for a trusted engine host; never consumes herbs or grants inventory. */
@RestController
@RequestMapping("/api/v1/kennel")
public class KennelController {
    private final TonicBook book;
    private final TonicBrewer brewer;
    private final String hostSubject;

    public record Request(List<String> herbs, String coat, String drinker, Integer stage, Boolean charm, Long seed) {
        public Request {
            herbs = herbs == null ? null : java.util.Collections.unmodifiableList(new java.util.ArrayList<>(herbs));
        }
    }

    public KennelController(@Value("${daedalus.kennel.host-subject:}") String hostSubject) throws IOException {
        this.hostSubject = hostSubject;
        try (var input = KennelController.class.getResourceAsStream("/kennel/tonics.json")) {
            if (input == null) throw new IOException("Packaged tonic book missing");
            book = TonicBook.parse(new String(input.readAllBytes(), StandardCharsets.UTF_8));
        }
        brewer = new TonicBrewer(book);
    }

    @PostMapping(value = "/brew", produces = MediaType.TEXT_PLAIN_VALUE)
    @PerKeyRateLimit("kennelBrew")
    public String brew(@RequestBody Request request, Principal principal) {
        if (hostSubject.isBlank() || !(principal instanceof Authentication auth) || !auth.isAuthenticated()
                || auth instanceof AnonymousAuthenticationToken || !hostSubject.equals(auth.getName())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Kennel host not authorized");
        }
        if (request == null || request.herbs() == null || request.herbs().isEmpty() || request.herbs().size() > book.maxHerbs()
                || request.herbs().stream().anyMatch(h -> h == null || !book.herbRoles().containsKey(h))
                || request.herbs().stream().distinct().count() != request.herbs().size()
                || request.coat() == null || !Set.of("None", "Spots", "Stripes", "Labyrinth").contains(request.coat())
                || request.drinker() == null || !Set.of("cane_corso", "packMember", "other").contains(request.drinker())
                || request.stage() == null || request.stage() < 1 || request.stage() > 3
                || request.charm() == null || request.seed() == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid brew input");
        }
        var rolled = brewer.brew(request.herbs(), request.coat(), request.drinker(), request.stage(), request.charm(), request.seed())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "No recipe for herb set"));
        var brew = rolled.brew();
        var recipe = brew.recipe();
        var wire = new StringBuilder("TONIC 1\n").append("brew ").append(recipe.id()).append(' ')
                .append(brew.factor()).append(' ').append(brew.durationSec()).append(' ').append(rolled.secondRoll() ? 1 : 0)
                .append(' ').append(recipe.mode()).append(' ').append(recipe.breedChancePct()).append('\n');
        for (var mod : brew.mods()) wire.append("mod ").append(mod.stat()).append(' ').append(mod.op()).append(' ').append(mod.value()).append('\n');
        for (var grant : recipe.grants()) wire.append("grant ").append(grant).append('\n');
        return wire.append("end\n").toString();
    }
}
