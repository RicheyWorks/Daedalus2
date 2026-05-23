package com.daedalus.plugin.events;

/**
 * Marker base for all Daedalus events that plugins can listen on.
 *
 * <p>Pure POJO — no Spring inheritance. Spring 4.2+ accepts arbitrary objects in
 * {@code ApplicationEventPublisher.publishEvent(Object)} and {@code @EventListener}
 * fires on POJO event types, so removing the {@code ApplicationEvent} parent does
 * not change publishing or subscription semantics under a Spring host.
 *
 * <p>Keeping this Spring-free is what lets {@code daedalus-plugin-api} stay
 * Spring-free; the {@code ApplicationEvent} adapter (if needed) lives in
 * {@code daedalus-plugin-runtime}.
 */
public abstract class PluginEvent {

    private final Object source;
    private final long timestamp;

    protected PluginEvent(Object source) {
        this.source = source;
        this.timestamp = System.currentTimeMillis();
    }

    /** The component that emitted the event (mirrors {@code ApplicationEvent#getSource}). */
    public Object getSource() { return source; }

    /** Wall-clock millis when the event was constructed. */
    public long getTimestamp() { return timestamp; }
}
