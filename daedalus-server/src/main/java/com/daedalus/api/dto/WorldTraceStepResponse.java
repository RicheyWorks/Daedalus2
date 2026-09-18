// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** One driven capability and the revision after it returned. */
public record WorldTraceStepResponse(String capability, String result, long revisionAfter,
                                    String actor, String at, String maze) {

    public WorldTraceStepResponse {
        actor = actor == null ? "" : actor;
        at = at == null ? "" : at;
        maze = maze == null ? "" : maze;
    }

    public WorldTraceStepResponse(String capability, String result, long revisionAfter,
            String actor, String at) {
        this(capability, result, revisionAfter, actor, at, "");
    }

    public WorldTraceStepResponse(String capability, String result, long revisionAfter) {
        this(capability, result, revisionAfter, "", "", "");
    }

    public WorldTraceStepResponse(String capability, String result, long revisionAfter,
            String actor) {
        this(capability, result, revisionAfter, actor, "", "");
    }
}
