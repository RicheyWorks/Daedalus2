// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.plugin.events.MazeMutatedEvent;
import com.daedalus.world.WorldId;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Service;

/**
 * Maze living ticks stay on the lab grid. This subscriber re-projects a
 * stamped slab when that maze mutates. No wallet types. WorldService still
 * does not open the maze cache — the event already carries the snapshot.
 */
@Service
public class LivingSlabService {

    private final WorldService worlds;

    public LivingSlabService(WorldService worlds) {
        this.worlds = worlds;
    }

    @EventListener
    public void onMazeMutated(MazeMutatedEvent event) {
        if (event == null || event.mazeId() == null || event.grid() == null) {
            return;
        }
        worlds.syncSlab(WorldId.ZERO.value(), event.mazeId(), event.grid());
    }
}
