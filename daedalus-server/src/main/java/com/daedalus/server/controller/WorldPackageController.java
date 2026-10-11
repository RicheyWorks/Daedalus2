// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.WorldManifest;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.service.WorldPackageService;
import com.daedalus.server.web.ResourceNotFoundException;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.CacheControl;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

/**
 * Daedalus World Packages over HTTP (ADR-032): the whole package as a zip, or its manifest and geometry on
 * their own for an engine that streams them. Public, like the chunks they are made from; built once per
 * world revision.
 */
@RestController
@RequestMapping("/api/v1")
@Tag(name = "World Package", description = "Export a world once; load it in Blender, Unreal, the realm.")
public class WorldPackageController {

    private final WorldPackageService packages;

    public WorldPackageController(WorldPackageService packages) {
        this.packages = packages;
    }

    private WorldPackageService.Built built(String id) {
        WorldPackageService.Built b = packages.build(id,
                ServletUriComponentsBuilder.fromCurrentContextPath().build().toUriString());
        if (b == null) {
            throw ResourceNotFoundException.world(id);
        }
        return b;
    }

    @GetMapping(value = "/world/{id}/package", produces = "application/zip")
    @Operation(summary = "The world as a Daedalus World Package: manifest.json, world.glb (glTF 2.0), assets/.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<byte[]> pack(@PathVariable String id) {
        WorldPackageService.Built b = built(id);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + id + "-r" + b.revision() + ".daedalus.zip\"")
                // No ETag: ships sail without moving a cube, so the zip can change within one revision.
                .cacheControl(CacheControl.noCache())
                .contentType(MediaType.parseMediaType("application/zip"))
                .body(b.zip());
    }

    @GetMapping("/world/{id}/package/manifest")
    @Operation(summary = "The package's manifest: islands, gates, arks, palette, the live API.")
    public WorldManifest manifest(@PathVariable String id) {
        return built(id).manifest();
    }

    @GetMapping(value = "/world/{id}/package/world.glb", produces = "model/gltf-binary")
    @Operation(summary = "The package's geometry: glTF 2.0 binary, one node per 16-cube chunk.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<byte[]> glb(@PathVariable String id) {
        WorldPackageService.Built b = built(id);
        return ResponseEntity.ok()
                .eTag("\"" + id + "-" + b.revision() + "\"")
                .cacheControl(CacheControl.noCache())
                .contentType(MediaType.parseMediaType("model/gltf-binary"))
                .body(b.glb());
    }
}
