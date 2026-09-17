// SPDX-License-Identifier: MIT
// World One W1.4 — inspect + listen. app.js owns leftover-state wiring.
"use strict";
(function (global) {
  const WORLD = "world-zero";
  const MAX_EVENTS = 8;
  const events = [];

  async function inspect(host) {
    const box = host && host.$ && host.$("worldBox");
    if (!box) return;
    try {
      const world = await host.api("/world/" + WORLD);
      const door = await host.api("/world/" + WORLD + "/door");
      const chunk = await host.api("/world/" + WORLD + "/chunk?x=0&y=0&z=0");
      paint(box, world, door, chunk);
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

  function paint(box, world, door, chunk) {
    box.replaceChildren();
    row(box, "world", world && world.id ? world.id : WORLD);
    row(box, "revision", world && world.revision != null ? String(world.revision) : "—");
    row(box, "chunks", world && world.chunkCount != null ? String(world.chunkCount) : "—");
    row(box, "door", door && door.state ? door.state : "—");
    const slice = chunk && chunk.present
        ? "0,0,0 occupied " + chunk.occupied
        : "0,0,0 empty";
    row(box, "chunk", slice);
    const last = document.createElement("div");
    last.className = "hint";
    last.textContent = events.length ? "last events" : "listening — no world events yet";
    box.appendChild(last);
    events.forEach(frame => {
      const line = document.createElement("div");
      line.textContent = frame.kind + " " + frame.x + "," + frame.y + "," + frame.z
          + " " + (frame.type || "") + " r=" + frame.revision;
      box.appendChild(line);
    });
  }

  function row(box, label, value) {
    const line = document.createElement("div");
    const name = document.createElement("b");
    name.textContent = label;
    line.appendChild(name);
    line.appendChild(document.createTextNode(" " + value));
    box.appendChild(line);
  }

  global.DaedalusWorld = {inspect, onEvent, WORLD};
})(window);
