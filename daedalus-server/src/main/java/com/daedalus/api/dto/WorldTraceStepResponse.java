// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** One driven capability and the revision after it returned. */
public record WorldTraceStepResponse(String capability, String result, long revisionAfter,
                                    String actor, String at, String maze, String lease,
                                    String place, String lot, String box) {

    public WorldTraceStepResponse {
        actor = actor == null ? "" : actor;
        at = at == null ? "" : at;
        maze = maze == null ? "" : maze;
        lease = lease == null ? "" : lease;
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        box = box == null ? "" : box;
    }

    public WorldTraceStepResponse(String capability, String result, long revisionAfter,
            String actor, String at, String maze, String lease, String place, String lot) {
        this(capability, result, revisionAfter, actor, at, maze, lease, place, lot, "");
    }

    public WorldTraceStepResponse(String capability, String result, long revisionAfter,
            String actor, String at, String maze, String lease, String place) {
        this(capability, result, revisionAfter, actor, at, maze, lease, place, "", "");
    }

    public WorldTraceStepResponse(String capability, String result, long revisionAfter,
            String actor, String at, String maze, String lease) {
        this(capability, result, revisionAfter, actor, at, maze, lease, "", "", "");
    }

    public WorldTraceStepResponse(String capability, String result, long revisionAfter,
            String actor, String at, String maze) {
        this(capability, result, revisionAfter, actor, at, maze, "", "", "", "");
    }

    public WorldTraceStepResponse(String capability, String result, long revisionAfter,
            String actor, String at) {
        this(capability, result, revisionAfter, actor, at, "", "", "", "", "");
    }

    public WorldTraceStepResponse(String capability, String result, long revisionAfter) {
        this(capability, result, revisionAfter, "", "", "", "", "", "", "");
    }

    public WorldTraceStepResponse(String capability, String result, long revisionAfter,
            String actor) {
        this(capability, result, revisionAfter, actor, "", "", "", "", "", "");
    }
}
