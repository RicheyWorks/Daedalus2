// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.daedalus.plugin.PluginManifest;

/**
 * Element of the response body for {@code GET /api/plugins}. Lightweight projection of a
 * {@code PluginRegistry.Entry} suitable for HTTP clients.
 *
 * @param id       plugin id from the manifest
 * @param state    lifecycle state name ({@code DISCOVERED}, {@code INITIALIZED}, {@code STARTED},
 *                 {@code STOPPED}, or {@code FAILED})
 * @param manifest the plugin's full manifest
 * @param error    {@code toString()} of the last error, or {@code null} if the plugin is healthy
 */
public record PluginInfo(String id, String state, PluginManifest manifest, String error) {}
