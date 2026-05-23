// SPDX-License-Identifier: MIT

package com.daedalus.plugin.events;

/**
 * Fired when a plugin fails to load or progress through its lifecycle.
 *
 * <p>The host (typically {@code PluginManager} in {@code daedalus-plugin-runtime}) publishes
 * this event whenever a plugin's {@code init}, {@code registerAlgorithms}, {@code start},
 * or {@code stop} call throws — or whenever discovery itself fails (bad JAR, ServiceLoader
 * error). The companion {@code PluginRegistry.Entry} is updated to {@code FAILED} state with
 * the same throwable attached, so listeners that need full detail can look it up.
 *
 * <p>Subscribers are expected to be:
 * <ul>
 *   <li>The WebSocket / STOMP bridge — forward to the UI's "/topic/plugins" channel so
 *       operators see plugin failures live instead of having to grep logs.</li>
 *   <li>Monitoring / alerting plumbing — e.g. a Micrometer counter or a PagerDuty hook.</li>
 * </ul>
 *
 * <p>Pure POJO, like the other {@link PluginEvent} subclasses — no Spring dependency.
 */
public class PluginFailedEvent extends PluginEvent {

    /** Where in the plugin lifecycle the failure occurred. */
    public enum Phase { DISCOVER, INIT, REGISTER_ALGORITHMS, START, STOP }

    private final String pluginId;
    private final String pluginVersion;
    private final Phase phase;
    private final String errorClass;
    private final String errorMessage;
    private final transient Throwable cause;

    public PluginFailedEvent(Object source,
                             String pluginId,
                             String pluginVersion,
                             Phase phase,
                             Throwable cause) {
        super(source);
        this.pluginId = pluginId;
        this.pluginVersion = pluginVersion;
        this.phase = phase;
        this.cause = cause;
        this.errorClass = (cause == null) ? null : cause.getClass().getName();
        this.errorMessage = (cause == null) ? null : cause.getMessage();
    }

    /** Stable plugin id from the manifest. {@code "unknown"} when discovery failed before a manifest could be read. */
    public String pluginId() { return pluginId; }

    /** Plugin version from the manifest, or {@code null} when unavailable. */
    public String pluginVersion() { return pluginVersion; }

    /** Lifecycle phase that failed. */
    public Phase phase() { return phase; }

    /** Fully qualified throwable class name — safe for serialization to WebSocket clients. */
    public String errorClass() { return errorClass; }

    /** Throwable message, or {@code null}. Safe for serialization. */
    public String errorMessage() { return errorMessage; }

    /**
     * The original throwable. Marked {@code transient} so JSON serializers (e.g. the STOMP
     * bridge) don't try to walk a deep cause chain that may include framework internals.
     * In-process listeners can still read it.
     */
    public Throwable cause() { return cause; }
}
