// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.service.RealmDirectoryService;
import java.security.Principal;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1")
public class RealmDirectoryController {
    private final RealmDirectoryService directory;
    public RealmDirectoryController(RealmDirectoryService directory) { this.directory = directory; }

    @GetMapping("/realms")
    @PerKeyRateLimit("oceanChunks")
    public RealmDirectoryService.Directory realms(Principal principal) {
        if (principal == null || principal.getName() == null || principal.getName().isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Authenticated principal required");
        }
        try { return directory.directory(); }
        catch (IllegalStateException conflict) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Realm directory unavailable", conflict);
        }
    }
}
