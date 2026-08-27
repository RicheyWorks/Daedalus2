// SPDX-License-Identifier: MIT
// Canvas painter. app.js builds a scene object; this file does not read `state`.
"use strict";
(function (global) {
  const COLORS = {
    wall: "#0b0f14", wallWarm: "#2a2218", unseen: "#05070a",
    floor: "#3d4a58", floorHi: "#536272", floorDim: "#2a333c",
    floorWarm: "#5c4a32",
    start: "#3ee08f", goal: "#ff5a5f", path: "#8fb8ff",
    ghost: "#e6edf3",
  };
  const PLAYER_COLORS = ["#f5c14a", "#ff8fa3", "#9ecbff", "#7ce2b3"];
  /** Overlay legend sits on the well — reserve so the last row is not under the key. */
  const LEGEND_RESERVE = 40;
  /** Show ASCII / PNG sit on the well — reserve so the first row is not under them. */
  const EXPORT_RESERVE = 28;

  function stageBox(canvas) {
    const wrap = canvas.parentElement;
    const w = wrap && wrap.clientWidth ? wrap.clientWidth : 880;
    const h = wrap && wrap.clientHeight ? wrap.clientHeight : 640;
    return { w: Math.max(80, w), h: Math.max(80, h) };
  }

  function computeGeometry(tiles, availW, availH, dprOverride) {
    const th = tiles.length, tw = tiles[0].length;
    const cols = (tw - 1) / 2;
    const rows = (th - 1) / 2;
    const cssW = Math.max(80, availW || 880);
    const cssH = Math.max(80, availH || 640);
    const cellByW = Math.floor(cssW / (cols * 1.25 + 0.25));
    const cellByH = Math.floor(cssH / (rows * 1.25 + 0.25));
    // No 42px ceiling — desktop Layout.fit already grows to the pane.
    // A small maze on a wide stage used to sit in a puddle of void.
    const cellCss = Math.max(6, Math.min(cellByW, cellByH));
    const wallCss = Math.max(2, Math.round(cellCss / 4));
    const dpr = dprOverride != null
        ? dprOverride
        : ((typeof window !== "undefined" && window.devicePixelRatio) || 1);
    const cell = Math.max(1, Math.round(cellCss * dpr));
    const wall = Math.max(1, Math.round(wallCss * dpr));
    const track = n => {
      const off = new Array(n + 1);
      off[0] = 0;
      for (let i = 0; i < n; i++) off[i + 1] = off[i] + (i % 2 === 0 ? wall : cell);
      return off;
    };
    const offX = track(tw), offY = track(th);
    return { offX, offY, cell, wall, dpr, cssW: offX[tw] / dpr, cssH: offY[th] / dpr };
  }

  function isRock(tiles, r, c) {
    return tiles[r - 1][c] === "#" && tiles[r + 1][c] === "#"
        && tiles[r][c - 1] === "#" && tiles[r][c + 1] === "#"
        && tiles[r][c] !== "S" && tiles[r][c] !== "G";
  }

  function isInteriorPost(tiles, r, c) {
    return r > 0 && c > 0 && r < tiles.length - 1 && c < tiles[0].length - 1
        && tiles[r - 1][c] !== "#" && tiles[r + 1][c] !== "#"
        && tiles[r][c - 1] !== "#" && tiles[r][c + 1] !== "#";
  }

  function cellCenter(geom, p) {
    return [geom.offX[2 * p.col + 1] + geom.cell / 2,
            geom.offY[2 * p.row + 1] + geom.cell / 2];
  }

  /**
   * Paint a 4-walk: stood-on cells and the openings between them. A polyline through
   * cell centers is wider than a passage (lineWidth 0.4·cell vs wall 0.25·cell) and
   * cuts the corner post at every turn — wall-follower and Trémaux looked like they
   * walked through walls. Desktop already paints connector tiles; this matches that.
   * A non-adjacent pair is a teleport: we refuse the chord rather than draw through a wall.
   */
  function paintWalk(g, geom, points, color, progress, alpha) {
    if (!points || !points.length || progress <= 0) return;
    const visible = Math.max(1, Math.ceil(points.length * Math.min(1, progress)));
    g.fillStyle = color;
    g.globalAlpha = alpha == null ? 0.85 : alpha;
    for (let i = 0; i < visible; i++) {
      const p = points[i];
      g.fillRect(geom.offX[2 * p.col + 1], geom.offY[2 * p.row + 1], geom.cell, geom.cell);
      if (i === 0) continue;
      const prev = points[i - 1];
      if (Math.abs(p.row - prev.row) + Math.abs(p.col - prev.col) !== 1) continue;
      const tr = prev.row + p.row + 1, tc = prev.col + p.col + 1;
      g.fillRect(geom.offX[tc], geom.offY[tr],
                 geom.offX[tc + 1] - geom.offX[tc],
                 geom.offY[tr + 1] - geom.offY[tr]);
    }
    g.globalAlpha = 1;
  }

  function walkHead(points, progress) {
    if (!points || !points.length || progress <= 0) return null;
    return points[Math.min(points.length, Math.max(1,
        Math.ceil(points.length * Math.min(1, progress)))) - 1];
  }

  function marker(g, geom, p, color, radius) {
    const [x, y] = cellCenter(geom, p);
    g.fillStyle = color;
    g.globalAlpha = 0.22;
    g.beginPath();
    g.arc(x, y, geom.cell * (radius + 0.22), 0, 2 * Math.PI);
    g.fill();
    g.globalAlpha = 1;
    g.beginPath();
    g.arc(x, y, geom.cell * radius, 0, 2 * Math.PI);
    g.fill();
    g.strokeStyle = color;
    g.globalAlpha = 0.65;
    g.lineWidth = Math.max(1, geom.cell * 0.07);
    g.beginPath();
    g.arc(x, y, geom.cell * radius, 0, 2 * Math.PI);
    g.stroke();
    g.globalAlpha = 1;
  }

  /** Recorded racer — soft glow + rim like a walker, translucent core so it stays a ghost. */
  function ghostDisc(g, geom, p) {
    if (!p) return;
    const [x, y] = cellCenter(geom, p);
    const r = geom.cell * 0.3;
    g.fillStyle = COLORS.ghost;
    g.globalAlpha = 0.18;
    g.beginPath();
    g.arc(x, y, r + geom.cell * 0.18, 0, 2 * Math.PI);
    g.fill();
    g.globalAlpha = 0.55;
    g.beginPath();
    g.arc(x, y, r, 0, 2 * Math.PI);
    g.fill();
    g.strokeStyle = COLORS.ghost;
    g.globalAlpha = 0.65;
    g.lineWidth = Math.max(1, geom.cell * 0.07);
    g.beginPath();
    g.arc(x, y, r, 0, 2 * Math.PI);
    g.stroke();
    g.globalAlpha = 1;
  }

  /** Start / goal: disc plus a wider ring so the ends of the maze read as places. */
  function endpoint(g, geom, p, color) {
    if (!p) return;
    marker(g, geom, p, color, 0.34);
    const [x, y] = cellCenter(geom, p);
    g.strokeStyle = color;
    g.globalAlpha = 0.42;
    g.lineWidth = Math.max(1.5, geom.cell * 0.09);
    g.beginPath();
    g.arc(x, y, geom.cell * 0.55, 0, 2 * Math.PI);
    g.stroke();
    g.globalAlpha = 1;
  }

  /** Tip of an unfolding route — soft halo so the head is not just another cell. */
  function pathHead(g, geom, p, color) {
    if (!p) return;
    const [x, y] = cellCenter(geom, p);
    g.strokeStyle = color;
    g.globalAlpha = 0.38;
    g.lineWidth = Math.max(1.5, geom.cell * 0.1);
    g.beginPath();
    g.arc(x, y, geom.cell * 0.5, 0, 2 * Math.PI);
    g.stroke();
    g.globalAlpha = 1;
    marker(g, geom, p, color, 0.3);
  }

  function seenCell(fog, r, c) {
    return !!(fog && fog.seen && fog.seen.has(r + "," + c));
  }

  /** Memory of stood-on cells, plus the wall segments that touch them. Unseen stays void. */
  function fogRevealsTile(fog, tr, tc) {
    if (!fog) return true;
    if (tr % 2 === 1 && tc % 2 === 1) return seenCell(fog, (tr - 1) / 2, (tc - 1) / 2);
    if (tr % 2 === 1 && tc % 2 === 0) {
      const r = (tr - 1) / 2, c = tc / 2;
      return seenCell(fog, r, c - 1) || seenCell(fog, r, c);
    }
    if (tr % 2 === 0 && tc % 2 === 1) {
      const r = tr / 2, c = (tc - 1) / 2;
      return seenCell(fog, r - 1, c) || seenCell(fog, r, c);
    }
    const r = tr / 2, c = tc / 2;
    return seenCell(fog, r - 1, c - 1) || seenCell(fog, r - 1, c)
        || seenCell(fog, r, c - 1) || seenCell(fog, r, c);
  }

  function mixHex(a, b, t) {
    const n = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
    const A = n(a), B = n(b);
    const u = Math.max(0, Math.min(1, t));
    return "rgb(" + A.map((v, i) => Math.round(v + (B[i] - v) * u)).join(",") + ")";
  }

  /**
   * Lamp falloff from the explorer. Stood-on memory stays visible; cells
   * underfoot read as the bright end of the corridor.
   */
  function fogLamp(fog, tr, tc) {
    if (!fog || !fog.position) return 1;
    const d = (r, c) => Math.abs(r - fog.position.row) + Math.abs(c - fog.position.col);
    const nearest = dists => Math.max(0.38, 1 - 0.12 * Math.min.apply(null, dists));
    if (tr % 2 === 1 && tc % 2 === 1) return nearest([d((tr - 1) / 2, (tc - 1) / 2)]);
    if (tr % 2 === 1 && tc % 2 === 0) {
      const r = (tr - 1) / 2, c = tc / 2;
      return nearest([d(r, c - 1), d(r, c)]);
    }
    if (tr % 2 === 0 && tc % 2 === 1) {
      const r = tr / 2, c = (tc - 1) / 2;
      return nearest([d(r - 1, c), d(r, c)]);
    }
    const r = tr / 2, c = tc / 2;
    return nearest([d(r - 1, c - 1), d(r - 1, c), d(r, c - 1), d(r, c)]);
  }

  function hitCell(geom, x, y) {
    if (!geom) return null;
    const track = (off, v) => {
      for (let i = 1; i < off.length; i += 2) if (v >= off[i] && v < off[i + 1]) return (i - 1) / 2;
      return -1;
    };
    const col = track(geom.offX, x), row = track(geom.offY, y);
    if (row < 0 || col < 0) return null;
    return { row, col };
  }

  function paintWashCell(g, geom, r, c) {
    g.fillRect(geom.offX[2 * c + 1], geom.offY[2 * r + 1], geom.cell, geom.cell);
  }

  /** Openings between live cells so a wash reads as a field, not graph paper. */
  function paintWashOpenings(g, geom, tiles, live) {
    const rows = (tiles.length - 1) / 2, cols = (tiles[0].length - 1) / 2;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        if (!live(r, c)) continue;
        if (c + 1 < cols && live(r, c + 1) && tiles[2 * r + 1][2 * c + 2] !== "#") {
          const tc = 2 * c + 2;
          g.fillRect(geom.offX[tc], geom.offY[2 * r + 1],
                     geom.offX[tc + 1] - geom.offX[tc], geom.cell);
        }
        if (r + 1 < rows && live(r + 1, c) && tiles[2 * r + 2][2 * c + 1] !== "#") {
          const tr = 2 * r + 2;
          g.fillRect(geom.offX[2 * c + 1], geom.offY[tr],
                     geom.cell, geom.offY[tr + 1] - geom.offY[tr]);
        }
      }
    }
  }

  function paint(canvas, scene) {
    const tiles = scene.tiles;
    const th = tiles.length, tw = tiles[0].length;
    const box = stageBox(canvas);
    const geom = computeGeometry(tiles, box.w, box.h - LEGEND_RESERVE - EXPORT_RESERVE);
    canvas.width = geom.offX[tw];
    canvas.height = geom.offY[th];
    canvas.style.width = geom.cssW + "px";
    canvas.style.height = geom.cssH + "px";
    canvas.style.marginTop = EXPORT_RESERVE + "px";
    canvas.style.marginBottom = LEGEND_RESERVE + "px";
    const g = canvas.getContext("2d");
    g.imageSmoothingEnabled = false;

    g.fillStyle = scene.fog ? COLORS.unseen : COLORS.wall;
    g.fillRect(0, 0, canvas.width, canvas.height);
    let start = null, goal = null;
    for (let r = 0; r < th; r++) {
      for (let col = 0; col < tw; col++) {
        const t = tiles[r][col];
        if (!fogRevealsTile(scene.fog, r, col)) continue;
        const wallTile = t === "#"
            && !(r % 2 === 0 && col % 2 === 0 && isInteriorPost(tiles, r, col));
        if (wallTile) {
          if (scene.fog) {
            const lamp = fogLamp(scene.fog, r, col);
            g.fillStyle = mixHex(COLORS.wall, COLORS.wallWarm, lamp * 0.45);
            g.fillRect(geom.offX[col], geom.offY[r],
                       geom.offX[col + 1] - geom.offX[col], geom.offY[r + 1] - geom.offY[r]);
          }
          continue;
        }
        if (r % 2 === 1 && col % 2 === 1 && isRock(tiles, r, col)) continue;
        const lamp = scene.fog ? fogLamp(scene.fog, r, col) : 1;
        if (scene.fog) {
          const lit = mixHex(COLORS.floor, COLORS.floorWarm, lamp * 0.28);
          g.fillStyle = mixHex(COLORS.floorDim, lit, lamp);
        } else {
          g.fillStyle = COLORS.floor;
        }
        g.fillRect(geom.offX[col], geom.offY[r],
                   geom.offX[col + 1] - geom.offX[col], geom.offY[r + 1] - geom.offY[r]);
        if (r % 2 === 1 && col % 2 === 1 && geom.cell >= 10 && lamp > 0.7) {
          g.fillStyle = COLORS.floorHi;
          g.fillRect(geom.offX[col] + 1, geom.offY[r] + 1, geom.cell - 2, 1);
        }
        if (t === "S") start = { row: (r - 1) / 2, col: (col - 1) / 2 };
        if (t === "G") goal  = { row: (r - 1) / 2, col: (col - 1) / 2 };
      }
    }

    if (scene.fog) {
      paintWalk(g, geom, scene.fog.walk, PLAYER_COLORS[0], 1, 0.32);
      if (start && seenCell(scene.fog, start.row, start.col)) {
        endpoint(g, geom, start, COLORS.start);
      }
      if (scene.fog.goal) endpoint(g, geom, scene.fog.goal, COLORS.goal);
      marker(g, geom, scene.fog.position, PLAYER_COLORS[0], 0.42);
      return geom;
    }

    const hot = new Map();
    (scene.hotspots || []).forEach(h => {
      const tr = 2 * h.row + 1, tc = 2 * h.col + 1;
      if (tiles[tr][tc] === "#" || isRock(tiles, tr, tc)) return;
      hot.set(h.row + "," + h.col, h.cost);
      g.fillStyle = "#e5484d";
      g.globalAlpha = Math.min(0.7, 0.2 + h.cost / 200);
      g.fillRect(geom.offX[tc], geom.offY[tr], geom.cell, geom.cell);
    });
    if (hot.size) {
      g.fillStyle = "#e5484d";
      g.globalAlpha = 0.35;
      paintWashOpenings(g, geom, tiles, (r, c) => hot.has(r + "," + c));
      g.globalAlpha = 1;
    }
    if (scene.field) {
      const max = Math.max(1, scene.field.maxDistance);
      const ramp = scene.distanceRamp;
      const tone = (r, c) => {
        const d = scene.field.distances[r][c];
        if (d < 0) return null;
        const t = d / max;
        return { color: ramp[Math.min(ramp.length - 1, Math.round(t * (ramp.length - 1)))],
                 alpha: 0.12 + 0.68 * t };
      };
      for (let r = 0; r < scene.field.rows; r++) {
        for (let c = 0; c < scene.field.cols; c++) {
          const s = tone(r, c);
          if (!s) continue;
          g.fillStyle = s.color;
          g.globalAlpha = s.alpha;
          paintWashCell(g, geom, r, c);
        }
      }
      g.fillStyle = ramp[Math.min(ramp.length - 1, Math.round(0.55 * (ramp.length - 1)))];
      g.globalAlpha = 0.42;
      paintWashOpenings(g, geom, tiles, (r, c) => scene.field.distances[r][c] >= 0);
      g.globalAlpha = 1;
    }
    if (scene.lens) {
      const lensColors = scene.lensColors;
      for (let r = 0; r < scene.lens.rows; r++) {
        for (let c = 0; c < scene.lens.cols; c++) {
          const band = scene.lens.bands[r][c];
          if (band < 0) continue;
          g.fillStyle = lensColors[band];
          g.globalAlpha = band === 2 ? 0.16 : 0.42;
          paintWashCell(g, geom, r, c);
        }
      }
      g.fillStyle = lensColors[2];
      g.globalAlpha = 0.2;
      paintWashOpenings(g, geom, tiles, (r, c) => scene.lens.bands[r][c] >= 0);
      g.globalAlpha = 1;
    }
    if (scene.expansions && scene.expansions.length && (scene.searchProgress ?? 1) > 0) {
      const shown = Math.ceil(scene.expansions.length * scene.searchProgress);
      const live = new Set();
      for (let i = 0; i < shown; i++) {
        const p = scene.expansions[i];
        live.add(p.row + "," + p.col);
      }
      g.fillStyle = COLORS.path;
      g.globalAlpha = 0.16;
      for (let i = 0; i < shown; i++) {
        paintWashCell(g, geom, scene.expansions[i].row, scene.expansions[i].col);
      }
      paintWashOpenings(g, geom, tiles, (r, c) => live.has(r + "," + c));
      g.globalAlpha = 0.45;
      for (let i = Math.max(0, shown - 6); i < shown; i++) {
        paintWashCell(g, geom, scene.expansions[i].row, scene.expansions[i].col);
      }
      g.globalAlpha = 1;
    }
    if (scene.path && scene.path.length && scene.pathProgress > 0) {
      paintWalk(g, geom, scene.path, COLORS.path, scene.pathProgress, 0.85);
      pathHead(g, geom, walkHead(scene.path, scene.pathProgress), COLORS.path);
    }
    if (scene.analysis) {
      (scene.analysis.deadEnds || []).forEach(p => {
        const [x, y] = cellCenter(geom, p);
        g.fillStyle = "#9ecbff";
        g.globalAlpha = 0.5;
        g.beginPath();
        g.arc(x, y, geom.cell * 0.12, 0, 2 * Math.PI);
        g.fill();
        g.globalAlpha = 1;
      });
      (scene.analysis.chokepoints || []).forEach(cp => {
        const tr = cp.a.row + cp.b.row + 1, tc = cp.a.col + cp.b.col + 1;
        g.fillStyle = "#c084fc";
        g.globalAlpha = 0.35;
        g.fillRect(geom.offX[tc] - geom.wall, geom.offY[tr] - geom.wall,
                   (geom.offX[tc + 1] - geom.offX[tc]) + 2 * geom.wall,
                   (geom.offY[tr + 1] - geom.offY[tr]) + 2 * geom.wall);
        g.globalAlpha = 0.95;
        g.fillRect(geom.offX[tc], geom.offY[tr],
                   geom.offX[tc + 1] - geom.offX[tc], geom.offY[tr + 1] - geom.offY[tr]);
        g.globalAlpha = 1;
      });
    }
    if (scene.sanctuaries) {
      scene.sanctuaries.placements.forEach(p => {
        const [x, y] = cellCenter(geom, p);
        g.fillStyle = "#4cc38a";
        g.beginPath();
        g.arc(x, y, geom.cell * 0.32, 0, 2 * Math.PI);
        g.fill();
      });
      const w = scene.sanctuaries.worstServed;
      if (w) {
        const [x, y] = cellCenter(geom, w);
        g.strokeStyle = "#e5484d";
        g.lineWidth = Math.max(1.5, geom.cell * 0.16);
        g.beginPath();
        g.arc(x, y, geom.cell * 0.36, 0, 2 * Math.PI);
        g.stroke();
      }
    }
    if (scene.hardest && scene.hardest.path && scene.hardest.path.length) {
      paintWalk(g, geom, scene.hardest.path, "#f2c94c", 1, 0.75);
    }
    if (scene.tourPath && scene.tourPath.length) {
      paintWalk(g, geom, scene.tourPath, "#9ecbff", 1, 0.38);
    }
    if (scene.tour && scene.tour.waypoints) {
      scene.tour.waypoints.forEach(w => {
        const got = (scene.tourGot || []).some(p => p.row === w.row && p.col === w.col);
        const [x, y] = cellCenter(geom, w);
        const rad = geom.cell * 0.3;
        g.beginPath();
        g.moveTo(x, y - rad); g.lineTo(x + rad, y); g.lineTo(x, y + rad); g.lineTo(x - rad, y);
        g.closePath();
        if (got) {
          g.strokeStyle = "#4cc38a"; g.lineWidth = Math.max(1.5, geom.cell * 0.09); g.stroke();
        } else {
          g.fillStyle = "#f2c94c"; g.fill();
        }
      });
    }
    if (scene.race) {
      scene.race.lanes.forEach((lane, li) => {
        const shown = Math.ceil(lane.expansions.length * lane.front);
        const live = new Set();
        for (let i = 0; i < shown; i++) {
          const p = lane.expansions[i];
          live.add(p.row + "," + p.col);
        }
        g.fillStyle = lane.color;
        g.globalAlpha = 0.13;
        for (let i = 0; i < shown; i++) {
          paintWashCell(g, geom, lane.expansions[i].row, lane.expansions[i].col);
        }
        paintWashOpenings(g, geom, tiles, (r, c) => live.has(r + "," + c));
        g.globalAlpha = 0.4;
        for (let i = Math.max(0, shown - 5); i < shown; i++) {
          paintWashCell(g, geom, lane.expansions[i].row, lane.expansions[i].col);
        }
        g.globalAlpha = 1;
        if (!(lane.pathProg > 0) && shown > 0) {
          pathHead(g, geom, lane.expansions[shown - 1], lane.color);
        }
        if (lane.pathProg > 0 && lane.path && lane.path.length) {
          paintWalk(g, geom, lane.path, lane.color, lane.pathProg, li === 0 ? 0.85 : 0.58);
          pathHead(g, geom, walkHead(lane.path, lane.pathProg), lane.color);
        }
      });
    }
    Object.entries(scene.trails || {}).forEach(([name, points], i) => {
      paintWalk(g, geom, points, PLAYER_COLORS[i % PLAYER_COLORS.length], 1, 0.32);
    });
    if (scene.session && scene.ghostWalk && scene.ghostWalk.length) {
      paintWalk(g, geom, scene.ghostWalk, COLORS.ghost, 1, 0.28);
    }
    if (start) endpoint(g, geom, start, COLORS.start);
    if (goal)  endpoint(g, geom, goal,  COLORS.goal);
    if (scene.session) {
      Object.entries(scene.session.positions).forEach(([name, p], i) => {
        marker(g, geom, p, PLAYER_COLORS[i % PLAYER_COLORS.length], 0.42);
      });
    }
    if (scene.session && scene.ghost && scene.ghost.pos) {
      ghostDisc(g, geom, scene.ghost.pos);
    }
    if (scene.won && goal) {
      const [x, y] = cellCenter(geom, goal);
      g.strokeStyle = "#f0b429";
      g.lineWidth = Math.max(2, geom.wall);
      g.beginPath();
      g.arc(x, y, geom.cell * 0.7, 0, 2 * Math.PI);
      g.stroke();
    }
    return geom;
  }

  /** A tiny honest maze — same thin-wall track, faint — so the empty well is a mark, not a caption. */
  const IDLE_TILES = [
    "###########",
    "# #   #   #",
    "# ### ### #",
    "#   #   # #",
    "### ### # #",
    "#     #   #",
    "###########",
  ];

  function paintIdleMark(g, cx, cy) {
    const tiles = IDLE_TILES;
    const geom = computeGeometry(tiles, 200, 140, 1);
    const w = geom.offX[tiles[0].length], h = geom.offY[tiles.length];
    const ox = Math.round(cx - w / 2), oy = Math.round(cy - h / 2);
    g.save();
    g.translate(ox, oy);
    g.globalAlpha = 0.42;
    g.fillStyle = COLORS.floor;
    for (let r = 0; r < tiles.length; r++) {
      for (let c = 0; c < tiles[r].length; c++) {
        if (tiles[r][c] === "#") continue;
        g.fillRect(geom.offX[c], geom.offY[r],
                   geom.offX[c + 1] - geom.offX[c], geom.offY[r + 1] - geom.offY[r]);
      }
    }
    g.globalAlpha = 0.78;
    marker(g, geom, {row: 0, col: 0}, COLORS.start, 0.34);
    marker(g, geom, {row: 2, col: 4}, COLORS.goal, 0.34);
    g.restore();
  }

  function paintEmpty(canvas) {
    const box = stageBox(canvas);
    const dpr = (typeof window !== "undefined" && window.devicePixelRatio) || 1;
    const cssW = Math.max(280, box.w);
    const cssH = Math.max(220, box.h);
    canvas.width = Math.round(cssW * dpr);
    canvas.height = Math.round(cssH * dpr);
    canvas.style.width = cssW + "px";
    canvas.style.height = cssH + "px";
    canvas.style.marginTop = "0";
    canvas.style.marginBottom = "0";
    const g = canvas.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.imageSmoothingEnabled = false;
    g.fillStyle = COLORS.wall;
    g.fillRect(0, 0, cssW, cssH);
    const cx = cssW / 2;
    const cy = cssH / 2;
    const glow = g.createRadialGradient(cx, cy - 36, 12, cx, cy - 36, Math.min(cssW, cssH) * 0.42);
    glow.addColorStop(0, "rgba(62, 224, 143, 0.10)");
    glow.addColorStop(0.55, "rgba(126, 182, 255, 0.04)");
    glow.addColorStop(1, "rgba(0, 0, 0, 0)");
    g.fillStyle = glow;
    g.fillRect(0, 0, cssW, cssH);
    paintIdleMark(g, cx, cy - 48);
    g.textAlign = "center";
    g.textBaseline = "alphabetic";
    g.fillStyle = "#e8eef4";
    g.font = "700 28px Bahnschrift, \"Avenir Next Condensed\", \"Trebuchet MS\", sans-serif";
    g.letterSpacing = "0.22em";
    g.fillText("DAEDALUS", cx, cy + 48);
    g.letterSpacing = "0";
    g.fillStyle = "#7d8894";
    g.font = "13px Bahnschrift, \"Segoe UI\", sans-serif";
    g.fillText("Pick a generator and press Generate", cx, cy + 78);
    g.fillStyle = "#5a6570";
    g.fillText("then Solve to watch a route unfold", cx, cy + 98);
    g.fillText("or open a session and play", cx, cy + 116);
  }

  function pathRevealMs(n) {
    return Math.min(5000, Math.max(700, (n || 0) * 14));
  }

  global.DaedalusDraw = {
    paint, paintEmpty, computeGeometry, isRock, isInteriorPost,
    paintWalk, walkHead, fogRevealsTile, fogLamp, hitCell, pathRevealMs,
    LEGEND_RESERVE, EXPORT_RESERVE,
  };
})(window);
