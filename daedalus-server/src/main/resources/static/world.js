// SPDX-License-Identifier: MIT
// World One W1.4 — inspect + listen. app.js owns leftover-state wiring.
"use strict";
(function (global) {
  const WORLD = "world-zero";
  const MAX_EVENTS = 8;
  const events = [];
  /** Same ids as {@code WorldZeroDrive}. No agent.* verbs. */
  const DRIVEN = {
    "world.inspect": {method: "GET", path: () => "/world/" + WORLD},
    "chunk.inspect": {method: "GET", path: at =>
        "/world/" + WORLD + "/chunk?x=" + at.x + "&y=" + at.y + "&z=" + at.z},
    "block.inspect": {method: "GET", path: at =>
        "/world/" + WORLD + "/block?x=" + at.x + "&y=" + at.y + "&z=" + at.z},
    "block.place": {method: "PUT", path: () => "/world/" + WORLD + "/block",
      body: (at, type) => ({x: at.x, y: at.y, z: at.z, type: type || "STONE"})},
    "block.remove": {method: "DELETE", path: at =>
        "/world/" + WORLD + "/block?x=" + at.x + "&y=" + at.y + "&z=" + at.z},
    "door.inspect": {method: "GET", path: () => "/world/" + WORLD + "/door"},
    "door.open": {method: "POST", path: () => "/world/" + WORLD + "/door/open"},
    "door.close": {method: "POST", path: () => "/world/" + WORLD + "/door/close"},
    "trap.inspect": {method: "GET", path: () => "/world/" + WORLD + "/trap"},
    "trap.arm": {method: "POST", path: () => "/world/" + WORLD + "/trap/arm"},
    "trap.disarm": {method: "POST", path: () => "/world/" + WORLD + "/trap/disarm"},
    "portal.inspect": {method: "GET", path: () => "/world/" + WORLD + "/portal"},
    "portal.open": {method: "POST", path: () => "/world/" + WORLD + "/portal/open"},
    "portal.seal": {method: "POST", path: () => "/world/" + WORLD + "/portal/seal"},
    "npc.inspect": {method: "GET", path: () => "/world/" + WORLD + "/npc"},
    "npc.talk": {method: "POST", path: () => "/world/" + WORLD + "/npc/talk"},
    "npc.hush": {method: "POST", path: () => "/world/" + WORLD + "/npc/hush"},
    "parcel.lease": {method: "POST", path: () => "/world/" + WORLD + "/parcels/lease"},
    "stamp.apply": {method: "POST", path: () => "/world/" + WORLD + "/stamp",
      body: (at, type, mazeId) => {
        const body = {x: at.x, y: at.y, z: at.z};
        if (mazeId) {
          body.mazeId = mazeId;
          body.next = true;
        }
        return body;
      }},
  };

  async function inspect(host) {
    const box = host && host.$ && host.$("worldBox");
    if (!box) return;
    try {
      const world = await host.api("/world/" + WORLD);
      const door = await host.api("/world/" + WORLD + "/door");
      const trap = await host.api("/world/" + WORLD + "/trap");
      const portal = await host.api("/world/" + WORLD + "/portal");
      const npc = await host.api("/world/" + WORLD + "/npc");
      const chunk = await host.api("/world/" + WORLD + "/chunk?x=0&y=0&z=0");
      const trace = await host.api("/world/" + WORLD + "/trace");
      paint(box, world, door, trap, portal, npc, chunk, trace);
    } catch (e) {
      box.textContent = "world inspect unavailable — " + (e && e.message ? e.message : e);
    }
  }

  function onEvent(host, frame) {
    if (!frame || frame.worldId !== WORLD) {
      return;
    }
    events.unshift(frame);
    while (events.length > MAX_EVENTS) {
      events.pop();
    }
    inspect(host);
  }

  async function drive(host, capability, at, type) {
    if (!host || !host.api) {
      throw new Error("World host is required");
    }
    const step = DRIVEN[capability];
    if (!step) {
      throw new Error("Unknown capability " + capability);
    }
    const cell = at || {x: 0, y: 0, z: 0};
    const opts = {method: step.method};
    if (step.body) {
      opts.headers = {"Content-Type": "application/json"};
      const mazeId = host.state && host.state.maze && host.state.maze.id;
      opts.body = JSON.stringify(step.body(cell, type, mazeId));
    }
    return host.api(step.path(cell), opts);
  }

  /**
   * Project the generated lab maze into world-zero. Occupied origin
   * walks +X. Daily / campaign stay inspect-only.
   */
  async function projectLab(host) {
    if (!host || !host.api) {
      return;
    }
    if (!host.state || !host.state.maze || !host.state.maze.id) {
      return inspect(host);
    }
    let stamped = false;
    try {
      const result = await drive(host, "stamp.apply");
      stamped = result && result.ok;
    } catch (e) {
      // named overlap is 200; a missing maze is a race
    }
    if (stamped) {
      try {
        await drive(host, "parcel.lease");
      } catch (e) {
        // lease is best-effort after a named stamp
      }
    }
    return inspect(host);
  }

  function paint(box, world, door, trap, portal, npc, chunk, trace) {
    box.replaceChildren();
    row(box, "world", world && world.id ? world.id : WORLD);
    row(box, "revision", world && world.revision != null ? String(world.revision) : "—");
    row(box, "chunks", world && world.chunkCount != null ? String(world.chunkCount) : "—");
    row(box, "door", door && door.state ? door.state : "—");
    row(box, "trap", trap && trap.state ? trap.state : "—");
    row(box, "portal", portal && portal.state ? portal.state : "—");
    row(box, "npc", npc && npc.state ? npc.state : "—");
    row(box, "plots", world && world.plots != null ? String(world.plots) : "—");
    row(box, "street", world && world.street ? world.street : "—");
    row(box, "place", world && world.place ? world.place : "—");
    row(box, "lot", world && world.lot ? world.lot : "—");
    row(box, "lease", world && world.lease ? world.lease : "—");
    row(box, "maze", world && world.maze ? world.maze : "—");
    const occupied = chunk && chunk.present && chunk.occupied > 0;
    const slice = occupied
        ? "0,0,0 occupied " + chunk.occupied
        : "0,0,0 empty";
    row(box, "chunk", slice, occupied);
    const last = document.createElement("div");
    last.className = "hint";
    last.textContent = events.length ? "last events" : "listening — no world events yet";
    box.appendChild(last);
    events.forEach(frame => {
      const line = document.createElement("div");
      const at = [frame.place, frame.lot].filter(Boolean).join(" ");
      line.textContent = frame.kind + " " + frame.x + "," + frame.y + "," + frame.z
          + " " + (frame.type || "") + (at ? " " + at : "") + " r=" + frame.revision;
      box.appendChild(line);
    });
    const built = document.createElement("div");
    built.className = "hint";
    const steps = trace && trace.steps ? trace.steps : [];
    built.textContent = steps.length
        ? "builder " + steps[steps.length - 1].capability
        : "builder — WorldOps only";
    box.appendChild(built);
  }

  function row(box, label, value, wood) {
    const line = document.createElement("div");
    const name = document.createElement("b");
    name.textContent = label;
    line.appendChild(name);
    const named = (label === "place" || label === "street") && value && value !== "—";
    if (named || wood) {
      const ink = document.createElement("span");
      ink.className = named ? "place" : "slab";
      ink.textContent = " " + value;
      line.appendChild(ink);
    } else {
      line.appendChild(document.createTextNode(" " + value));
    }
    box.appendChild(line);
  }

  global.DaedalusWorld = {inspect, onEvent, drive, projectLab, DRIVEN, WORLD};
})(window);
