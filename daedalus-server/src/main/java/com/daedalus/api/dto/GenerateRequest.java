// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.daedalus.api.validation.AlgorithmId;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

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
 * </ul>
 *
 * @param generatorId identifier of the registered generator algorithm (e.g. {@code "binary-tree"})
 * @param rows        number of rows in the maze grid
 * @param cols        number of columns in the maze grid
 * @param seed        optional RNG seed; when {@code null} the server uses {@code System.nanoTime()}
 */
public record GenerateRequest(
        @AlgorithmId
        String generatorId,

        @Min(value = 2,   message = "rows must be at least 2")
        @Max(value = 512, message = "rows must be at most 512")
        int rows,

        @Min(value = 2,   message = "cols must be at least 2")
        @Max(value = 512, message = "cols must be at most 512")
        int cols,

        Long seed
) {}
