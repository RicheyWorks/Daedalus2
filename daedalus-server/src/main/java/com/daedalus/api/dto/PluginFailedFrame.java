// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * STOMP frame published to {@code /topic/plugins/failures} whenever a plugin throws during one
 * of its lifecycle phases. Lets the front-end surface plugin failures as toasts or banner
 * alerts instead of leaving them buried in server logs.
 *
 * @param pluginId      id from the plugin's manifest (or a synthetic id for failures that occur
 *                      before manifest read, e.g. classloader construction errors)
 * @param pluginVersion version from the plugin's manifest, or empty when manifest read failed
 * @param phase         which lifecycle phase failed: {@code DISCOVER}, {@code INIT},
 *                      {@code REGISTER_ALGORITHMS}, {@code START}, or {@code STOP}
 * @param errorClass    fully-qualified class name of the throwable
 * @param errorMessage  the throwable's message (may be {@code null})
 * @param timestamp     epoch-millis when the failure was published
 */
public record PluginFailedFrame(String pluginId, String pluginVersion, String phase,
                                String errorClass, String errorMessage, long timestamp) {}
