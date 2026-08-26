// SPDX-License-Identifier: MIT
// Canvas painter. app.js builds a scene object; this file does not read `state`.
"use strict";
(function (global) {
  const COLORS = {
    wall: "#161c24", floor: "#465362", start: "#4cc38a", goal: "#e5484d", path: "#82b1ff",
  };
  const PLAYER_COLORS = ["#f0b429", "#ff8fa3", "#9ecbff", "#7ce2b3"];

  function computeGeometry(tiles) {
    const th = tiles.length, tw = tiles[0].length;
    const cols = (tw - 1) / 2;
    const cell = Math.max(6, Math.min(26, Math.floor(880 / (cols * 1.25 + 0.25))));
    const wall = Math.max(2, Math.round(cell / 4));
    const track = n => {
      const off = new Array(n + 1);
      off[0] = 0;
      for (let i = 0; i < n; i++) off[i + 1] = off[i] + (i % 2 === 0 ? wall : cell);
      return off;
    };
    return { offX: track(tw), offY: track(th), cell, wall };
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
    g.beginPath();
    g.arc(x, y, geom.cell * radius, 0, 2 * Math.PI);
    g.fill();
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

  function paint(canvas, scene) {
    const tiles = scene.tiles;
    const th = tiles.length, tw = tiles[0].length;
    const geom = computeGeometry(tiles);
    canvas.width = geom.offX[tw];
    canvas.height = geom.offY[th];
    const g = canvas.getContext("2d");

    g.fillStyle = COLORS.wall;
    g.fillRect(0, 0, canvas.width, canvas.height);
    let start = null, goal = null;
    for (let r = 0; r < th; r++) {
      for (let col = 0; col < tw; col++) {
        const t = tiles[r][col];
        if (t === "#" && !(r % 2 === 0 && col % 2 === 0 && isInteriorPost(tiles, r, col))) {
          continue;
        }
        if (r % 2 === 1 && col % 2 === 1 && isRock(tiles, r, col)) continue;
        if (!fogRevealsTile(scene.fog, r, col)) continue;
        g.fillStyle = COLORS.floor;
        g.fillRect(geom.offX[col], geom.offY[r],
                   geom.offX[col + 1] - geom.offX[col], geom.offY[r + 1] - geom.offY[r]);
        if (t === "S") start = { row: (r - 1) / 2, col: (col - 1) / 2 };
        if (t === "G") goal  = { row: (r - 1) / 2, col: (col - 1) / 2 };
      }
    }

    if (scene.fog) {
      paintWalk(g, geom, scene.fog.walk, PLAYER_COLORS[0], 1, 0.45);
      marker(g, geom, scene.fog.position, PLAYER_COLORS[0], 0.42);
      if (scene.fog.goal) marker(g, geom, scene.fog.goal, COLORS.goal, 0.34);
      return geom;
    }

    (scene.hotspots || []).forEach(h => {
      const tr = 2 * h.row + 1, tc = 2 * h.col + 1;
      if (tiles[tr][tc] === "#" || isRock(tiles, tr, tc)) return;
      g.fillStyle = "#e5484d";
      g.globalAlpha = Math.min(0.7, 0.2 + h.cost / 200);
      g.fillRect(geom.offX[tc], geom.offY[tr], geom.cell, geom.cell);
      g.globalAlpha = 1;
    });
    if (scene.field) {
      const max = Math.max(1, scene.field.maxDistance);
      const ramp = scene.distanceRamp;
      for (let r = 0; r < scene.field.rows; r++) {
        for (let c = 0; c < scene.field.cols; c++) {
          const d = scene.field.distances[r][c];
          if (d < 0) continue;
          const t = d / max;
          g.fillStyle = ramp[Math.min(ramp.length - 1, Math.round(t * (ramp.length - 1)))];
          g.globalAlpha = 0.12 + 0.68 * t;
          g.fillRect(geom.offX[2 * c + 1], geom.offY[2 * r + 1], geom.cell, geom.cell);
        }
      }
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
          g.fillRect(geom.offX[2 * c + 1], geom.offY[2 * r + 1], geom.cell, geom.cell);
        }
      }
      g.globalAlpha = 1;
    }
    if (scene.expansions && scene.expansions.length && (scene.searchProgress ?? 1) > 0) {
      const shown = Math.ceil(scene.expansions.length * scene.searchProgress);
      g.fillStyle = COLORS.path;
      g.globalAlpha = 0.16;
      for (let i = 0; i < shown; i++) {
        const p = scene.expansions[i];
        g.fillRect(geom.offX[2 * p.col + 1], geom.offY[2 * p.row + 1], geom.cell, geom.cell);
      }
      g.globalAlpha = 0.45;
      for (let i = Math.max(0, shown - 6); i < shown; i++) {
        const p = scene.expansions[i];
        g.fillRect(geom.offX[2 * p.col + 1], geom.offY[2 * p.row + 1], geom.cell, geom.cell);
      }
      g.globalAlpha = 1;
    }
    if (scene.path && scene.path.length && scene.pathProgress > 0) {
      paintWalk(g, geom, scene.path, COLORS.path, scene.pathProgress, 0.85);
      const head = walkHead(scene.path, scene.pathProgress);
      if (head) marker(g, geom, head, COLORS.path, 0.38);
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
        g.fillStyle = lane.color;
        g.globalAlpha = 0.13;
        for (let i = 0; i < shown; i++) {
          const p = lane.expansions[i];
          g.fillRect(geom.offX[2 * p.col + 1], geom.offY[2 * p.row + 1], geom.cell, geom.cell);
        }
        g.globalAlpha = 0.4;
        for (let i = Math.max(0, shown - 5); i < shown; i++) {
          const p = lane.expansions[i];
          g.fillRect(geom.offX[2 * p.col + 1], geom.offY[2 * p.row + 1], geom.cell, geom.cell);
        }
        g.globalAlpha = 1;
        if (lane.pathProg > 0 && lane.path && lane.path.length) {
          paintWalk(g, geom, lane.path, lane.color, lane.pathProg, li === 0 ? 0.55 : 0.85);
          const head = walkHead(lane.path, lane.pathProg);
          if (head) marker(g, geom, head, lane.color, 0.36);
        }
      });
    }
    Object.entries(scene.trails || {}).forEach(([name, points], i) => {
      paintWalk(g, geom, points, PLAYER_COLORS[i % PLAYER_COLORS.length], 1, 0.32);
    });
    if (scene.session && scene.ghostWalk && scene.ghostWalk.length) {
      paintWalk(g, geom, scene.ghostWalk, "#e6edf3", 1, 0.28);
    }
    if (start) marker(g, geom, start, COLORS.start, 0.34);
    if (goal)  marker(g, geom, goal,  COLORS.goal,  0.34);
    if (scene.session) {
      Object.entries(scene.session.positions).forEach(([name, p], i) => {
        marker(g, geom, p, PLAYER_COLORS[i % PLAYER_COLORS.length], 0.42);
      });
    }
    if (scene.session && scene.ghost && scene.ghost.pos) {
      const [x, y] = cellCenter(geom, scene.ghost.pos);
      g.globalAlpha = 0.55;
      g.fillStyle = "#e6edf3";
      g.beginPath();
      g.arc(x, y, geom.cell * 0.3, 0, 2 * Math.PI);
      g.fill();
      g.globalAlpha = 1;
      g.strokeStyle = "#e6edf3";
      g.lineWidth = 1;
      g.beginPath();
      g.arc(x, y, geom.cell * 0.3, 0, 2 * Math.PI);
      g.stroke();
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

  function paintEmpty(canvas) {
    const g = canvas.getContext("2d");
    g.fillStyle = COLORS.wall;
    g.fillRect(0, 0, canvas.width, canvas.height);
    g.fillStyle = "#8a949e";
    g.font = "14px system-ui, sans-serif";
    g.textAlign = "center";
    g.fillText("Pick a generator and press Generate", canvas.width / 2, canvas.height / 2 - 8);
    g.fillStyle = "#5c6771";
    g.fillText("then Solve to watch a route unfold, or open a session and play",
        canvas.width / 2, canvas.height / 2 + 16);
  }

  function pathRevealMs(n) {
    return Math.min(5000, Math.max(700, (n || 0) * 14));
  }

  global.DaedalusDraw = {
    paint, paintEmpty, computeGeometry, isRock, isInteriorPost,
    paintWalk, walkHead, fogRevealsTile, hitCell, pathRevealMs,
  };
})(window);
