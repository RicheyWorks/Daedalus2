// SPDX-License-Identifier: MIT
package com.daedalus.server.controller;

import com.daedalus.api.dto.ChunkBlocksResponse;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.service.OceanHostService;
import java.io.IOException;
import java.security.Principal;
import java.util.NoSuchElementException;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/ocean/v1")
@ConditionalOnProperty(name="daedalus.ocean.enabled",havingValue="true")
public class OceanHostController {
    private final OceanHostService ocean;
    public OceanHostController(OceanHostService ocean) { this.ocean=ocean; }
    @GetMapping
    @PerKeyRateLimit("oceanChunks")
    public OceanHostService.Manifest manifest(Principal principal) {
        requireIdentity(principal);return ocean.manifest();
    }
    @GetMapping("/chunk")
    @PerKeyRateLimit("oceanChunks")
    public ChunkBlocksResponse chunk(@RequestParam int x,@RequestParam int y,@RequestParam int z,Principal principal) throws IOException {
        requireIdentity(principal);
        try { return ocean.chunk(x,y,z); }
        catch(NoSuchElementException outside) { throw new ResponseStatusException(HttpStatus.NOT_FOUND,outside.getMessage()); }
        catch(IOException unavailable) { throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,"Ocean storage unavailable",unavailable); }
    }
    private static void requireIdentity(Principal principal) {
        if(principal==null||principal.getName()==null||principal.getName().isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,"Authenticated principal required");
        }
    }
}
