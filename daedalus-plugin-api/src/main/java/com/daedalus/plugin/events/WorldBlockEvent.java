// SPDX-License-Identifier: MIT

package com.daedalus.plugin.events;

/**
 * Voxel mutation beside the maze events. STOMP maps these to
 * {@code /topic/world/{id}/events} — not the maze {@code /state} topic.
 */
public class WorldBlockEvent extends PluginEvent {

    public enum Kind {
        BLOCK_PLACED,
        BLOCK_REMOVED,
        WORLD_REVISION_CHANGED
    }

    private final String worldId;
    private final Kind kind;
    private final int x;
    private final int y;
    private final int z;
    private final String type;
    private final String previous;
    private final long revision;

    public WorldBlockEvent(Object source, String worldId, Kind kind,
                           int x, int y, int z, String type, String previous, long revision) {
        super(source);
        this.worldId = worldId;
        this.kind = kind;
        this.x = x;
        this.y = y;
        this.z = z;
        this.type = type;
        this.previous = previous;
        this.revision = revision;
    }

    public String worldId() { return worldId; }
    public Kind kind() { return kind; }
    public int x() { return x; }
    public int y() { return y; }
    public int z() { return z; }
    public String type() { return type; }
    public String previous() { return previous; }
    public long revision() { return revision; }
}
