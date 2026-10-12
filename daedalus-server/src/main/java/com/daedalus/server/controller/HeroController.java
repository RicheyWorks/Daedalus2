// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.HeroRequest;
import com.daedalus.api.dto.HeroResponse;
import com.daedalus.api.dto.HeroRulesResponse;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.service.HeroService;
import com.daedalus.world.adventure.FoeKind;
import com.daedalus.world.adventure.Hero;
import com.daedalus.world.adventure.HeroRules;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.security.Principal;
import java.util.ArrayList;
import java.util.List;

import static org.springframework.http.HttpStatus.BAD_REQUEST;

/**
 * Heroes over HTTP (ADR-037): the Zelda II game of experience and levels. The realm fights; the server keeps
 * the score. A hero is one per person, across every world.
 */
@RestController
@RequestMapping("/api/v1/hero")
@Tag(name = "Hero", description = "Experience, levels and the rules of the fight.")
public class HeroController {

    private final HeroService heroes;

    public HeroController(HeroService heroes) {
        this.heroes = heroes;
    }

    private static String actor(Principal principal, String claimed) {
        if (principal != null && principal.getName() != null && !principal.getName().isBlank()) {
            return principal.getName();
        }
        return claimed;
    }

    static HeroResponse view(String result, Hero h) {
        List<String> can = new ArrayList<>();
        for (HeroRules.Stat s : HeroRules.Stat.values()) {
            if (h.canRaise(s)) {
                can.add(s.name());
            }
        }
        return new HeroResponse(result, h.name(), h.exp(), h.attack(), h.magic(), h.life(), h.beaten(),
                HeroRules.cost(HeroRules.Stat.ATTACK, h.attack()), HeroRules.cost(HeroRules.Stat.MAGIC, h.magic()),
                HeroRules.cost(HeroRules.Stat.LIFE, h.life()), can, HeroRules.maxLife(h.life()),
                HeroRules.maxMagic(h.magic()), HeroRules.damage(h.attack()));
    }

    private static ResponseEntity<HeroResponse> answer(HeroService.HeroWrite w) {
        if (w.hero() == null) {
            throw new ResponseStatusException(BAD_REQUEST, "Pick a name first (letters, digits, . _ @ -)");
        }
        return ResponseEntity.ok(view(w.result(), w.hero()));
    }

    @GetMapping
    @Operation(summary = "Your hero: experience, the three levels, what the next of each costs.")
    public ResponseEntity<HeroResponse> hero(@RequestParam(required = false) String actorId, Principal principal) {
        Hero h = heroes.hero(actor(principal, actorId));
        if (h == null) {
            throw new ResponseStatusException(BAD_REQUEST, "Pick a name first (letters, digits, . _ @ -)");
        }
        return ResponseEntity.ok(view("SEEN", h));
    }

    @GetMapping("/rules")
    @Operation(summary = "The foes and the level costs every client plays by (ADR-037).")
    public ResponseEntity<HeroRulesResponse> rules() {
        List<HeroRulesResponse.Foe> foes = new ArrayList<>();
        for (FoeKind f : FoeKind.values()) {
            foes.add(new HeroRulesResponse.Foe(f.name(), f.title(), f.life(), f.power(), f.exp(),
                    f.reach() == null ? null : f.reach().name(), f.guard() == null ? null : f.guard().name(),
                    f.strike() == null ? null : f.strike().name(), f.shifting(), f.speed()));
        }
        return ResponseEntity.ok(new HeroRulesResponse(foes, costs(HeroRules.Stat.ATTACK), costs(HeroRules.Stat.MAGIC),
                costs(HeroRules.Stat.LIFE), HeroRules.HEAL_COST, HeroRules.HEAL_AMOUNT, HeroService.MIN_BETWEEN_MS));
    }

    private static List<Integer> costs(HeroRules.Stat s) {
        List<Integer> out = new ArrayList<>();
        for (int l = 1; l < HeroRules.TABLE_LEVELS; l++) {
            out.add(HeroRules.cost(s, l));
        }
        return out;
    }

    @PostMapping("/defeat")
    @Operation(summary = "Report a foe beaten: the server adds that foe's experience from its own table.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<HeroResponse> defeat(@Valid @RequestBody HeroRequest body, Principal principal) {
        if (body.foe() == null) {
            throw new ResponseStatusException(BAD_REQUEST, "foe is required");
        }
        return answer(heroes.beat(actor(principal, body.actorId()), FoeKind.valueOf(body.foe())));
    }

    @PostMapping("/raise")
    @Operation(summary = "Spend experience on Attack, Magic or Life; it resets to zero, as in Zelda II.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<HeroResponse> raise(@Valid @RequestBody HeroRequest body, Principal principal) {
        if (body.stat() == null) {
            throw new ResponseStatusException(BAD_REQUEST, "stat is required");
        }
        return answer(heroes.raise(actor(principal, body.actorId()), HeroRules.Stat.valueOf(body.stat())));
    }

    @PostMapping("/fall")
    @Operation(summary = "Fall in battle: unspent experience is lost; levels stay.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<HeroResponse> fall(@Valid @RequestBody HeroRequest body, Principal principal) {
        return answer(heroes.fall(actor(principal, body.actorId())));
    }
}
