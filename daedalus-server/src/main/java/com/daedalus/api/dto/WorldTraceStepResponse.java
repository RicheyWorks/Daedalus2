// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** One driven capability and the revision after it returned. */
public record WorldTraceStepResponse(String capability, String result, long revisionAfter,
                                    String actor) {

    public WorldTraceStepResponse {
        actor = actor == null ? "" : actor;
    }

    public WorldTraceStepResponse(String capability, String result, long revisionAfter) {
        this(capability, result, revisionAfter, "");
    }
}
