// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.world.island.VoxelIsle;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * The Orrery Reach for the web (ADR-058): Claude Island and its four neighbouring isles, grown by the Java port of
 * the Unreal plugin's voxel isle core, so the browser draws the same isles Unreal does. It's read-only and
 * deterministic, so the reply is built once and kept.
 *
 * <p>Each isle carries:
 * <ul>
 *   <li>its settings and offset (in Unreal centimetres; one cube is 100 cm);</li>
 *   <li>its column grid, {@code (2r+5)^2} columns, row-major from {@code (-r-2, -r-2)};</li>
 *   <li>the column tops and bottoms, as base64 of little-endian int16 ({@code -32768} = no column).</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/v1/reach")
@Tag(name = "Orrery Reach", description = "The Orrery Reach's voxel isles, the same as Unreal's.")
public class ReachController {

    private static final short NONE = Short.MIN_VALUE;
    private volatile Map<String, Object> orrery;

    @GetMapping("/orrery")
    @Operation(summary = "The Orrery Reach's five isles: settings, offsets and column heights.")
    public ResponseEntity<Map<String, Object>> orrery() {
        Map<String, Object> body = orrery;
        if (body == null) {
            body = build();
            orrery = body;
        }
        return ResponseEntity.ok().cacheControl(CacheControl.maxAge(1, TimeUnit.HOURS)).body(body);
    }

    static Map<String, Object> build() {
        List<Map<String, Object>> isles = new ArrayList<>();
        for (VoxelIsle.Placed placed : VoxelIsle.orreryReach()) {
            VoxelIsle.Params p = placed.params();
            int[][] g = VoxelIsle.columns(p);
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("name", placed.name());
            row.put("seed", p.seed());
            row.put("radius", p.radius());
            row.put("summitHeight", p.summitHeight());
            row.put("depth", p.depth());
            row.put("pond", List.of(p.pondX(), p.pondY(), p.pondRadius()));
            row.put("offsetCm", List.of(placed.dx(), placed.dy(), placed.dz()));
            row.put("grid", 2 * (p.radius() + 2) + 1);
            row.put("tops", pack(g[0]));
            row.put("bottoms", pack(g[1]));
            isles.add(row);
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("name", "The Orrery Reach");
        body.put("cubeCm", 100);
        body.put("isles", isles);
        // Claude Island's sky bridges (orr_reach.py); the Vault stays out of reach on foot.
        body.put("bridges", List.of("Bloomfields", "Tidewells", "Lens Forge"));
        return body;
    }

    private static String pack(int[] v) {
        ByteBuffer b = ByteBuffer.allocate(v.length * 2).order(ByteOrder.LITTLE_ENDIAN);
        for (int x : v) {
            b.putShort(x == VoxelIsle.OFF ? NONE : (short) x);
        }
        return Base64.getEncoder().encodeToString(b.array());
    }
}
