// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.service.RealmLandService;
import java.security.Principal;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/realms")
public class RealmLandController {
    private final RealmLandService lands;
    public RealmLandController(RealmLandService lands) { this.lands = lands; }

    @GetMapping("/{realm}/lands")
    @PerKeyRateLimit("oceanChunks")
    public RealmLandService.District district(@PathVariable String realm, @RequestParam int district,
                                              Principal principal) {
        if (principal == null || principal.getName() == null || principal.getName().isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Authenticated principal required");
        }
        return lands.district(realm, district);
    }
}
