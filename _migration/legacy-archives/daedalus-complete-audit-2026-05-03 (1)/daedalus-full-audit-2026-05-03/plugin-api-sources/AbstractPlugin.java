package com.daedalus.plugin;

/** Convenience base — stash the context once and forget. */
public abstract class AbstractPlugin implements MazePlugin {

    protected PluginContext context;

    @Override
    public void init(PluginContext ctx) {
        this.context = ctx;
    }
}
