/* SPDX-License-Identifier: MIT
 * Read-only Parcels expedition. Claims, builds and NFT minting belong to the server realm.
 */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const canvas = $("districtCanvas"), ctx = canvas.getContext("2d");
  const MIN_X = -26, MIN_Z = -148, SIDE = 148, PLOT_SIZE = 16, MAX_Y = 32;
  const PLAZA_IDS = new Set([27, 28, 35, 36]);
  const SHOWS = ["LAWN", "GROVE", "PAVILION", "TOWER", "SCULPTURE", "POND"];
  const DEFAULT_SEED = "33033", SAVE_VERSION = 1;
  const prefersReducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const keys = new Set(), touchDirections = new Map();
  const state = {
    seed: DEFAULT_SEED, worldId: "", worlds: [], plots: [], missions: [], stage: 0,
    player: { x: 48, z: -74, heading: 0 }, visited: new Set(), pinned: new Set(), selected: null,
    mode: "local", connecting: false, sourceMessage: "Local visitor draft", zoom: 1, overview: true,
    width: 1, height: 1, scale: 1, camera: { x: 48, z: -74 }, time: 0, lastSave: 0,
    loadSequence: 0, toastTimer: 0, saveAvailable: true, pointerDown: null
  };

  function seedString(raw) {
    if (typeof raw !== "string" || !/^-?\d{1,20}$/.test(raw.trim())) return null;
    try {
      const n = BigInt(raw.trim());
      return n >= -(1n << 63n) && n < (1n << 63n) ? n.toString() : null;
    } catch (_) { return null; }
  }
  const nice = word => word.toLowerCase().replace(/^./, s => s.toUpperCase());
  const distance = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
  const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
  const isPlotId = n => Number.isInteger(n) && n >= 0 && n < 64 && !PLAZA_IDS.has(n);
  const offset = i => 4 + Math.floor(i / 2) * 36 + i % 2 * 16;
  const center = plot => ({ x: (plot.minX + plot.maxX + 1) / 2, z: (plot.minZ + plot.maxZ + 1) / 2 });
  const plotAt = (x, z) => state.plots.find(p => x >= p.minX && x < p.maxX + 1 && z >= p.minZ && z < p.maxZ + 1);

  // Source port of Java SplittableRandom's first bounded draw, using 64-bit wrapping,
  // intended to match DistrictOps.pick. Parity is unverified; no runtime check was run.
  // Illustrations remain visitor renderings, not cube data.
  function openingKind(seed, n) {
    let next = BigInt.asUintN(64, BigInt(seed) * 1000003n + BigInt(n));
    let r;
    do {
      next = BigInt.asUintN(64, next + 0x9e3779b97f4a7c15n);
      let z = BigInt.asUintN(64, (next ^ next >> 33n) * 0x62a9d9ed799705f5n);
      z = BigInt.asUintN(64, (z ^ z >> 28n) * 0xcb24d0a5c88c35b3n);
      const u = Number(z >> 32n) >>> 1;
      r = u % 100;
      if (u + 99 - r <= 0x7fffffff) break;
    } while (true);
    return r < 48 ? "LAWN" : r < 66 ? "GROVE" : r < 78 ? "PAVILION" : r < 88 ? "TOWER" : r < 94 ? "SCULPTURE" : "POND";
  }
  function localPlots(seed) {
    const plots = [];
    for (let n = 0; n < 64; n++) {
      if (!isPlotId(n)) continue;
      const minX = MIN_X + offset(n % 8), minZ = MIN_Z + offset(Math.floor(n / 8));
      plots.push({ n, minX, minZ, maxX: minX + 15, maxZ: minZ + 15, height: MAX_Y,
        show: openingKind(seed, n), owner: "", builders: [] });
    }
    return plots;
  }
  function makeMissions() {
    const pick = (show, fallback) => state.plots.find(p => p.show === show) || state.plots.find(p => p.n === fallback);
    const grove = pick("GROVE", 9), pond = pick("POND", 54), sculpture = pick("SCULPTURE", 14);
    return [
      { title: "The plaza remembers", target: { x: 48, z: -74 }, radius: 8, short: "Hear Neri’s briefing", icon: "01",
        copy: "Meet Neri at the orange helipad. The city kept its streets when the meteor broke the planet.",
        found: "Neri: ‘A Heartstone holds a fragment together. We are listening for its echo, never taking its heart. Follow the gold marker.’" },
      { title: "Roots between the stones", target: center(grove), radius: 10, plot: grove.n, short: `Observe Plot ${grove.n}`, icon: "02",
        copy: `Walk to Plot ${grove.n}. Log how a living patch softens the old city. This is observation, not harvesting.`,
        found: "Echo 1 logged locally: roots have found a way between the stones. A fragment can grow again without forgetting its city." },
      { title: "Water remembers the sky", target: center(pond), radius: 10, plot: pond.n, short: `Read Plot ${pond.n}`, icon: "03",
        copy: `Reach Plot ${pond.n} and read the second echo. Water and life survived the impact in scattered pockets.`,
        found: "Echo 2 logged locally: keep clean water moving. The district will need the arks’ living cargo as much as its buildings." },
      { title: "A pulse through the glass", target: center(sculpture), radius: 10, plot: sculpture.n, short: `Listen at Plot ${sculpture.n}`, icon: "04",
        copy: `Find Plot ${sculpture.n}. The third reading travels through the ground. A crystal scene is a landmark, not a mined Heartstone.`,
        found: "Echo 3 logged locally: the pulse points beneath the district. The Heartstone stays where it belongs; the survey carries only its story." },
      { title: "The northern signal", target: { x: 48, z: -146 }, radius: 6, short: "Reach the north ring road", icon: "05",
        copy: "Walk north to the ring road beacon at X 48 / Z −146. The cloud gate lies beyond walking reach. Buildings stop at Y 32.",
        found: "North beacon logged locally: the rainbow starts above the city. Parcels’ helicopter is the route to the sky gates, once the server links them." },
      { title: "Leave a light for the arks", target: { x: 48, z: -74 }, radius: 8, short: "Return to the helipad", icon: "06",
        copy: "Bring the signal log back to Neri at the helipad. Every fragment needs a place where travelers can find each other.",
        found: "Expedition complete on this device. Neri: ‘The old planet is gone. What grows back is up to us.’ Your survey changes no claims, deeds or server state." }
    ];
  }

  function saveKey() { return `daedalus.parcels.expedition.v${SAVE_VERSION}:${encodeURIComponent(state.worldId || "local")}:${state.seed}`; }
  function save() {
    try {
      localStorage.setItem(saveKey(), JSON.stringify({ version: SAVE_VERSION, seed: state.seed, worldId: state.worldId,
        stage: state.stage, player: { x: state.player.x, z: state.player.z }, visited: [...state.visited], pinned: [...state.pinned], selected: state.selected }));
      state.saveAvailable = true;
      $("saveStatus").textContent = "Local expedition saved on this device. It never changes land ownership.";
    } catch (_) {
      state.saveAvailable = false;
      $("saveStatus").textContent = "Device storage is unavailable. This local expedition lasts for the current page session.";
    }
    state.lastSave = performance.now();
  }
  function restore() {
    state.stage = 0; state.player = { x: 48, z: -74, heading: 0 };
    state.visited = new Set(); state.pinned = new Set(); state.selected = null;
    try {
      const raw = localStorage.getItem(saveKey());
      if (!raw) return;
      if (raw.length > 10000) throw new Error("oversized local save");
      const s = JSON.parse(raw);
      const validIds = list => Array.isArray(list) && list.length <= 60 && list.every(isPlotId) && new Set(list).size === list.length;
      if (!s || s.version !== SAVE_VERSION || s.seed !== state.seed || s.worldId !== state.worldId ||
          !Number.isInteger(s.stage) || s.stage < 0 || s.stage > 6 || !s.player ||
          !Number.isFinite(s.player.x) || !Number.isFinite(s.player.z) || s.player.x < MIN_X + .6 || s.player.x > MIN_X + SIDE - .6 ||
          s.player.z < MIN_Z + .6 || s.player.z > MIN_Z + SIDE - .6 || !validIds(s.visited) || !validIds(s.pinned) ||
          !(s.selected === null || isPlotId(s.selected))) throw new Error("invalid local save");
      state.stage = s.stage; state.player = { x: s.player.x, z: s.player.z, heading: 0 };
      state.visited = new Set(s.visited); state.pinned = new Set(s.pinned); state.selected = s.selected;
    } catch (_) {
      $("saveStatus").textContent = "A local save could not be restored. A fresh visitor expedition has started.";
    }
  }
  function toast(message) {
    clearTimeout(state.toastTimer);
    $("mapToast").textContent = message;
    $("mapToast").classList.add("visible");
    state.toastTimer = setTimeout(() => $("mapToast").classList.remove("visible"), 8500);
  }

  async function getJson(path) {
    const abort = new AbortController(), timeout = setTimeout(() => abort.abort(), 6000);
    try {
      const res = await fetch(path, { signal: abort.signal, credentials: "same-origin", headers: { Accept: "application/json" } });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const raw = await res.text();
      if (raw.length > 2000000) throw new Error("Response too large");
      // Java long seeds must remain exact even past JavaScript's safe integer range.
      return JSON.parse(raw.replace(/("seed"\s*:\s*)(-?\d+)(?=\s*[,}])/g, '$1"$2"'));
    } finally { clearTimeout(timeout); }
  }
  function validatePlots(data, worldId) {
    if (!data || data.worldId !== worldId || data.plotSize !== PLOT_SIZE || data.height !== MAX_Y ||
        data.plazaMinX !== 30 || data.plazaMaxX !== 65 || data.plazaMinZ !== -92 || data.plazaMaxZ !== -57 ||
        data.padX !== 48 || data.padZ !== -74 || !Array.isArray(data.plots) || data.plots.length !== 60) throw new Error("Unexpected district geometry");
    const ids = new Set();
    const rows = data.plots.map(p => {
      if (!p || !isPlotId(p.n) || ids.has(p.n) || p.minX !== MIN_X + offset(p.n % 8) ||
          p.minZ !== MIN_Z + offset(Math.floor(p.n / 8)) || p.maxX !== p.minX + 15 || p.maxZ !== p.minZ + 15 ||
          p.height !== MAX_Y || !SHOWS.includes(p.show) || typeof p.owner !== "string" || p.owner.length > 300 ||
          !Array.isArray(p.builders) || p.builders.length > 1000 || !p.builders.every(b => typeof b === "string" && b.length <= 300)) throw new Error("Unexpected plot row");
      ids.add(p.n); return { ...p, builders: [...p.builders] };
    });
    return rows.sort((a, b) => a.n - b.n);
  }
  function realmUrl() { return state.worldId ? `realm.html?world=${encodeURIComponent(state.worldId)}` : "realm.html"; }
  function syncLinks() {
    for (const id of ["serverRealmLink", "manageLandLink", "travelLink"]) $(id).href = realmUrl();
    const url = new URL(location.href);
    url.searchParams.set("seed", state.seed);
    if (state.worldId) url.searchParams.set("world", state.worldId); else url.searchParams.delete("world");
    try { history.replaceState(null, "", url); } catch (_) { /* file previews may restrict history */ }
  }
  function updateSource() {
    $("connectionStatus").textContent = state.sourceMessage;
    $("connectionDot").classList.toggle("connected", state.mode === "server");
    $("districtMode").textContent = state.mode === "server" ? "SERVER SNAPSHOT" : state.mode === "snapshot" ? "OFFLINE SNAPSHOT" : "LOCAL DRAFT";
    $("districtLabel").textContent = `SEED ${state.seed}`;
    $("seedInput").value = state.seed;
    const live = state.mode === "server", owners = state.plots.filter(p => p.owner).length;
    $("claimStatus").textContent = live ? `Server claims: ${owners} held / ${60 - owners} open` : state.mode === "snapshot" ? "Server claims: previous snapshot" : "Server claims: not connected";
    $("claimDetail").textContent = live
      ? "Owners and builders are a read-only server snapshot. Open plots require a successful server claim before building. Refresh to read changes."
      : state.mode === "snapshot" ? "The previous server district remains available for your local expedition. Its owner and builder records may have changed. Refresh to reconnect."
      : "Local plots are preview geometry with unknown ownership. Connect to an existing Parcels world for authoritative owners.";
    $("manageLandLink").textContent = state.worldId ? "Open this district’s ownership controls ↗" : "Open server realm and create a district ↗";
    $("worldSelect").value = state.worldId;
    syncLinks();
  }
  function setDistrict(seed, worldId, plots, mode, message) {
    clearMovement();
    state.seed = seed; state.worldId = worldId; state.plots = plots; state.mode = mode; state.sourceMessage = message;
    state.missions = makeMissions(); restore(); state.camera = { x: 48, z: -74 };
    updateSource(); updateJournal(); inspect(state.selected); renderDirectory(); updateHud();
    $("helicopterStatus").textContent = "Helicopter status unavailable";
    $("gateStatus").textContent = "No live gate routes loaded.";
  }
  function markSnapshotOffline() {
    state.mode = "snapshot"; state.sourceMessage = "Previous server snapshot · offline";
    updateSource(); inspect(state.selected); renderDirectory();
    $("helicopterStatus").textContent = "Helicopter status: previous snapshot offline";
    $("gateStatus").textContent = "Live gate routes unavailable. Open the server realm to reconnect.";
  }
  async function loadWorld(worldId) {
    const seq = ++state.loadSequence;
    if (!worldId) {
      save(); setDistrict(state.seed, "", localPlots(state.seed), "local", "Local visitor draft"); return;
    }
    const world = state.worlds.find(w => w.id === worldId);
    if (!world) { toast("That world is not a mounted Parcels district."); return; }
    state.connecting = true;
    $("connectionStatus").textContent = "Reading server district…";
    try {
      const data = await getJson(`/api/v1/world/${encodeURIComponent(worldId)}/plots`);
      if (seq !== state.loadSequence) return;
      const plots = validatePlots(data, worldId), seed = seedString(world.seed);
      if (!seed) throw new Error("Invalid server seed");
      save(); setDistrict(seed, worldId, plots, "server", "Connected · read-only");
      toast(`Visiting ${world.title || worldId}. Server plot ownership loaded; your expedition remains local.`);
      readTravel(worldId, seq);
    } catch (_) {
      if (seq !== state.loadSequence) return;
      if (worldId === state.worldId && state.mode === "server") markSnapshotOffline();
      $("worldSelect").value = state.worldId;
      $("connectionStatus").textContent = state.sourceMessage;
      toast("That district could not be read. Your current visitor expedition stays open.");
    } finally { if (seq === state.loadSequence) state.connecting = false; }
  }
  async function readTravel(worldId, seq) {
    const results = await Promise.allSettled([
      getJson(`/api/v1/world/${encodeURIComponent(worldId)}/gates`),
      getJson(`/api/v1/world/${encodeURIComponent(worldId)}/arks`)
    ]);
    if (seq !== state.loadSequence || state.worldId !== worldId) return;
    const [gateResult, arkResult] = results;
    if (gateResult.status === "fulfilled" && Array.isArray(gateResult.value.gates)) {
      const gates = gateResult.value.gates;
      $("gateStatus").textContent = gates.length ? `${gates.length} linked sky gate${gates.length === 1 ? "" : "s"}: ${gates.map(g => String(g.toTitle || g.toWorld || "destination").slice(0, 100)).join(" · ")}` : "No paired sky gates are configured in this district yet.";
    }
    if (arkResult.status === "fulfilled" && Array.isArray(arkResult.value.arks)) {
      const heli = arkResult.value.arks.find(a => a.id === "heli-0");
      if (heli) $("helicopterStatus").textContent = `heli-0 · ${String(heli.state || "status unknown").toLowerCase()}`;
    }
  }
  async function refreshWorlds(requestedId = "") {
    const loadSequence = state.loadSequence;
    $("refreshWorldsButton").disabled = true;
    $("refreshWorldsButton").textContent = "Reading districts…";
    try {
      const data = await getJson("/api/v1/worlds");
      if (!data || !Array.isArray(data.worlds)) throw new Error("Invalid world list");
      state.worlds = data.worlds.filter(w => w && w.style === "PARCELS" && typeof w.id === "string" && /^[\w-]{1,128}$/.test(w.id) && seedString(w.seed));
      const select = $("worldSelect"); select.replaceChildren(new Option("Local visitor draft", ""));
      for (const w of state.worlds) select.appendChild(new Option(String(w.title || w.id), w.id));
      if (state.worldId && !state.worlds.some(w => w.id === state.worldId)) {
        const old = new Option(`${state.worldId} · previous snapshot`, state.worldId);
        old.disabled = true; select.appendChild(old);
      }
      select.value = state.worldId;
      if (loadSequence !== state.loadSequence) return;
      if (requestedId && state.worlds.some(w => w.id === requestedId)) await loadWorld(requestedId);
      else if (requestedId) toast("The requested Parcels world is not mounted. Exploring a local draft instead.");
      else if (state.worldId && state.worlds.some(w => w.id === state.worldId)) await loadWorld(state.worldId);
      else if (state.worldId) {
        ++state.loadSequence;
        markSnapshotOffline();
        toast("This district is no longer listed. Its last plot snapshot is retained for your local expedition; ownership is no longer current.");
      } else toast(state.worlds.length ? `${state.worlds.length} Parcels district${state.worlds.length === 1 ? "" : "s"} available in the land panel.` : "The server has no Parcels district yet. Create one in the server realm; this local draft is playable now.");
    } catch (_) {
      if (loadSequence !== state.loadSequence) return;
      if (state.mode === "server") markSnapshotOffline();
      if (requestedId) toast("Server access is unavailable. The requested world was not connected; this is a local visitor draft.");
      else toast("Server access is unavailable. Continue your local expedition, or refresh when the server is ready.");
    } finally {
      $("refreshWorldsButton").disabled = false; $("refreshWorldsButton").textContent = "Refresh server districts";
    }
  }

  function updateJournal() {
    $("missionCount").textContent = `${state.stage} / 6 signals`;
    $("surveyPercent").textContent = `${Math.round(state.stage / 6 * 100)}%`;
    $("missionProgress").setAttribute("aria-valuenow", state.stage);
    $("missionProgressFill").style.width = `${state.stage / 6 * 100}%`;
    $("missionList").replaceChildren();
    state.missions.forEach((mission, i) => {
      const li = document.createElement("li"); li.className = i < state.stage ? "done" : i === state.stage ? "active" : "";
      const badge = document.createElement("span"); badge.className = "mission-step"; badge.textContent = i < state.stage ? "✓" : mission.icon;
      const text = document.createElement("span"); text.textContent = mission.short; li.append(badge, text); $("missionList").appendChild(li);
    });
    const mission = state.missions[state.stage];
    $("missionTitle").textContent = mission ? mission.title : "A light in the district";
    $("missionCopy").textContent = mission ? mission.copy : "Your local survey is complete. Keep exploring, pin a favorite plot, or take the helicopter through a configured gate in the server realm.";
    $("waypointButton").disabled = !mission;
    $("visitedCount").textContent = state.visited.size;
    $("echoCount").textContent = clamp(state.stage - 1, 0, 3);
  }
  function inspect(n) {
    const plot = state.plots.find(p => p.n === n);
    state.selected = plot ? plot.n : null;
    if (!plot) {
      $("plotTitle").textContent = "Heart plaza";
      $("plotDescription").textContent = "The four heart plots became a public square. Nobody claims the plaza or its streets.";
      $("plotBadge").textContent = "PUBLIC"; $("plotFootprint").textContent = "36 × 36 cubes";
      $("plotShow").textContent = "Paving + helipad"; $("plotOwner").textContent = "Public district";
      $("plotHeight").textContent = "No plot building"; $("plotBuilders").textContent = "—";
      $("pinPlotButton").disabled = true; $("pinPlotButton").textContent = "Pin a plot to your journal";
      $("plotPinNote").textContent = "Select a plot on the map or in the directory below.";
    } else {
      const lore = { LAWN: "A quiet patch of surviving ground. An owner's next idea could start here.", GROVE: "A small stand of trees, breathing between the old streets. Observe its life; leave its roots intact.", PAVILION: "Glass catches the light above an open meeting place. Travelers need places to exchange more than cargo.", TOWER: "Stone and glass rise toward the clouds. The ceiling leaves the sky gates safely beyond the buildings.", SCULPTURE: "A crystal landmark catches the fragment's light. The real Heartstone remains deep in the land.", POND: "A pocket of water survived the impact. The arks bring life; the district must give it somewhere to live." };
      $("plotTitle").textContent = `Plot ${plot.n}`; $("plotDescription").textContent = lore[plot.show];
      $("plotBadge").textContent = state.mode === "server" ? (plot.owner ? "HELD" : "OPEN") : state.mode === "snapshot" ? "OLD SNAPSHOT" : "PREVIEW";
      $("plotFootprint").textContent = `X ${plot.minX}…${plot.maxX} / Z ${plot.minZ}…${plot.maxZ}`;
      $("plotShow").textContent = `${nice(plot.show)} · opening scene`;
      $("plotOwner").textContent = state.mode === "server" ? (plot.owner || "Unclaimed on server") : state.mode === "snapshot" ? `${plot.owner || "Unclaimed"} (last snapshot)` : "Unknown · local preview";
      $("plotHeight").textContent = "Y 0…32 · 16 × 16 cubes";
      $("plotBuilders").textContent = state.mode === "local" ? "Unknown · local preview" : plot.builders.length ? plot.builders.join(", ") : "None in snapshot";
      $("pinPlotButton").disabled = false; $("pinPlotButton").textContent = state.pinned.has(plot.n) ? "Unpin this local note" : "Pin a plot to your journal";
      $("plotPinNote").textContent = `Local waypoint: X ${center(plot).x} / Z ${center(plot).z}. Pinning never reserves or claims land.`;
    }
    document.querySelectorAll(".directory-plot").forEach(button => button.classList.toggle("selected", Number(button.dataset.plot) === state.selected && state.selected !== null));
  }
  function renderDirectory() {
    const filter = $("plotFilter").value;
    const plots = state.plots.filter(p => filter === "all" || filter === "pinned" && state.pinned.has(p.n) || filter === "visited" && state.visited.has(p.n) || p.show === filter);
    const fragment = document.createDocumentFragment();
    for (const p of plots) {
      const button = document.createElement("button"); button.type = "button"; button.dataset.plot = p.n;
      button.className = `directory-plot${p.n === state.selected ? " selected" : ""}${state.visited.has(p.n) ? " observed" : ""}${state.pinned.has(p.n) ? " pinned" : ""}${state.mode === "server" && p.owner ? " owned" : ""}`;
      button.setAttribute("aria-label", `Inspect Plot ${p.n}, ${nice(p.show)}, ${state.mode === "server" ? p.owner ? "held on server" : "unclaimed on server" : "ownership unknown"}`);
      const number = document.createElement("strong"); number.textContent = `Plot ${p.n}`;
      const show = document.createElement("span"); show.textContent = nice(p.show);
      button.append(number, show); button.addEventListener("click", () => { inspect(p.n); save(); toast(`Plot ${p.n} selected. Walk to X ${center(p).x}, Z ${center(p).z} to observe it.`); });
      fragment.appendChild(button);
    }
    if (!plots.length) { const empty = document.createElement("p"); empty.className = "compact"; empty.textContent = "No plots match this view yet."; fragment.appendChild(empty); }
    $("plotDirectory").replaceChildren(fragment); $("directoryCount").textContent = `${plots.length} plot${plots.length === 1 ? "" : "s"}`;
  }
  function updateHud() {
    const plot = plotAt(state.player.x, state.player.z), mission = state.missions[state.stage];
    $("coordinates").textContent = `X ${Math.round(state.player.x)} / Z ${Math.round(state.player.z)}`;
    const inPlaza = state.player.x >= 30 && state.player.x < 66 && state.player.z >= -92 && state.player.z < -56;
    $("locationLabel").textContent = plot ? `PLOT ${plot.n} · ${plot.show}` : inPlaza ? "PUBLIC PLAZA" : "PUBLIC STREET";
    const near = mission && distance(state.player, mission.target) <= mission.radius;
    $("interactButton").disabled = !near;
    $("interactButton").innerHTML = `<span class="keycap">E</span> ${mission ? "Survey checkpoint" : "Survey complete"}`;
    $("interactHint").textContent = mission ? near ? `${mission.title} · Ready to log.` : `${Math.round(distance(state.player, mission.target))} cubes to ${mission.title.toLowerCase()}. Follow the gold marker.` : "Local expedition complete. The district is still yours to explore.";
  }
  function interact() {
    const mission = state.missions[state.stage];
    if (!mission || distance(state.player, mission.target) > mission.radius) return;
    if (mission.plot !== undefined) state.visited.add(mission.plot);
    state.stage++; updateJournal(); updateHud(); renderDirectory(); save(); toast(mission.found);
  }

  function viewPoint(x, z) { return { x: (x - state.camera.x) * state.scale + state.width / 2, y: (z - state.camera.z) * state.scale + state.height / 2 - 8 }; }
  function worldPoint(x, y) { return { x: (x - state.width / 2) / state.scale + state.camera.x, z: (y - state.height / 2 + 8) / state.scale + state.camera.z }; }
  function rectangle(x, z, w, h, color, outline) {
    const p = viewPoint(x, z); ctx.fillStyle = color; ctx.fillRect(p.x, p.y, w * state.scale, h * state.scale);
    if (outline) { ctx.strokeStyle = outline; ctx.lineWidth = 1; ctx.strokeRect(p.x + .5, p.y + .5, w * state.scale - 1, h * state.scale - 1); }
  }
  function disk(x, z, radius, color) {
    const p = viewPoint(x, z); ctx.fillStyle = color; ctx.beginPath(); ctx.arc(p.x, p.y, radius * state.scale, 0, Math.PI * 2); ctx.fill();
  }
  function line(points, color, width = 1) {
    ctx.beginPath(); points.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.strokeStyle = color; ctx.lineWidth = width; ctx.stroke();
  }
  function label(x, z, text, size, color, align = "center") {
    const p = viewPoint(x, z); ctx.font = `${size}px ui-sans-serif,system-ui,sans-serif`; ctx.textAlign = align; ctx.fillStyle = color; ctx.fillText(text, p.x, p.y);
  }
  function drawGround() {
    const p = viewPoint(MIN_X, MIN_Z), s = state.scale, size = SIDE * s;
    ctx.shadowColor = "#041827aa"; ctx.shadowBlur = 30; ctx.shadowOffsetY = 15;
    ctx.fillStyle = "#2b4c48"; ctx.fillRect(p.x, p.y, size, size + 7 * s); ctx.shadowBlur = 0; ctx.shadowOffsetY = 0;
    ctx.fillStyle = "#325b4e"; ctx.fillRect(p.x, p.y + size, size, 4 * s);
    ctx.fillStyle = "#223e40"; ctx.fillRect(p.x, p.y + size + 4 * s, size, 3 * s);
    ctx.fillStyle = "#293a3b"; ctx.fillRect(p.x, p.y, size, size);
    for (const d of [0, 36, 72, 108, 144]) {
      rectangle(MIN_X + d, MIN_Z, 1, SIDE, "#879b87");
      rectangle(MIN_X + d + 3, MIN_Z, 1, SIDE, "#879b87");
      rectangle(MIN_X, MIN_Z + d, SIDE, 1, "#879b87");
      rectangle(MIN_X, MIN_Z + d + 3, SIDE, 1, "#879b87");
      ctx.setLineDash([2 * s, 3 * s]);
      const a = viewPoint(MIN_X + d + 2, MIN_Z), b = viewPoint(MIN_X + d + 2, MIN_Z + SIDE);
      line([[a.x, a.y], [b.x, b.y]], "#b5bd9760", .7);
      const c = viewPoint(MIN_X, MIN_Z + d + 2), e = viewPoint(MIN_X + SIDE, MIN_Z + d + 2);
      line([[c.x, c.y], [e.x, e.y]], "#b5bd9760", .7); ctx.setLineDash([]);
    }
    for (const plot of state.plots) {
      const tint = state.mode === "server" && plot.owner ? "#89996b" : ["#73a886", "#6ea17d", "#80ac84", "#6fa18e"][plot.n % 4];
      rectangle(plot.minX, plot.minZ, 16, 16, tint, "#5d957866");
      if (state.visited.has(plot.n)) rectangle(plot.minX + .6, plot.maxZ -.2, 2, .55, "#b9ead0");
      if (state.pinned.has(plot.n)) {
        const pos = viewPoint(plot.maxX - 1, plot.minZ + 2); ctx.fillStyle = "#f7c377"; ctx.beginPath();
        ctx.moveTo(pos.x, pos.y - 3); ctx.lineTo(pos.x + 3, pos.y); ctx.lineTo(pos.x, pos.y + 3); ctx.lineTo(pos.x - 3, pos.y); ctx.closePath(); ctx.fill();
      }
    }
    rectangle(30, -92, 36, 36, "#b4c1a4");
    for (let d = 3; d < 36; d += 3) {
      rectangle(30 + d, -92, .12, 36, "#9bab9655"); rectangle(30, -92 + d, 36, .12, "#9bab9655");
    }
    rectangle(43, -79, 10, 10, "#d79353");
    rectangle(45, -77, .8, 6, "#f1e3bb"); rectangle(50, -77, .8, 6, "#f1e3bb"); rectangle(45, -74.5, 5.8, 1, "#f1e3bb");
    for (const [x, z] of [[33, -89], [63, -89], [33, -59], [63, -59]]) { disk(x, z, 1.6, "#597d59"); disk(x -.3, z -.4, 1.3, "#76a36c"); }
    label(48, -60, "HEART PLAZA", Math.max(6, 3 * s), "#3d6155");
    label(48, -153, "NORTH RING / SKY GATE LINE", Math.max(7, 2.7 * s), "#94d3c2");
    for (const d of [0, 36, 108, 144]) {
      for (const e of [18, 54, 90, 126]) {
        disk(MIN_X + d + 1, MIN_Z + e, .25, "#e9e0ac"); disk(MIN_X + e, MIN_Z + d + 1, .25, "#e9e0ac");
      }
    }
  }
  function drawTree(x, z, variant) {
    disk(x + .7, z + .7, 1.8, "#163d4350"); rectangle(x -.2, z, .4, 1.3, "#675c40");
    disk(x, z -.5, 1.9, variant ? "#c59ca0" : "#3a7860");
    disk(x -.45, z -1.15, 1.35, variant ? "#e3b5ad" : "#66a47c");
    disk(x + .5, z -1.15, .8, variant ? "#ecc6b0" : "#83b888");
  }
  function drawBuilding(x, z, w, d, height, roof, walls) {
    const base = viewPoint(x - w / 2, z - d / 2), s = state.scale, h = height * s * .26;
    ctx.fillStyle = "#193d3f40"; ctx.fillRect(base.x + w * s * .3, base.y + 2 * s, w * s, d * s);
    ctx.fillStyle = walls; ctx.fillRect(base.x, base.y - h, w * s, d * s + h);
    ctx.fillStyle = "#577978"; ctx.fillRect(base.x, base.y + d * s - h, w * s, h);
    ctx.fillStyle = roof; ctx.fillRect(base.x, base.y - h, w * s, d * s);
    ctx.strokeStyle = "#d6efe255"; ctx.lineWidth = .7; ctx.strokeRect(base.x + .5, base.y - h + .5, w * s -1, d * s -1);
    if (height > 8) for (let i = 2; i < height * .26; i += 1.4) {
      ctx.fillStyle = "#b8e2cfb0"; ctx.fillRect(base.x + s, base.y + d * s - h + i * s, (w - 2) * s, .45 * s);
    }
  }
  function drawPlots() {
    for (const plot of state.plots) {
      const c = center(plot), s = state.scale;
      switch (plot.show) {
        case "GROVE":
          [[-3, -2], [3, -2], [-2, 3], [3, 3]].forEach(([x, z], i) => drawTree(c.x + x, c.z + z, (plot.n + i) % 4 === 0)); break;
        case "PAVILION":
          rectangle(c.x - 5, c.z - 5, 10, 10, "#a9b99d");
          drawBuilding(c.x, c.z, 9, 9, 5, "#b4d8d4a6", "#815f43");
          for (const d of [-4, 0, 4]) rectangle(c.x + d, c.z - 4.5, .2, 8, "#e0e4b860"); break;
        case "TOWER": drawBuilding(c.x, c.z, 7, 7, 14 + plot.n % 12, "#c3d6cc", "#90b5b1"); break;
        case "SCULPTURE": {
          disk(c.x, c.z, 3, "#aabdad"); const p = viewPoint(c.x, c.z); const rise = (8 + plot.n % 10) * s * .3;
          ctx.beginPath(); ctx.moveTo(p.x, p.y - rise); ctx.lineTo(p.x + 2.2*s, p.y - s); ctx.lineTo(p.x, p.y + s); ctx.lineTo(p.x - 2.2*s, p.y - s); ctx.closePath(); ctx.fillStyle = "#b9f2e1"; ctx.fill();
          ctx.beginPath(); ctx.moveTo(p.x, p.y - rise); ctx.lineTo(p.x, p.y + s); ctx.lineTo(p.x - 2.2*s, p.y - s); ctx.closePath(); ctx.fillStyle = "#69bbaf"; ctx.fill(); break;
        }
        case "POND": {
          const p = viewPoint(c.x, c.z); ctx.beginPath(); ctx.ellipse(p.x, p.y, 4.6*s, 3.6*s, 0, 0, Math.PI*2); ctx.fillStyle = "#d3bd81"; ctx.fill();
          ctx.beginPath(); ctx.ellipse(p.x, p.y, 3.7*s, 2.7*s, 0, 0, Math.PI*2); ctx.fillStyle = "#508f9f"; ctx.fill();
          line([[p.x - 2*s, p.y - .7*s], [p.x + 1.8*s, p.y - .7*s]], "#9bdbd080", .8); drawTree(c.x + 5, c.z + 4, false); break;
        }
        default:
          for (let i = 0; i < 3; i++) disk(plot.minX + 3 + (plot.n * 7 + i * 3) % 11, plot.minZ + 3 + (plot.n * 3 + i * 7) % 11, .32, "#e9bdba");
      }
      const p = viewPoint(plot.minX + 1.3, plot.maxZ - .7);
      ctx.font = `${Math.max(5, 2.5*s)}px ui-sans-serif,system-ui`; ctx.textAlign = "left"; ctx.fillStyle = "#294c3ca8"; ctx.fillText(String(plot.n).padStart(2, "0"), p.x, p.y);
      if (state.selected === plot.n) {
        const q = viewPoint(plot.minX, plot.minZ); ctx.strokeStyle = "#ffe3a3"; ctx.lineWidth = 2; ctx.strokeRect(q.x + 1, q.y + 1, 16*s -2, 16*s -2);
      }
    }
  }
  function drawHelicopter() {
    const p = viewPoint(48, -74), s = state.scale;
    // Schematic heli is always a visitor illustration; the server status panel is authoritative.
    ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(-.1); ctx.fillStyle = "#1d475955";
    ctx.beginPath(); ctx.ellipse(2*s, 2*s, 4.8*s, 2.4*s, 0, 0, Math.PI*2); ctx.fill();
    ctx.fillStyle = "#244d57"; ctx.fillRect(-.65*s, -5*s, 1.3*s, 5*s);
    ctx.fillStyle = "#d7e2c4"; ctx.fillRect(-2*s, -1.5*s, 4*s, 4*s);
    ctx.fillStyle = "#477c89"; ctx.fillRect(-1.6*s, 1*s, 3.2*s, 1.7*s);
    ctx.strokeStyle = "#f4dfb3"; ctx.lineWidth = Math.max(1, .22*s); ctx.beginPath(); ctx.moveTo(-2.5*s,-1.5*s);ctx.lineTo(-2.5*s,3*s);ctx.moveTo(2.5*s,-1.5*s);ctx.lineTo(2.5*s,3*s);ctx.stroke();
    ctx.save(); ctx.rotate(prefersReducedMotion ? .6 : state.time * 2.5); ctx.fillStyle = "#eef0daaa"; ctx.fillRect(-5*s, -.25*s, 10*s, .5*s); ctx.fillRect(-.25*s, -5*s, .5*s, 10*s); ctx.restore(); ctx.restore();
    const neri = viewPoint(55, -74); ctx.fillStyle = "#dfac73"; ctx.beginPath();ctx.arc(neri.x,neri.y,Math.max(2,.7*s),0,Math.PI*2);ctx.fill(); label(55,-71.4,"NERI",Math.max(6,2*s),"#496859");
  }
  function drawSignals() {
    const mission = state.missions[state.stage], s = state.scale;
    for (let i = 0; i < state.stage; i++) {
      const m = state.missions[i]; if (i === 0 || i === 5) continue;
      const p = viewPoint(m.target.x, m.target.z); ctx.strokeStyle = "#b8ebc5"; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(p.x, p.y, 2*s, 0, Math.PI*2);ctx.stroke();
    }
    if (mission) {
      const p = viewPoint(mission.target.x, mission.target.z), pulse = prefersReducedMotion ? 0 : Math.sin(state.time * 3) * 1.8;
      ctx.fillStyle = "#f5c96a33"; ctx.beginPath();ctx.arc(p.x,p.y,(mission.radius*.65)*s+pulse,0,Math.PI*2);ctx.fill();
      ctx.strokeStyle = "#ffda89"; ctx.lineWidth = 1.3;ctx.beginPath();ctx.arc(p.x,p.y,3.6*s+pulse,0,Math.PI*2);ctx.stroke();
      ctx.fillStyle = "#f8d580";ctx.beginPath();ctx.moveTo(p.x,p.y-8*s);ctx.lineTo(p.x+1.7*s,p.y-5*s);ctx.lineTo(p.x,p.y-3.6*s);ctx.lineTo(p.x-1.7*s,p.y-5*s);ctx.closePath();ctx.fill();
      if (p.x < 25 || p.x > state.width-25 || p.y < 35 || p.y > state.height-105) {
        const edgeX = clamp(p.x, 26, state.width-26), edgeY = clamp(p.y, 90, state.height-114);
        ctx.save();ctx.translate(edgeX,edgeY);ctx.rotate(Math.atan2(p.y-edgeY,p.x-edgeX));ctx.fillStyle="#fbd584";ctx.beginPath();ctx.moveTo(7,0);ctx.lineTo(-5,-5);ctx.lineTo(-5,5);ctx.closePath();ctx.fill();ctx.restore();
      }
    }
    // The north beacon is a local narrative overlay, never a world cube write.
    disk(48,-146,1,"#ebc688");
  }
  function drawPlayer() {
    const p = viewPoint(state.player.x,state.player.z), s = state.scale;
    ctx.fillStyle = "#183f4b66";ctx.beginPath();ctx.ellipse(p.x+1,p.y+2,Math.max(3,1.2*s),Math.max(2,.65*s),0,0,Math.PI*2);ctx.fill();
    ctx.strokeStyle = "#ffffdd";ctx.lineWidth = 1.5;ctx.fillStyle = "#193a58";ctx.beginPath();ctx.arc(p.x,p.y,Math.max(3,1.05*s),0,Math.PI*2);ctx.fill();ctx.stroke();
    ctx.fillStyle = "#9ae1ce";ctx.beginPath();ctx.arc(p.x,p.y-1,Math.max(1.5,.5*s),0,Math.PI*2);ctx.fill();
    ctx.save();ctx.translate(p.x,p.y);ctx.rotate(state.player.heading);ctx.fillStyle="#eaeecb";ctx.beginPath();ctx.moveTo(0,-Math.max(7,2.4*s));ctx.lineTo(-3,-Math.max(4,1.4*s));ctx.lineTo(3,-Math.max(4,1.4*s));ctx.closePath();ctx.fill();ctx.restore();
  }
  function draw() {
    if (!ctx) return;
    const dpr = Math.min(devicePixelRatio || 1, 2); ctx.setTransform(dpr,0,0,dpr,0,0);
    const w=state.width,h=state.height;
    const sky = ctx.createLinearGradient(0,0,w,h);sky.addColorStop(0,"#164e50");sky.addColorStop(.6,"#16404b");sky.addColorStop(1,"#102c41");ctx.fillStyle=sky;ctx.fillRect(0,0,w,h);
    for(let i=0;i<35;i++) { const x=(i*137.3+39)%w,y=(i*91.7+27)%h;ctx.fillStyle=i%3?"#b3e0d224":"#b3e0d244";ctx.fillRect(x,y,1,1); }
    ctx.strokeStyle="#81adab15";ctx.lineWidth=1;ctx.beginPath();ctx.ellipse(w*.5,h*.52,w*.49,h*.48,-.1,0,Math.PI*2);ctx.stroke();
    state.scale = Math.min(w/183,h/188)*state.zoom;
    if (state.overview) { state.camera.x=48;state.camera.z=-74; } else { state.camera.x=state.player.x;state.camera.z=state.player.z; }
    drawGround();drawPlots();drawHelicopter();drawSignals();drawPlayer();
  }
  function resize() {
    const box = $("canvasWrap").getBoundingClientRect(), dpr = Math.min(devicePixelRatio || 1,2);
    state.width = Math.max(1,box.width);state.height = Math.max(1,box.height);canvas.width=Math.round(state.width*dpr);canvas.height=Math.round(state.height*dpr);draw();
  }
  function frame(now) {
    const delta = Math.min((now - (state.previousFrame || now))/1000,.05);state.previousFrame=now;state.time=now/1000;
    const held = direction => [...touchDirections.values()].includes(direction);
    let dx=(keys.has("d")||keys.has("arrowright")||held("right")?1:0)-(keys.has("a")||keys.has("arrowleft")||held("left")?1:0);
    let dz=(keys.has("s")||keys.has("arrowdown")||held("down")?1:0)-(keys.has("w")||keys.has("arrowup")||held("up")?1:0);
    if(dx||dz) {
      const norm=Math.hypot(dx,dz),speed=keys.has("shift")?27:16;
      state.player.x=clamp(state.player.x+dx/norm*speed*delta,MIN_X+.6,MIN_X+SIDE-.6);
      state.player.z=clamp(state.player.z+dz/norm*speed*delta,MIN_Z+.6,MIN_Z+SIDE-.6);
      state.player.heading=Math.atan2(dx,-dz);
      const p=plotAt(state.player.x,state.player.z);
      if(p&&!state.visited.has(p.n)) {state.visited.add(p.n);updateJournal();renderDirectory();}
      if(now-state.lastSave>5000)save();
    }
    if(now-(state.lastHud||0)>140){state.lastHud=now;updateHud();}
    draw();requestAnimationFrame(frame);
  }
  function zoom(by) {
    state.zoom=clamp(state.zoom+by,1,3);state.overview=state.zoom===1;
    $("overviewButton").setAttribute("aria-pressed",state.overview);draw();
  }
  function clearMovement() {
    keys.clear();touchDirections.clear();document.querySelectorAll("[data-move]").forEach(b=>b.classList.remove("is-down"));
  }
  $("districtForm").addEventListener("submit",event=>{
    event.preventDefault();const seed=seedString($("seedInput").value);
    if(!seed){toast("Use an integer seed from −9223372036854775808 to 9223372036854775807.");return;}
    ++state.loadSequence;save();setDistrict(seed,"",localPlots(seed),"local","Local visitor draft");
    toast("A local district draft is open. Connect to a mounted world for server owners.");
  });
  $("worldSelect").addEventListener("change",()=>loadWorld($("worldSelect").value));
  $("refreshWorldsButton").addEventListener("click",()=>refreshWorlds());
  $("plotFilter").addEventListener("change",renderDirectory);
  $("pinPlotButton").addEventListener("click",()=>{
    if(state.selected===null)return;
    if(state.pinned.has(state.selected))state.pinned.delete(state.selected);else state.pinned.add(state.selected);
    inspect(state.selected);renderDirectory();save();
  });
  $("resetProgressButton").addEventListener("click",()=>{
    clearMovement();state.stage=0;state.visited.clear();state.pinned.clear();state.player={x:48,z:-74,heading:0};
    updateJournal();updateHud();inspect(state.selected);renderDirectory();save();toast("This seed’s local expedition has restarted at Neri’s helipad.");
  });
  $("interactButton").addEventListener("click",interact);
  $("waypointButton").addEventListener("click",()=>{
    state.zoom=1;state.overview=true;$("overviewButton").setAttribute("aria-pressed","true");
    const m=state.missions[state.stage];if(m)toast(`Checkpoint: X ${m.target.x} / Z ${m.target.z}. Walk to the gold signal and press E.`);canvas.focus({preventScroll:true});
  });
  $("zoomInButton").addEventListener("click",()=>zoom(.4));$("zoomOutButton").addEventListener("click",()=>zoom(-.4));
  $("overviewButton").addEventListener("click",()=>{state.overview=!state.overview;state.zoom=state.overview?1:2;$("overviewButton").setAttribute("aria-pressed",state.overview);canvas.focus({preventScroll:true});});
  window.addEventListener("keydown",event=>{
    if(event.target instanceof HTMLElement && (event.target.isContentEditable || /^(INPUT|SELECT|TEXTAREA)$/.test(event.target.tagName)))return;
    const key=event.key.toLowerCase();
    if(["w","a","s","d","arrowup","arrowdown","arrowleft","arrowright","shift","e"].includes(key)){
      event.preventDefault();keys.add(key);if(key==="e"&&!event.repeat)interact();
    }
  });
  window.addEventListener("keyup",event=>keys.delete(event.key.toLowerCase()));
  window.addEventListener("blur",()=>{clearMovement();save();});
  document.addEventListener("visibilitychange",()=>{if(document.hidden){clearMovement();save();}});
  window.addEventListener("pagehide",save);
  for(const button of document.querySelectorAll("[data-move]")){
    button.addEventListener("pointerdown",event=>{event.preventDefault();button.setPointerCapture(event.pointerId);touchDirections.set(event.pointerId,button.dataset.move);button.classList.add("is-down");});
    const release=event=>{touchDirections.delete(event.pointerId);button.classList.remove("is-down");};
    button.addEventListener("pointerup",release);button.addEventListener("pointercancel",release);button.addEventListener("lostpointercapture",release);
  }
  canvas.addEventListener("pointerdown",event=>{state.pointerDown={x:event.clientX,y:event.clientY};canvas.focus({preventScroll:true});});
  canvas.addEventListener("pointerup",event=>{
    if(!state.pointerDown||Math.hypot(event.clientX-state.pointerDown.x,event.clientY-state.pointerDown.y)>15){state.pointerDown=null;return;}
    state.pointerDown=null;const rect=canvas.getBoundingClientRect(),point=worldPoint(event.clientX-rect.left,event.clientY-rect.top),plot=plotAt(point.x,point.z);
    if(plot){inspect(plot.n);save();}else if(point.x>=30&&point.x<66&&point.z>=-92&&point.z< -56){inspect(null);save();}
  });
  canvas.addEventListener("pointercancel",()=>{state.pointerDown=null;});
  canvas.addEventListener("wheel",event=>{event.preventDefault();zoom(event.deltaY < 0 ? .2 : -.2);},{passive:false});
  window.addEventListener("resize",resize);
  if(typeof ResizeObserver!=="undefined")new ResizeObserver(resize).observe($("canvasWrap"));
  const params=new URLSearchParams(location.search),seed=seedString(params.get("seed")||DEFAULT_SEED)||DEFAULT_SEED;
  const requestedWorld=params.get("world")||"";
  setDistrict(seed,"",localPlots(seed),"local","Local visitor draft");resize();
  if(!ctx)toast("Canvas is unavailable in this browser. Use the plot directory to inspect the district.");
  requestAnimationFrame(frame);refreshWorlds(requestedWorld);
})();
