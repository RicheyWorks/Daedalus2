// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.daedalus.api.validation.AlgorithmId;
import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;

import java.util.List;

/**
 * Request body for {@code POST /api/v1/maze/generate}.
 *
 * <p>Validation contract (enforced by {@code spring-boot-starter-validation} when the
 * controller annotates the parameter with {@code @Valid}):
 * <ul>
 *   <li>{@code generatorId} — see {@link AlgorithmId}: required, non-blank, lowercase +
 *       digits + hyphens only, 1..64 characters. Matches the id space used by the
 *       {@code GeneratorRegistry}.</li>
 *   <li>{@code rows}, {@code cols} — bounded to a sane range. The lower bound rules out
 *       degenerate 0/1 grids that several generators don't define behavior for; the upper
 *       bound (512) is a guardrail against accidental memory blowups (a 512×512 grid
 *       allocates roughly 1 MB of {@code boolean[]} state alone).</li>
 *   <li>{@code seed} — optional. {@code null} means "let the server pick {@code System.nanoTime()}".</li>
 *   <li>{@code hotspots} — optional, at most 64, and <em>each element</em> is validated against
 *       {@link Hotspot}'s own bounds. The cascade is written {@code List<@Valid Hotspot>} rather
 *       than {@code @Valid List<Hotspot>}: the latter still cascades in Hibernate Validator 9,
 *       but only by a deprecated path (HV000271) that names the container instead of what is
 *       inside it. When that path goes, the element bounds stop being enforced — silently, and
 *       in the direction that accepts bad input. {@code MazeControllerValidationTest} pins the
 *       cascade so the removal cannot happen quietly.</li>
 *   <li>{@code braid} — optional fraction of dead ends to open, in {@code [0, 1]}.
 *       {@code null} or {@code 0} is today's generate: a spanning tree (for the
 *       22 tree generators). The tournament already braided its sample; without
 *       this field "load the adversarial maze" rebuilt the tree and the race
 *       was a different question.</li>
 * </ul>
 *
 * @param generatorId identifier of the registered generator algorithm (e.g. {@code "binary-tree"})
 * @param rows        number of rows in the maze grid
 * @param cols        number of columns in the maze grid
 * @param seed        optional RNG seed; when {@code null} the server uses {@code System.nanoTime()}
 * @param hotspots    optional weighted cells; {@code null} for uniform cost
 * @param braid       optional dead-end opening factor in {@code [0, 1]}; {@code null} is none
 */
@com.fasterxml.jackson.annotation.JsonInclude(
        com.fasterxml.jackson.annotation.JsonInclude.Include.NON_NULL)
public record GenerateRequest(
        @AlgorithmId
        String generatorId,

        @Min(value = 2,   message = "rows must be at least 2")
        @Max(value = 512, message = "rows must be at most 512")
        int rows,

        @Min(value = 2,   message = "cols must be at least 2")
        @Max(value = 512, message = "cols must be at most 512")
        int cols,

        Long seed,

        @Size(max = 64, message = "at most 64 hotspots per maze")
        List<@Valid Hotspot> hotspots,

        @DecimalMin(value = "0.0", message = "braid must be at least 0")
        @DecimalMax(value = "1.0", message = "braid must be at most 1")
        Double braid
) {
    public GenerateRequest {
        hotspots = hotspots == null ? null : List.copyOf(hotspots);
    }

    /** Pre-hotspot shape — uniform-cost maze, kept for source compatibility. */
    public GenerateRequest(String generatorId, int rows, int cols, Long seed) {
        this(generatorId, rows, cols, seed, null, null);
    }

    /** Uniform-cost maze, optional braid omitted. */
    public GenerateRequest(String generatorId, int rows, int cols, Long seed,
                           List<Hotspot> hotspots) {
        this(generatorId, rows, cols, seed, hotspots, null);
    }
}
