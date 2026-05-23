package com.daedalus.plugin.events;

import org.springframework.context.ApplicationEvent;

/** Marker base for all Daedalus events that plugins can listen on. */
public abstract class PluginEvent extends ApplicationEvent {
    protected PluginEvent(Object source) { super(source); }
}
