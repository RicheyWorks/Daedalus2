// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.UUID;

/**
 * STOMP frame published to {@code /topic/maze/{id}/solver} when a solver finishes a run.
 *
 * @param mazeId     id of the maze that was solved
 * @param solverId   id of the solver that produced the run
 * @param pathLength length of the solution path (0 when {@code success=false})
 * @param success    whether the solver actually reached the goal
 */
public record SolvedFrame(UUID mazeId, String solverId, int pathLength, boolean success) {}
