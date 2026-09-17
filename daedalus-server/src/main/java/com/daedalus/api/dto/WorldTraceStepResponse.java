// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** One driven capability and the revision after it returned. */
public record WorldTraceStepResponse(String capability, String result, long revisionAfter) {
}
