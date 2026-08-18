const { chromium } = require('playwright');
const results = [];
function record(name, ok, evidence) {
  results.push({ name, ok, evidence });
  console.log(`${ok ? 'PASS' : '**FAIL**'}\t${name}\t${evidence}`);
}
async function check(name, fn) {
  try { const [ok, ev] = await fn(); record(name, ok, ev); }
  catch (e) { record(name, false, `${e.name}: ${e.message.slice(0, 110)}`); }
}

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const ctx = await browser.newContext({ viewport: { width: 1500, height: 1000 } });
  const page = await ctx.newPage();
  const pageErrors = [];
  page.on('pageerror', e => pageErrors.push(e.message));
  await page.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
  await page.waitForFunction(() => document.getElementById('generator').options.length > 0, null, { timeout: 20000 });

  await check('A. catalog populates', async () => {
    const n = await page.evaluate(() => ({
      g: document.getElementById('generator').options.length,
      s: document.getElementById('solver').options.length,
      r: document.getElementById('rival').options.length }));
    return [n.g > 10 && n.s > 5 && n.r > 5, `${n.g} generators, ${n.s} solvers, ${n.r} rivals`];
  });

  await check('B. generate + solve animation', async () => {
    await page.fill('#rows','21'); await page.fill('#cols','21'); await page.fill('#seed','3');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.rows === 21, null, {timeout:15000});
    await page.click('#solve');
    await page.waitForFunction(() => state.path && state.path.length > 1, null, {timeout:15000});
    const n = await page.evaluate(() => ({p: state.path.length, e: (state.expansions||[]).length}));
    return [n.p > 1 && n.e > 0, `route ${n.p} cells, ${n.e} expansions animated`];
  });

  await check('C. compare all solvers', async () => {
    await page.click('#compare');
    await page.waitForFunction(() => document.getElementById('compareBox').innerText.length > 40, null, {timeout:20000});
    const rows = await page.evaluate(() => document.querySelectorAll('#compareBox tr, #compareBox div').length);
    return [rows > 0, `comparison rendered (${rows} rows)`];
  });

  await check('D. analyze structure overlay', async () => {
    await page.click('#analyze');
    await page.waitForFunction(() => state.analysis != null, null, {timeout:15000});
    const a = await page.evaluate(() => state.analysis);
    return [a.cutSize === 1 && a.deadEndCount > 0, `cut=${a.cutSize}, deadEnds=${a.deadEndCount}, route=${a.routeLength}`];
  });

  await check('D2. hardest route: tree says one route, eroded says detour', async () => {
    // Both halves matter. On the perfect maze the button must report a detour of exactly 1.00
    // and say why; after erosion opens loops the same button must report a real gap. A check
    // that only looked at the eroded case would pass against a service that always claims a
    // detour, which is the failure this feature is most likely to have.
    // This check erodes a maze, so it works on its own instance and hands the sequence back
    // the maze it was given. The first version skipped that and left the shared maze alive,
    // which made the later 'living maze' and 'traffic' checks fail on a disabled #live button
    // — a sweep step that breaks the steps after it is worse than no step at all.
    await page.fill('#seed','909'); await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 909, null, {timeout:15000});
    await page.click('#hardest');
    await page.waitForFunction(() => state.hardest != null, null, {timeout:20000});
    const tree = await page.evaluate(() => state.hardest);
    const saysTree = await page.evaluate(() =>
        document.getElementById('compareBox').innerText.includes('tree'));

    await page.click('#live');
    await page.waitForTimeout(14000);
    await page.evaluate(() => { state.hardest = null; });
    await page.click('#hardest');
    await page.waitForFunction(() => state.hardest != null, null, {timeout:20000});
    const eroded = await page.evaluate(() => state.hardest);
    const gold = await page.evaluate(() => {
      const c = document.getElementById('maze');
      const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      let n = 0;
      for (let i = 0; i < d.length; i += 4) {
        if (d[i] > 150 && d[i+1] > 120 && d[i] - d[i+2] > 60) n++;
      }
      return n;
    });
    const ok = tree.loops === 0 && tree.detour === 1.0 && saysTree
        && eroded.loops > 0 && eroded.detour > 1.0 && gold > 500;

    await page.fill('#seed','3'); await page.click('#generate');   // restore B's maze
    await page.waitForFunction(() => state.maze && state.maze.seed === 3, null, {timeout:15000});
    return [ok, `tree x${tree.detour} loops=${tree.loops}; eroded x${eroded.detour} `
        + `loops=${eroded.loops}; ${gold} route pixels drawn`];
  });

  await check('D3. heat map shades the field, sanctuaries mark the lonely cell', async () => {
    await page.click('#heatmap');
    await page.waitForFunction(() => state.field != null, null, {timeout:20000});
    const shaded = await page.evaluate(() => {
      const c = document.getElementById('maze');
      const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      let n = 0;
      for (let i = 0; i < d.length; i += 4) if (d[i+2] - d[i] > 40 && d[i+2] > 110) n++;
      return n;
    });
    const f = await page.evaluate(() => ({max: state.field.maxDistance, un: state.field.unreachable}));

    await page.click('#sanctuaries');
    await page.waitForFunction(() => state.sanctuaries != null, null, {timeout:20000});
    const s = await page.evaluate(() => ({n: state.sanctuaries.placements.length,
        r: state.sanctuaries.coveringRadius, served: state.sanctuaries.servedCells,
        hab: state.sanctuaries.habitableCells, fieldCleared: state.field === null}));
    const green = await page.evaluate(() => {
      const c = document.getElementById('maze');
      const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      let n = 0;
      for (let i = 0; i < d.length; i += 4) if (d[i+1] > 150 && d[i] < 130 && d[i+2] < 160) n++;
      return n;
    });
    const ok = shaded > 5000 && f.max > 50 && f.un === 0
        && s.n === 5 && s.r > 0 && s.served === s.hab && s.fieldCleared && green > 300;
    return [ok, `${shaded} cells shaded up to ${f.max} steps; ${s.n} sanctuaries radius ${s.r} `
        + `serving ${s.served}/${s.hab}; ${green} marker pixels`];
  });

  await check('E. solver arena race', async () => {
    await page.selectOption('#solver','bfs'); await page.selectOption('#rival','astar');
    await page.click('#race');
    await page.waitForFunction(() => /wins/.test(document.getElementById('compareBox').innerText), null, {timeout:30000});
    const v = await page.$eval('#compareBox', el => el.innerText.trim().slice(0, 90));
    return [/wins/.test(v), v];
  });

  await check('F. play + keyboard movement', async () => {
    await page.fill('#player','sweeper');
    await page.click('#play');
    await page.waitForFunction(() => !!state.session, null, {timeout:15000});
    const before = await page.evaluate(() => JSON.stringify(state.session.positions));
    for (const k of ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight']) {
      await page.keyboard.press(k); await page.waitForTimeout(150);
    }
    const after = await page.evaluate(() => JSON.stringify(state.session.positions));
    const trail = await page.evaluate(() => {
      const t = Object.values(state.trails)[0] || [];
      for (let i = 1; i < t.length; i++) {
        if (Math.abs(t[i].row - t[i-1].row) + Math.abs(t[i].col - t[i-1].col) !== 1) return 0;
      }
      return t.length;
    });
    const hash = await page.evaluate(() => location.hash);
    return [before !== after && trail >= 2 && /session=/.test(hash),
        `player moved via arrow keys; trail ${trail} cells; ${hash}`];
  });

  await check('G. living maze erodes in UI', async () => {
    await page.click('#live');
    await page.waitForFunction(() => /alive/.test(document.getElementById('log').innerText), null, {timeout:15000});
    const walls = t => t.reduce((n,r) => n + (r.match(/#/g)||[]).length, 0);
    const before = await page.evaluate(() => state.maze.tiles.reduce((n,r)=>n+(r.match(/#/g)||[]).length,0));
    await page.waitForFunction(b => state.maze.tiles.reduce((n,r)=>n+(r.match(/#/g)||[]).length,0) < b,
        before, {timeout:30000});
    const after = await page.evaluate(() => state.maze.tiles.reduce((n,r)=>n+(r.match(/#/g)||[]).length,0));
    return [after < before, `walls ${before} -> ${after} live in the UI`];
  });

  await check('H. traffic congestion in UI', async () => {
    await page.click('#traffic');
    await page.waitForTimeout(500);
    await page.evaluate(async () => {
      const r = await api(`/maze/${state.maze.id}/solve/bfs`, {method:'POST'});
      for (let i = 1; i < Math.min(14, r.path.length); i++) {
        const f = state.session.positions[state.session.primary], t = r.path[i];
        await move(state.session.primary, t.row - f.row, t.col - f.col);
        await new Promise(x => setTimeout(x, 90));
      }
    });
    await page.waitForFunction(() => (state.maze.hotspots||[]).length > 0, null, {timeout:25000});
    const h = await page.evaluate(() => (state.maze.hotspots||[]).length);
    return [h > 0, `${h} congested cells rendered`];
  });

  await check('I. daily challenge + scoped board', async () => {
    await page.click('#daily');
    await page.waitForFunction(() => document.getElementById('lbTitle').textContent === 'Daily leaderboard', null, {timeout:20000});
    const hash = await page.evaluate(() => location.hash);
    return [hash === '#daily', `${await page.$eval('#lbTitle', e => e.textContent)} ${hash}`];
  });

  await check('J. crossbreed lineage', async () => {
    await page.fill('#rows','15'); await page.fill('#cols','15');
    await page.selectOption('#generator','recursive-backtracker'); await page.fill('#seed','21');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze.rows === 15 && state.maze.generatorId === 'recursive-backtracker', null, {timeout:15000});
    await page.selectOption('#generator','binary-tree'); await page.fill('#seed','22');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze.generatorId === 'binary-tree', null, {timeout:15000});
    const before = await page.evaluate(() => state.maze.id);
    await page.click('#breed');
    await page.waitForFunction(b => state.maze.id !== b && state.maze.generatorId === 'crossbreed', before, {timeout:20000});
    return [true, `child generated (${await page.evaluate(() => state.maze.generatorId)})`];
  });

  await check('K. campaign ladder + stage play', async () => {
    await page.click('#campaign');
    await page.waitForFunction(() => state.campaign && state.session, null, {timeout:40000});
    const c = await page.evaluate(() => ({n: state.campaign.stages.length, stage: state.stageIndex,
      title: document.getElementById('lbTitle').textContent}));
    await page.evaluate(async () => {
      const r = await api(`/maze/${state.maze.id}/solve/bfs`, {method:'POST'});
      for (let i = 1; i < r.path.length; i++) {
        const f = state.session.positions[state.session.primary], t = r.path[i];
        await move(state.session.primary, t.row - f.row, t.col - f.col);
        await new Promise(x => setTimeout(x, 20));
      }
    });
    await page.waitForFunction(() => state.cleared[0] === true, null, {timeout:40000});
    const hash = await page.evaluate(() => location.hash);
    return [c.n === 6 && c.stage === 0 && /campaign=/.test(hash),
        `${c.n} stages, "${c.title}", stage 1 cleared, ${hash}`];
  });

  await check('L. ghost on stage replay', async () => {
    // Clear first: a ghost left over from the previous stage load makes the wait below pass
    // instantly on stale state, and the assertion then races the reload that nulls it.
    await page.evaluate(() => { state.ghost = null; });
    await page.evaluate(() => document.querySelector('#campaignBox a[data-stage="0"]').click());
    await page.waitForFunction(() => state.stageIndex === 0 && !!state.ghost && !!state.session,
        null, {timeout:30000});
    const g = await page.evaluate(() => ({n: state.ghost.name, ms: state.ghost.elapsedMs}));
    return [!!g.n, `ghost "${g.n}" summoned (${(g.ms/1000).toFixed(1)}s run)`];
  });

  await check('M. spectator permalink read-only', async () => {
    // Independent of earlier checks: establish a session here rather than inheriting one.
    if (!(await page.evaluate(() => !!state.session))) {
      await page.click('#play');
      await page.waitForFunction(() => !!state.session, null, {timeout:15000});
    }
    // One legal hop so the snapshot has a walk, not just a seat.
    await page.evaluate(async () => {
      const r = await api(`/maze/${state.maze.id}/solve/bfs`, {method:'POST'});
      if (r.path && r.path.length > 1) {
        const f = state.session.positions[state.session.primary], t = r.path[1];
        await move(state.session.primary, t.row - f.row, t.col - f.col);
      }
    });
    await page.waitForTimeout(400);
    const sid = await page.evaluate(() => state.session.id);
    const spec = await ctx.newPage();
    await spec.goto(`http://localhost:8080/#session=${sid}`, { waitUntil: 'networkidle' });
    await spec.waitForFunction(() => state.readOnly === true && !!state.session
        && state.trails && Object.values(state.trails).some(w => w && w.length >= 2),
        null, {timeout:25000});
    const walk = await spec.evaluate(() => {
      const w = state.trails[state.session.primary] || [];
      let adj = true;
      for (let i = 1; i < w.length; i++) {
        if (Math.abs(w[i].row - w[i-1].row) + Math.abs(w[i].col - w[i-1].col) !== 1) adj = false;
      }
      return {n: w.length, adj, hash: location.hash};
    });
    for (const k of ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight']) await spec.keyboard.press(k);
    await spec.waitForTimeout(500);
    const mc = await spec.evaluate(async () => (await api(`/session/${state.session.id}`)).moveCount);
    const mine = await page.evaluate(() => state.session ? 1 : 0);
    await spec.close();
    return [mine === 1 && walk.n >= 2 && walk.adj && /session=/.test(walk.hash),
        `spectator walk ${walk.n} 4-adj; hash ${walk.hash}; moveCount ${mc}`];
  });

  await check('N. maze permalink', async () => {
    const p2 = await ctx.newPage();
    const id = await page.evaluate(() => state.maze.id);
    await p2.goto(`http://localhost:8080/#maze=${id}`, { waitUntil: 'networkidle' });
    await p2.waitForFunction(i => state.maze && state.maze.id === i, id, {timeout:20000});
    const dims = await p2.evaluate(() => ({r: document.getElementById('rows').value, m: state.maze.rows}));
    await p2.close();
    return [String(dims.r) === String(dims.m), `loaded by id; size inputs synced to ${dims.m}`];
  });

  await check('Q. login form + fog-of-war hides unseen floor', async () => {
    const form = await page.evaluate(() => ({
      login: !!document.getElementById('login'),
      user: !!document.getElementById('user'),
      fog: !!document.getElementById('fog'),
    }));
    await page.fill('#rows','15'); await page.fill('#cols','15'); await page.fill('#seed','7');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 7, null, {timeout:15000});
    await page.click('#fog');
    await page.waitForFunction(() => state.fog && state.fog.seen && state.fog.seen.size === 1,
        null, {timeout:15000});
    const f = await page.evaluate(() => ({
      seen: state.fog.seen.size,
      open: (state.fog.open || []).length,
      walk: (state.fog.walk || []).length,
    }));
    const key = {NORTH:'ArrowUp', SOUTH:'ArrowDown', WEST:'ArrowLeft', EAST:'ArrowRight'}
        [(await page.evaluate(() => (state.fog.open || [])[0]))];
    if (key) {
      await page.keyboard.press(key);
      await page.waitForFunction(() => state.fog.walk && state.fog.walk.length === 2,
          null, {timeout:10000});
    }
    const walked = await page.evaluate(() => {
      const w = state.fog.walk || [];
      if (w.length < 2) return false;
      return Math.abs(w[1].row - w[0].row) + Math.abs(w[1].col - w[0].col) === 1;
    });
    // Living tick + fog: GET /maze would rewrite unseen rooms. Memory of the void
    // must not change when the server erodes.
    const unseen = () => page.evaluate(() => {
      const tiles = state.maze.tiles;
      let s = '';
      for (let r = 0; r < tiles.length; r++) {
        for (let c = 0; c < tiles[r].length; c++) {
          if (!fogRevealsTile(r, c)) s += tiles[r][c];
        }
      }
      return s;
    });
    const beforeUnseen = await unseen();
    await page.click('#live');
    await page.waitForFunction(() => /tick \d/.test(document.getElementById('log').innerText),
        null, {timeout:20000});
    const afterUnseen = await unseen();
    return [form.login && form.user && form.fog && f.seen === 1 && f.open > 0 && walked
        && beforeUnseen.length > 0 && beforeUnseen === afterUnseen,
        `fog walk 4-adj; unseen glyphs held through a living tick (${beforeUnseen.length} chars)`];
  });

  await check('R. ASCII is negotiated as text/plain, not drawn from tiles', async () => {
    await page.fill('#seed','11'); await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 11, null, {timeout:15000});
    await page.click('#ascii');
    await page.waitForFunction(() => {
      const el = document.getElementById('asciiOut');
      return el && !el.hidden && el.textContent.includes('#') && el.textContent.includes('S');
    }, null, {timeout:15000});
    const art = await page.$eval('#asciiOut', el => el.textContent);
    const plugins = await page.$eval('#pluginBox', el => el.textContent);
    return [art.includes('#') && art.includes('S') && !art.includes('{') && plugins.length > 0,
        `ASCII ${art.length} chars; plugins: ${plugins.slice(0, 40)}`];
  });

  await check('S. generator partition is a query, not a client filter', async () => {
    // Leave any daily/campaign maze-scope so maze= cannot swallow generator=.
    await page.fill('#seed','13'); await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 13
        && state.dailyId == null && state.stageIndex == null, null, {timeout:15000});
    await page.selectOption('#lbGen', 'prims');
    await page.waitForFunction(() => state.lbQuery && state.lbQuery.includes('generator=prims')
        && !state.lbQuery.includes('maze='), null, {timeout:10000});
    const q = await page.evaluate(() => state.lbQuery);
    const title = await page.$eval('#lbTitle', e => e.textContent);
    return [/generator=prims/.test(q) && !/maze=/.test(q) && /prim/i.test(title),
        `${title} via ${q}`];
  });

  await check('T. solver walks stay 4-adjacent (no chord through a wall)', async () => {
    await page.fill('#rows','15'); await page.fill('#cols','15'); await page.fill('#seed','5');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 5, null, {timeout:15000});
    const jumped = [];
    for (const id of ['bfs', 'wall-follower', 'tremaux']) {
      await page.selectOption('#solver', id);
      await page.evaluate(() => { state.path = null; });
      await page.click('#solve');
      await page.waitForFunction(() => state.path && state.path.length > 1, null, {timeout:20000});
      const hop = await page.evaluate(() => {
        const p = state.path;
        for (let i = 1; i < p.length; i++) {
          if (Math.abs(p[i].row - p[i-1].row) + Math.abs(p[i].col - p[i-1].col) !== 1) {
            return i;
          }
        }
        return 0;
      });
      if (hop) jumped.push(id + '@' + hop);
    }
    return [jumped.length === 0 && typeof paintWalk === 'function',
        jumped.length ? jumped.join(',') : 'bfs, wall-follower, tremaux are 4-walks'];
  });

  await check('U. waypoint tour paints the Held-Karp walk, not just coins', async () => {
    await page.fill('#rows','15'); await page.fill('#cols','15'); await page.fill('#seed','8');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 8, null, {timeout:15000});
    await page.click('#tour');
    await page.waitForFunction(() => state.tour && state.tour.path && state.tour.path.length > 1,
        null, {timeout:20000});
    const w = await page.evaluate(() => {
      const p = tourWalk();
      let adj = true;
      for (let i = 1; i < p.length; i++) {
        if (Math.abs(p[i].row - p[i-1].row) + Math.abs(p[i].col - p[i-1].col) !== 1) adj = false;
      }
      return {n: p.length, cost: state.tour.optimalCost, adj,
        coins: (state.tour.waypoints || []).length};
    });
    const sid = await page.evaluate(() => state.session && state.session.id);
    const spec = await ctx.newPage();
    await spec.goto(`http://localhost:8080/#session=${sid}`, { waitUntil: 'networkidle' });
    await spec.waitForFunction(() => state.readOnly && state.tour && tourWalk().length > 1,
        null, {timeout:25000});
    const specWalk = await spec.evaluate(() => ({n: tourWalk().length, hash: location.hash}));
    await spec.close();
    return [w.adj && w.n === w.cost + 1 && w.coins > 0
        && specWalk.n === w.n && /session=/.test(specWalk.hash),
        `tour walk ${w.n} cells = cost ${w.cost}+1; spectator ${specWalk.n} ${specWalk.hash}`];
  });

  await check('V. generator permalink is the partition, not a title', async () => {
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/#generator=prims', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => state.lbQuery && state.lbQuery.includes('generator=prims')
        && !state.lbQuery.includes('maze='), null, {timeout:20000});
    const q = await p2.evaluate(() => ({
      path: state.lbQuery,
      hash: location.hash,
      sel: document.getElementById('lbGen').value,
    }));
    await p2.close();
    return [/generator=prims/.test(q.path) && q.sel === 'prims' && /generator=prims/.test(q.hash),
        `${q.sel} via ${q.path} ${q.hash}`];
  });

  await check('W. generate braid opens dead ends, not just a label', async () => {
    await page.fill('#rows', '15'); await page.fill('#cols', '15'); await page.fill('#seed', '7');
    await page.selectOption('#braid', '0');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 7, null, {timeout:15000});
    await page.evaluate(() => { state.analysis = null; });
    await page.click('#analyze');
    await page.waitForFunction(() => state.analysis != null, null, {timeout:15000});
    const tree = await page.evaluate(() => state.analysis.deadEndCount);
    await page.selectOption('#braid', '0.8');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 7, null, {timeout:15000});
    await page.evaluate(() => { state.analysis = null; });
    await page.click('#analyze');
    await page.waitForFunction(() => state.analysis != null, null, {timeout:15000});
    const braided = await page.evaluate(() => state.analysis.deadEndCount);
    const echoed = await page.evaluate(() => ({
      factor: state.maze.braid,
      stats: document.getElementById('stats').innerText,
    }));
    await page.selectOption('#braid', '0');
    return [braided < tree && echoed.factor === 0.8 && echoed.stats.includes('0.8'),
        `dead ends ${tree} → ${braided}; maze.braid=${echoed.factor}`];
  });

  await check('X. living tick updates the hardest overlay without a second click', async () => {
    await page.selectOption('#braid', '0');
    await page.fill('#rows', '15'); await page.fill('#cols', '15'); await page.fill('#seed', '909');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 909, null, {timeout:15000});
    await page.click('#hardest');
    await page.waitForFunction(() => state.hardest && state.hardest.loops === 0, null, {timeout:20000});
    await page.click('#live');
    await page.waitForFunction(() => state.hardest && state.hardest.loops > 0, null, {timeout:25000});
    const h = await page.evaluate(() => ({loops: state.hardest.loops, detour: state.hardest.detour}));
    await page.fill('#seed', '3'); await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 3, null, {timeout:15000});
    return [h.loops > 0 && h.detour > 1, `auto-refresh loops=${h.loops} x${h.detour}`];
  });

  await check('Y. living tick updates the fingerprint without a second click', async () => {
    await page.selectOption('#braid', '0');
    await page.fill('#rows', '15'); await page.fill('#cols', '15'); await page.fill('#seed', '909');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 909, null, {timeout:15000});
    await page.click('#fingerprint');
    await page.waitForFunction(() => state.fingerprint && state.fingerprint.signature, null,
        {timeout:40000});
    const before = await page.evaluate(() => state.fingerprint.signature.deadEndRatio);
    await page.click('#live');
    await page.waitForFunction((was) => state.fingerprint
        && state.fingerprint.signature.deadEndRatio !== was, before, {timeout:25000});
    const after = await page.evaluate(() => state.fingerprint.signature.deadEndRatio);
    await page.fill('#seed', '3'); await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 3, null, {timeout:15000});
    return [after < before, `dead-end ratio ${before.toFixed(3)} → ${after.toFixed(3)}`];
  });

  await check('Z. generate braid and tournament braid stay one number', async () => {
    await page.selectOption('#braid', '0.8');
    const v = await page.evaluate(() => ({
      g: document.getElementById('braid').value,
      t: document.getElementById('tourBraid').value,
    }));
    await page.selectOption('#tourBraid', '0.4');
    const back = await page.evaluate(() => ({
      g: document.getElementById('braid').value,
      t: document.getElementById('tourBraid').value,
    }));
    await page.selectOption('#braid', '0');
    return [v.g === '0.8' && v.t === '0.8' && back.g === '0.4' && back.t === '0.4',
        `braid ${v.g}/${v.t} then ${back.g}/${back.t}`];
  });

  await check('O. no uncaught page errors', async () =>
    [pageErrors.length === 0, pageErrors.length ? pageErrors.join(' | ').slice(0,150) : 'none']);

  await page.screenshot({ path: 'sweep-final.png' });
  const errs = await page.$$eval('#log span.err', els => els.map(e => e.textContent));
  const real = errs.filter(t => !/unavailable/.test(t));
  record('P. no error lines in UI log', real.length === 0, real.length ? real.join(' | ').slice(0,150) : 'none');

  const passed = results.filter(r => r.ok).length;
  console.log(`\n=== ${passed}/${results.length} UI checks passed ===`);
  results.filter(r => !r.ok).forEach(r => console.log(`FAILED: ${r.name} -- ${r.evidence}`));
  await browser.close();
  process.exit(passed === results.length ? 0 : 1);
})().catch(e => { console.error('HARNESS FAILED:', e.message); process.exit(2); });
