// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.api.dto.ArkFrame;
import com.daedalus.api.dto.EcologyFrame;
import com.daedalus.plugin.events.IslandLifeEvent;
import com.daedalus.plugin.events.ArkVoyageEvent;

import com.daedalus.api.dto.WorldEventFrame;
import com.daedalus.plugin.events.WorldBlockEvent;
import com.daedalus.server.service.WorldService;
import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.World;
import com.daedalus.world.auto.WorldOps;
import org.springframework.context.event.EventListener;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Controller;

import java.util.Map;
import java.util.TreeMap;

/**
 * World events on their own topic. Maze {@code /state} frames stay maze-shaped.
 */
@Controller
public class WorldWebSocketController {

    private final SimpMessagingTemplate stomp;
    private final WorldService worlds;

    public WorldWebSocketController(SimpMessagingTemplate stomp, WorldService worlds) {
        this.stomp = stomp;
        this.worlds = worlds;
    }

    @EventListener
    public void onWorldBlock(WorldBlockEvent e) {
        World live = worlds == null ? null : worlds.inspect(e.worldId());
        BlockCoordinate at = new BlockCoordinate(e.x(), e.y(), e.z());
        stomp.convertAndSend("/topic/world/" + e.worldId() + "/events",
                new WorldEventFrame(e.worldId(), e.kind().name(),
                        e.x(), e.y(), e.z(), e.type(), e.previous(), e.revision(),
                        WorldOps.placeAt(live, at), WorldOps.lotAt(live, at),
                        WorldOps.occupantAt(live, at),
                        WorldOps.driveOn(live, at), WorldOps.actorOn(live, at),
                        WorldOps.atOn(live, at), WorldOps.boxAt(live, at),
                        WorldOps.mazeAt(live, at), WorldOps.leaseAt(live, at),
                        WorldOps.aclAt(live, at)));
    }

    /** Ark voyages on their own topic (ADR-020); world event frames stay cube-shaped. */
    @EventListener
    public void onArkVoyage(ArkVoyageEvent e) {
        stomp.convertAndSend("/topic/world/" + e.worldId() + "/arks",
                new ArkFrame(e.worldId(), e.kind().name(), e.arkId(), e.fromSlot(), e.toSlot(),
                        e.departAt(), e.arriveAt(), worlds == null ? System.currentTimeMillis() : worlds.now()));
    }

    /** Island life on its own topic (ADR-024): days, landings and stowaways. */
    @EventListener
    public void onIslandLife(IslandLifeEvent e) {
        Map<String, Integer> richness = new TreeMap<>();
        e.richness().forEach((slot, n) -> richness.put(String.valueOf(slot), n));
        stomp.convertAndSend("/topic/world/" + e.worldId() + "/ecology",
                new EcologyFrame(e.worldId(), e.kind().name(), e.day(), e.slot(), e.arkId(), e.keys(),
                        richness, worlds == null ? System.currentTimeMillis() : worlds.now()));
    }
}
