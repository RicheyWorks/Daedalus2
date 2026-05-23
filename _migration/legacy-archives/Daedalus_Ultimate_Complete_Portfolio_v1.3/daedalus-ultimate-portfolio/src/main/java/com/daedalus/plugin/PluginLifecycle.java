package com.daedalus.plugin;

/** Internal state machine for tracking plugin lifecycle progression. */
public enum PluginLifecycle {
    DISCOVERED, INITIALIZED, REGISTERED, STARTED, STOPPED, FAILED
}
