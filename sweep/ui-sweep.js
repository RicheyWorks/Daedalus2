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

  await check('B2. hotspot cells follow the seed', async () => {
    const d = await page.evaluate(() => {
      const a = placeHotspots(15, 15, 4, 42, 25);
      const b = placeHotspots(15, 15, 4, 42, 25);
      const c = placeHotspots(15, 15, 4, 43, 25);
      return {same: JSON.stringify(a) === JSON.stringify(b),
              diff: JSON.stringify(a) !== JSON.stringify(c), n: a.length};
    });
    return [d.same && d.diff && d.n === 4,
        `4 spots; seed-stable ${d.same} seed-sensitive ${d.diff}`];
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

  await check('N2. hotspot recipe rebuilds an aged-out maze id', async () => {
    await page.fill('#rows', '15'); await page.fill('#cols', '15'); await page.fill('#seed', '42');
    await page.fill('#hotspots', '4');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 42
        && (state.maze.hotspots || []).length === 4, null, {timeout:15000});
    const hash = await page.evaluate(() => location.hash);
    const spots = await page.evaluate(() => JSON.stringify(state.maze.hotspots));
    const recipe = hash.replace(/maze=[0-9a-fA-F-]+/,
        'maze=00000000-0000-0000-0000-000000000000');
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/' + recipe, { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => state.maze && (state.maze.hotspots || []).length === 4,
        null, {timeout:20000});
    const rebuilt = await p2.evaluate(() => JSON.stringify(state.maze.hotspots));
    await p2.close();
    await page.fill('#hotspots', '0');
    return [rebuilt === spots && /hotspots=4/.test(hash),
        `recipe ${hash}; spots ${rebuilt === spots}`];
  });

  await check('N3. capacity kinds name the pool, not the status line', async () => {
    const d = await page.evaluate(() => {
      const raw = kind => `409 Conflict on /maze/x — ${kind}: already holding 1`;
      const maze = nameCapacity(raw('maze-capacity'));
      const session = nameCapacity(raw('session-capacity'));
      const agent = nameCapacity(raw('agent-capacity'));
      const tour = nameCapacity(raw('tour-capacity'));
      const living = nameCapacity(raw('living-capacity'));
      const traffic = nameCapacity(raw('traffic-capacity'));
      const miss = nameCapacity('404 Not Found on /maze/x');
      const rebuild = permalinkLoadFailed(
          {message: '404 Not Found on /maze/dead'},
          {message: raw('maze-capacity')});
      const gone = permalinkLoadFailed({message: '404 Not Found on /maze/dead'}, null);
      return {maze, session, agent, tour, living, traffic, miss, rebuild, gone,
        dumps: /409/.test([maze, session, agent, tour, living, traffic].join(' '))};
    });
    const named = d.maze && d.session && d.agent && d.tour && d.living && d.traffic
        && d.miss == null && !d.dumps
        && /cached/.test(d.maze) && /sessions/.test(d.session)
        && /fog/.test(d.agent) && /waypoint/.test(d.tour)
        && /aged out/.test(d.rebuild) && /cached/.test(d.rebuild)
        && !/not found/.test(d.rebuild) && /gone/.test(d.gone) && !/404/.test(d.gone);
    return [named, named ? 'six pools named; permalink 409 is not a 404'
        : JSON.stringify(d).slice(0, 160)];
  });

  await check('N4. spectator and permalink 404s name gone, not the status line', async () => {
    const d = await page.evaluate(() => {
      const mazeRaw = '404 Not Found on /maze/dead — maze: No maze dead is available';
      const sessionRaw = '404 Not Found on /session/dead — session: No session dead is open.';
      const agentRaw = '404 Not Found on /agent/dead — agent: No agent walk dead is open.';
      const maze = nameGone(mazeRaw);
      const session = nameGone(sessionRaw);
      const agent = nameGone(agentRaw);
      const permalink = permalinkLoadFailed({message: mazeRaw}, null);
      const tour = nameGone('404 Not Found on /session/dead/tour — tour: no hunt');
      const ghost = nameGone('404 Not Found on /maze/dead/ghost — ghost run: none');
      const solver = nameGone('404 Not Found on /maze/dead/solve/nope — solver: unknown');
      return {maze, session, agent, permalink, tour, ghost, solver,
        dumps: /404/.test([maze, session, agent, permalink].join(' '))};
    });
    const named = d.maze === 'that maze is gone' && d.session === 'that session is gone'
        && d.agent === 'that fog walk is gone' && d.permalink === 'that maze is gone'
        && d.tour == null && d.ghost == null && d.solver == null && !d.dumps;
    return [named, named ? 'gone named; tour/ghost/solver 404s stay unnamed'
        : JSON.stringify(d).slice(0, 180)];
  });

  await check('N5. solver-budget names the give-up, not the status line', async () => {
    const d = await page.evaluate(() => {
      const raw = '422 Unprocessable Entity on /maze/x/solve/ida-star — solver-budget: '
          + 'ida-star gave up after expanding 50000 nodes';
      const named = nameBudget(raw);
      const again = nameBudget(named);
      const miss = nameBudget('404 Not Found on /maze/x/solve/nope — solver: unknown');
      const cap = nameBudget('409 Conflict on /maze/x — maze-capacity: already holding 1');
      return {named, again, miss, cap,
        dumps: /422|Unprocessable/.test(named || '')};
    });
    const ok = d.named && /budget/.test(d.named) && d.again === d.named
        && d.miss == null && d.cap == null && !d.dumps;
    return [ok, ok ? 'solver-budget named; 404/409 stay unnamed'
        : JSON.stringify(d).slice(0, 180)];
  });

  await check('N6. spectator Fog/Generate/Open session leave watch before they write', async () => {
    // Old body: generate had no leaveSpectate; play left after the POST; fog never left
    // (readOnly stayed true while POST /agent minted a walk on the watched maze).
    const src = await page.evaluate(() => {
      const order = (fn, write) => {
        const s = fn.toString();
        const leave = s.indexOf('leaveSpectate');
        const w = s.indexOf(write);
        return leave >= 0 && w >= 0 && leave < w;
      };
      return {
        gen: order(generate, '/maze/generate'),
        fog: order(startFog, '/agent'),
        play: order(play, '/session?'),
      };
    });
    if (!(await page.evaluate(() => !!state.session))) {
      await page.click('#play');
      await page.waitForFunction(() => !!state.session, null, {timeout:15000});
    }
    const sid = await page.evaluate(() => state.session.id);
    const spec = await ctx.newPage();
    await spec.goto(`http://localhost:8080/#session=${sid}`, { waitUntil: 'networkidle' });
    await spec.waitForFunction(() => state.readOnly === true && !!state.session, null, {timeout:25000});
    const armed = await spec.evaluate(() => ({
      fog: !document.getElementById('fog').disabled,
      gen: !document.getElementById('generate').disabled,
      play: !document.getElementById('play').disabled,
      live: document.getElementById('live').disabled,
      tour: document.getElementById('tour').disabled,
    }));
    await spec.click('#fog');
    await spec.waitForFunction(() => state.fog && state.fog.seen, null, {timeout:15000});
    const after = await spec.evaluate(() => ({
      readOnly: state.readOnly,
      session: !!state.session,
      fog: !!(state.fog && state.fog.agentId),
    }));
    await spec.close();
    const ok = src.gen && src.fog && src.play
        && armed.fog && armed.gen && armed.play && armed.live && armed.tour
        && !after.readOnly && after.fog && !after.session;
    return [ok, ok ? 'leave before write; fog dropped watch'
        : JSON.stringify({src, armed, after}).slice(0, 200)];
  });

  await check('N7. spectator Daily/Campaign/Breed/Solve leave watch before they write', async () => {
    // Old body: those four fetched (or painted) while readOnly was still set;
    // adoptMaze then cleared watch as a side effect. Solve never left.
    const src = await page.evaluate(() => {
      const order = (fn, write) => {
        const s = fn.toString();
        const leave = s.indexOf('leaveSpectate');
        const w = s.indexOf(write);
        return leave >= 0 && w >= 0 && leave < w;
      };
      return {
        daily: order(loadDaily, '/maze/daily'),
        campaign: order(loadCampaign, '/campaign'),
        stage: order(playStage, 'stage.mazeId'),
        breed: order(crossbreed, '/maze/breed'),
        solve: order(solve, '/solve/'),
      };
    });
    if (!(await page.evaluate(() => !!state.session))) {
      await page.click('#play');
      await page.waitForFunction(() => !!state.session, null, {timeout:15000});
    }
    const sid = await page.evaluate(() => state.session.id);
    const spec = await ctx.newPage();
    await spec.goto(`http://localhost:8080/#session=${sid}`, { waitUntil: 'networkidle' });
    await spec.waitForFunction(() => state.readOnly === true && !!state.session, null, {timeout:25000});
    const armed = await spec.evaluate(() => ({
      daily: !document.getElementById('daily').disabled,
      campaign: !document.getElementById('campaign').disabled,
      solve: !document.getElementById('solve').disabled,
      live: document.getElementById('live').disabled,
      tour: document.getElementById('tour').disabled,
    }));
    await spec.click('#solve');
    await spec.waitForFunction(() => state.path && state.path.length > 1 && !state.readOnly,
        null, {timeout:15000});
    const after = await spec.evaluate(() => ({
      readOnly: state.readOnly,
      path: !!(state.path && state.path.length > 1),
      session: !!state.session,
    }));
    await spec.close();
    const ok = src.daily && src.campaign && src.stage && src.breed && src.solve
        && armed.daily && armed.campaign && armed.solve && armed.live && armed.tour
        && !after.readOnly && after.path;
    return [ok, ok ? 'leave before daily/campaign/breed/solve write'
        : JSON.stringify({src, armed, after}).slice(0, 220)];
  });

  await check('N8. spectator Measure/tournament/ASCII stay watchers', async () => {
    // Old body: showAscii called leaveSpectate, so a living-tick refresh of the
    // dump re-armed Bring to life. Measure and tournament already stayed.
    const src = await page.evaluate(() => {
      const stay = (fn) => {
        const s = fn.toString();
        return !s.includes('leaveSpectate') && !s.includes('refuseSpectatorWrite');
      };
      return {measure: stay(measureGrowth), tour: stay(runTournament), ascii: stay(showAscii)};
    });
    if (!(await page.evaluate(() => !!state.session))) {
      await page.click('#play');
      await page.waitForFunction(() => !!state.session, null, {timeout:15000});
    }
    const sid = await page.evaluate(() => state.session.id);
    const spec = await ctx.newPage();
    await spec.goto(`http://localhost:8080/#session=${sid}`, { waitUntil: 'networkidle' });
    await spec.waitForFunction(() => state.readOnly === true && !!state.session, null, {timeout:25000});
    const armed = await spec.evaluate(() => ({
      measure: !document.getElementById('measure').disabled,
      tournament: !document.getElementById('tournament').disabled,
      ascii: !document.getElementById('ascii').disabled,
      live: document.getElementById('live').disabled,
      tour: document.getElementById('tour').disabled,
    }));
    await spec.click('#measure');
    await spec.waitForFunction(() => {
      const t = document.getElementById('labOut').innerText;
      return t && t.length > 20 && !/measuring/.test(t);
    }, null, {timeout:25000});
    await spec.click('#ascii');
    await spec.waitForFunction(() => {
      const el = document.getElementById('asciiOut');
      return el && !el.hidden && el.textContent.includes('#');
    }, null, {timeout:15000});
    const after = await spec.evaluate(() => ({
      readOnly: state.readOnly,
      session: !!state.session,
      path: !!(state.path && state.path.length > 1),
      analysis: !!state.analysis,
      lab: document.getElementById('labOut').innerText.length,
      ascii: !document.getElementById('asciiOut').hidden,
    }));
    await spec.close();
    const ok = src.measure && src.tour && src.ascii
        && armed.measure && armed.tournament && armed.ascii && armed.live && armed.tour
        && after.readOnly && after.session && !after.path && !after.analysis
        && after.lab > 20 && after.ascii;
    return [ok, ok ? 'stay watching; sidebar/pre only'
        : JSON.stringify({src, armed, after}).slice(0, 220)];
  });

  await check('N9. ASCII dump does not mint a solve', async () => {
    // Old body: showAscii appended ?solve=, so a living-tick dump refresh
    // (or a spectator click) ran a solver and published MazeSolvedEvent.
    const src = await page.evaluate(() => {
      const s = showAscii.toString();
      return !s.includes('?solve=') && !s.includes('leaveSpectate');
    });
    const minted = [];
    const onReq = (r) => {
      if (r.method() === 'GET' && /\/api\/v1\/maze\/[^/?]+/.test(r.url())
          && /[?&]solve=/.test(r.url())) minted.push(r.url());
    };
    page.on('request', onReq);
    try {
      await page.click('#ascii');
      await page.waitForFunction(() => {
        const el = document.getElementById('asciiOut');
        return el && !el.hidden && el.textContent.includes('#');
      }, null, {timeout:15000});
    } finally {
      page.off('request', onReq);
    }
    const art = await page.evaluate(() => document.getElementById('asciiOut').textContent);
    const dump = art.includes('#') && art.includes('S') && !art.includes('.');
    const ok = src && minted.length === 0 && dump;
    return [ok, ok ? 'text/plain dump, no ?solve='
        : JSON.stringify({src, minted: minted.length, dump}).slice(0, 220)];
  });

  await check('N10. Back re-hydrates the hash; pinHash does not remint', async () => {
    // Old body: loadFromHash was boot-only. Generate wrote #maze=B; Back left
    // the bar on A and the canvas on B. pinHash's write must not re-GET.
    const src = await page.evaluate(() => {
      const s = loadFromHash.toString();
      return typeof hashShowsCurrent === 'function'
          && s.includes('hashShowsCurrent()');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '11');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 11, null, {timeout:15000});
    const a = await p2.evaluate(() => ({id: state.maze.id, hash: location.hash}));
    await p2.fill('#seed', '12');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 12, null, {timeout:15000});
    const b = await p2.evaluate(() => ({id: state.maze.id, hash: location.hash}));
    const fetched = [];
    const onReq = (r) => {
      if (r.method() === 'GET' && r.url().includes(`/api/v1/maze/${a.id}`)
          && !/[?&]/.test(r.url().split(`/api/v1/maze/${a.id}`)[1] || '')) {
        fetched.push(r.url());
      }
    };
    p2.on('request', onReq);
    try {
      await p2.evaluate(() => history.back());
      await p2.waitForFunction(id => state.maze && state.maze.id === id, a.id, {timeout:20000});
    } finally {
      p2.off('request', onReq);
    }
    const after = await p2.evaluate(() => ({id: state.maze.id, hash: location.hash}));
    await p2.close();
    const ok = src && a.id !== b.id && /maze=/.test(a.hash) && /maze=/.test(b.hash)
        && after.id === a.id && after.hash === a.hash && fetched.length === 1;
    return [ok, ok ? `Back ${b.hash.slice(0, 24)} → ${a.hash.slice(0, 24)}; one GET`
        : JSON.stringify({src, a: a.id, b: b.id, after, fetched: fetched.length}).slice(0, 220)];
  });

  await check('N11. Back from a campaign drops the ladder', async () => {
    // Old body: hashchange re-hydrated the maze (N10) but adoptMaze only
    // nulled stageIndex. state.campaign and #campaignBox stayed painted;
    // a stage click still played a campaign maze the bar no longer named.
    const src = await page.evaluate(() => {
      const s = loadFromHash.toString();
      return typeof leaveCampaign === 'function'
          && typeof hashShowsCurrent === 'function'
          && s.includes('leaveCampaign()')
          && s.includes('hashShowsCurrent()');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '13');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 13, null, {timeout:15000});
    const maze = await p2.evaluate(() => ({id: state.maze.id, hash: location.hash}));
    await p2.click('#campaign');
    await p2.waitForFunction(() => state.campaign && state.stageIndex === 0
        && !!document.querySelector('#campaignBox a[data-stage]'), null, {timeout:40000});
    await p2.evaluate(() => history.back());
    await p2.waitForFunction(id => state.maze && state.maze.id === id
        && !state.campaign
        && !document.querySelector('#campaignBox a[data-stage]'), maze.id, {timeout:20000});
    const after = await p2.evaluate(() => ({
      id: state.maze && state.maze.id,
      hash: location.hash,
      campaign: !!state.campaign,
      stages: document.querySelectorAll('#campaignBox a[data-stage]').length,
    }));
    let stillPlays = false;
    try {
      stillPlays = await p2.evaluate(async () => {
        await playStage(0);
        return !!(state.campaign && state.stageIndex === 0);
      });
    } catch (e) {
      stillPlays = false;
    }
    await p2.close();
    const ok = src && /maze=/.test(maze.hash) && after.id === maze.id
        && /maze=/.test(after.hash) && !after.campaign && after.stages === 0
        && !stillPlays;
    return [ok, ok ? `Back dropped the ladder; ${after.hash.slice(0, 28)}`
        : JSON.stringify({src, maze: maze.id, after, stillPlays}).slice(0, 220)];
  });

  await check('N12. Generate / Daily / Breed from a campaign drop the ladder', async () => {
    // Old body: loadFromHash left on a non-campaign hydrate (N11), but
    // Generate / Daily / Breed adopt then pin a matching #maze= / #daily.
    // hashShowsCurrent no-ops, so the ladder stayed and a stage click
    // still played a campaign maze the bar no longer named.
    const src = await page.evaluate(() => {
      const pin = pinHash.toString();
      const stage = playStage.toString();
      const afterAdopt = (fn) => {
        const s = fn.toString();
        const a = s.indexOf('adoptMaze');
        const p = s.indexOf('pinHash()');
        return a >= 0 && p > a && !s.includes('leaveCampaign()');
      };
      return typeof leaveCampaign === 'function'
          && pin.includes('leaveCampaign()')
          && pin.includes('p.campaign == null')
          && afterAdopt(generate) && afterAdopt(loadDaily) && afterAdopt(crossbreed)
          && stage.includes('state.stageIndex = index')
          && stage.indexOf('pinHash()') > stage.indexOf('state.stageIndex = index')
          && !stage.includes('leaveCampaign()');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    const enterCampaign = async () => {
      await p2.click('#campaign');
      await p2.waitForFunction(() => state.campaign && state.stageIndex === 0
          && !!document.querySelector('#campaignBox a[data-stage]'), null, {timeout:40000});
    };
    const left = async (hashRe) => {
      await p2.waitForFunction(() => !state.campaign
          && !document.querySelector('#campaignBox a[data-stage]'), null, {timeout:20000});
      const snap = await p2.evaluate(() => ({
        hash: location.hash,
        campaign: !!state.campaign,
        stages: document.querySelectorAll('#campaignBox a[data-stage]').length,
      }));
      let stillPlays = false;
      try {
        stillPlays = await p2.evaluate(async () => {
          await playStage(0);
          return !!(state.campaign && state.stageIndex === 0);
        });
      } catch (e) {
        stillPlays = false;
      }
      return {ok: hashRe.test(snap.hash) && !snap.campaign && snap.stages === 0
          && !stillPlays, snap, stillPlays};
    };
    await enterCampaign();
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '14');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 14, null, {timeout:15000});
    const gen = await left(/maze=/);
    await enterCampaign();
    await p2.click('#daily');
    await p2.waitForFunction(() => !!state.dailyId, null, {timeout:20000});
    const daily = await left(/^#daily$/);
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '15');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 15, null, {timeout:15000});
    await p2.waitForFunction(() => !document.getElementById('breed').disabled,
        null, {timeout:5000});
    await enterCampaign();
    await p2.waitForFunction(() => !document.getElementById('breed').disabled,
        null, {timeout:5000});
    await p2.click('#breed');
    await p2.waitForFunction(() => state.maze && !state.campaign, null, {timeout:20000});
    const breed = await left(/maze=/);
    await p2.close();
    const ok = src && gen.ok && daily.ok && breed.ok;
    return [ok, ok ? 'Generate / Daily / Breed dropped the ladder'
        : JSON.stringify({src, gen, daily, breed}).slice(0, 220)];
  });

  await check('N13. campaign permalink names the stage', async () => {
    // Old body: currentPermalink wrote only the seed; loadCampaign always
    // playStage(0). Back / Forward / paste of #campaign=SEED reminted stage 1.
    const src = await page.evaluate(() => {
      const perm = currentPermalink.toString();
      const load = loadCampaign.toString();
      const from = loadFromHash.toString();
      return typeof parseCampaignToken === 'function'
          && perm.includes('stageIndex')
          && perm.includes('+ ":" +')
          && load.includes('playStage(index)')
          && !load.includes('playStage(0)')
          && from.includes('named.stage')
          && from.includes('parseCampaignToken')
          && !from.includes('loadCampaign(Number(h.campaign))');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.click('#campaign');
    await p2.waitForFunction(() => state.campaign && state.stageIndex === 0
        && !!document.querySelector('#campaignBox a[data-stage="2"]'), null, {timeout:40000});
    const at0 = await p2.evaluate(() => ({
      hash: location.hash,
      seed: state.campaign.seed,
      stage: state.stageIndex,
      maze: state.maze.id,
    }));
    await p2.evaluate(() => document.querySelector('#campaignBox a[data-stage="2"]').click());
    await p2.waitForFunction(() => state.campaign && state.stageIndex === 2
        && state.maze, null, {timeout:30000});
    const at2 = await p2.evaluate(() => ({
      hash: location.hash,
      stage: state.stageIndex,
      maze: state.maze.id,
    }));
    await p2.evaluate(() => history.back());
    await p2.waitForFunction(id => state.campaign && state.stageIndex === 0
        && state.maze && state.maze.id === id, at0.maze, {timeout:20000});
    const back = await p2.evaluate(() => ({
      hash: location.hash,
      stage: state.stageIndex,
      maze: state.maze && state.maze.id,
    }));
    await p2.evaluate(() => history.forward());
    await p2.waitForFunction(id => state.campaign && state.stageIndex === 2
        && state.maze && state.maze.id === id, at2.maze, {timeout:20000});
    const fwd = await p2.evaluate(() => ({
      hash: location.hash,
      stage: state.stageIndex,
      maze: state.maze && state.maze.id,
    }));
    await p2.close();
    const want0 = `#campaign=${at0.seed}`;
    const want2 = `#campaign=${at0.seed}:2`;
    const ok = src && at0.stage === 0 && at0.hash === want0
        && at2.stage === 2 && at2.hash === want2 && at2.maze !== at0.maze
        && back.stage === 0 && back.hash === want0 && back.maze === at0.maze
        && fwd.stage === 2 && fwd.hash === want2 && fwd.maze === at2.maze;
    return [ok, ok ? `Back/Forward ${want0} ↔ ${want2}`
        : JSON.stringify({src, at0, at2, back, fwd}).slice(0, 220)];
  });

  await check('N14. Back onto an empty / #generator= hash drops the maze', async () => {
    // Old body: N10 re-hydrated maze-to-maze. Back from #maze= onto "" or
    // #generator= only touched selects and left the previous maze (and a
    // daily / session seat) on the canvas the bar no longer named.
    const src = await page.evaluate(() => {
      const from = loadFromHash.toString();
      const drop = leaveMaze.toString();
      return typeof leaveMaze === 'function'
          && from.includes('leaveMaze()')
          && from.indexOf('leaveMaze()') > from.indexOf('if (h.maze)')
          && drop.includes('state.maze = null')
          && drop.includes('drawEmpty')
          && !drop.includes('pinHash()');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '16');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 16, null, {timeout:15000});
    const hashed = await p2.evaluate(() => location.hash);
    await p2.evaluate(() => history.back());
    await p2.waitForFunction(() => !state.maze && !location.hash, null, {timeout:20000});
    const empty = await p2.evaluate(() => ({
      maze: !!state.maze,
      session: !!state.session,
      daily: !!state.dailyId,
      campaign: !!state.campaign,
      hash: location.hash,
    }));
    await p2.selectOption('#lbGen', 'prims');
    await p2.waitForFunction(() => location.hash === '#generator=prims', null, {timeout:5000});
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && /maze=/.test(location.hash), null, {timeout:15000});
    await p2.evaluate(() => history.back());
    await p2.waitForFunction(() => !state.maze && location.hash === '#generator=prims',
        null, {timeout:20000});
    const gen = await p2.evaluate(() => ({
      maze: !!state.maze,
      hash: location.hash,
      lb: document.getElementById('lbGen').value,
    }));
    await p2.close();
    const ok = src && /maze=/.test(hashed) && !empty.maze && !empty.session
        && !empty.daily && !empty.campaign && empty.hash === ''
        && !gen.maze && gen.hash === '#generator=prims' && gen.lb === 'prims';
    return [ok, ok ? 'Back dropped the maze onto "" and #generator=prims'
        : JSON.stringify({src, hashed, empty, gen}).slice(0, 220)];
  });

  await check('N15. Fog after Open session drops the leftover #session= hash', async () => {
    // Old body: play pinned #session=. Fog nulled the seat and started
    // the walk without pinning, so the bar still named the session.
    const src = await page.evaluate(() => {
      const s = startFog.toString();
      return s.includes('state.session = null')
          && s.includes('pinHash()')
          && s.indexOf('pinHash()') > s.indexOf('state.session = null');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '17');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 17, null, {timeout:15000});
    await p2.click('#play');
    await p2.waitForFunction(() => !!state.session && /session=/.test(location.hash),
        null, {timeout:15000});
    const opened = await p2.evaluate(() => ({
      sid: state.session.id,
      maze: state.maze.id,
      hash: location.hash,
    }));
    await p2.click('#fog');
    await p2.waitForFunction(() => !!(state.fog && state.fog.agentId) && !state.session
        && /maze=/.test(location.hash) && !/session=/.test(location.hash),
        null, {timeout:20000});
    const after = await p2.evaluate(() => ({
      session: !!state.session,
      fog: !!(state.fog && state.fog.agentId),
      maze: state.maze && state.maze.id,
      hash: location.hash,
    }));
    await p2.close();
    const ok = src && /session=/.test(opened.hash)
        && after.fog && !after.session && after.maze === opened.maze
        && /maze=/.test(after.hash) && !/session=/.test(after.hash)
        && after.hash.includes(opened.maze);
    return [ok, ok ? `Fog rewrote ${opened.hash.slice(0, 24)} → ${after.hash.slice(0, 28)}`
        : JSON.stringify({src, opened, after}).slice(0, 220)];
  });

  await check('N18. late Analyze after Fog does not restore the sidebar', async () => {
    // Old body: startFog emptied #compareBox (N17). Analyze / Compare
    // that were already out still wrote the caption and hover-armed
    // state.path. Discard after the fetch when state.fog is set.
    const src = await page.evaluate(() => {
      const after = (fn) => {
        const s = fn.toString();
        const w = s.indexOf('await ');
        const f = s.indexOf('if (state.fog)');
        return w >= 0 && f > w;
      };
      return after(analyzeStructure) && after(compareSolvers)
          && after(identifyGenerator) && after(distanceHeatMap)
          && after(heuristicLens) && after(solve);
    });
    const p2 = await ctx.newPage();
    await p2.route('**/api/v1/maze/*/analysis', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '19');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 19, null, {timeout:15000});
    await p2.click('#analyze');
    await p2.click('#fog');
    await p2.waitForFunction(() => !!(state.fog && state.fog.agentId), null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const after = await p2.evaluate(() => ({
      fog: !!(state.fog && state.fog.agentId),
      box: document.getElementById('compareBox').innerText.trim(),
      analysis: !!state.analysis,
      path: !!(state.path && state.path.length),
      caption: state.caption,
      tour: !!state.tour,
    }));
    await p2.close();
    const ok = src && after.fog && after.box === '' && !after.analysis
        && !after.path && after.caption == null;
    return [ok, ok ? 'late analysis discarded; sidebar stayed empty'
        : JSON.stringify({src, after}).slice(0, 220)];
  });

  await check('N19. late living GET /maze after Fog does not install the god-mode grid', async () => {
    // Old body: refreshLivingMaze skipped GET /maze only when fog
    // was already set. A tick that passed that gate still assigned
    // the snapshot after Fog started. Discard after the fetch.
    const src = await page.evaluate(() => {
      const s = refreshLivingMaze.toString();
      const snap = s.indexOf('await api(`/maze/${forMaze}`)');
      const discard = s.indexOf('if (stale() || state.fog)', snap);
      const assign = s.indexOf('state.maze = maze');
      return snap >= 0 && discard > snap && assign > discard;
    });
    const p2 = await ctx.newPage();
    await p2.route('**/api/v1/maze/*', async route => {
      const path = new URL(route.request().url()).pathname;
      const snapshot = route.request().method() === 'GET'
          && /\/api\/v1\/maze\/[^/]+$/.test(path);
      if (!snapshot) {
        await route.continue();
        return;
      }
      await new Promise(r => setTimeout(r, 1200));
      const res = await route.fetch();
      const json = await res.json();
      json.seed = 999999;
      await route.fulfill({
        status: res.status(),
        headers: {'content-type': 'application/json'},
        body: JSON.stringify(json),
      });
    });
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '23');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 23, null, {timeout:15000});
    const before = await p2.evaluate(() => ({id: state.maze.id, seed: state.maze.seed}));
    await p2.evaluate(() => { refreshLivingMaze(); });
    await p2.click('#fog');
    await p2.waitForFunction(() => !!(state.fog && state.fog.agentId), null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const after = await p2.evaluate(() => ({
      fog: !!(state.fog && state.fog.agentId),
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
      tour: !!state.tour,
    }));
    await p2.close();
    const ok = src && after.fog && after.seed === before.seed && after.id === before.id
        && after.seed !== 999999;
    return [ok, ok ? 'late living snapshot discarded; fog walk kept its grid'
        : JSON.stringify({src, before, after}).slice(0, 220)];
  });

  await check('N20. late Open session after Fog does not steal the walk', async () => {
    // Old body: play snapshotted hadFog, POSTed, then always
    // state.fog = null. A Fog that started mid-flight still pinned
    // #session= and left the blind walk. Discard after the POST.
    // Hunt → play: discard /tour too, or a late Hunt still calls play().
    const src = await page.evaluate(() => {
      const s = play.toString();
      const post = s.indexOf('/session?');
      const discard = s.indexOf('if (state.fog)', post);
      const apply = s.indexOf('state.session =');
      const drop = s.indexOf('state.fog = null');
      const t = startTour.toString();
      const tw = t.indexOf('await ');
      const tf = t.indexOf('if (state.fog)');
      return post >= 0 && discard > post && apply > discard
          && drop >= 0 && drop < post && !s.includes('hadFog')
          && tw >= 0 && tf > tw;
    });
    const p2 = await ctx.newPage();
    await p2.route('**/api/v1/maze/*/session*', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '29');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 29, null, {timeout:15000});
    await p2.click('#play');
    await p2.click('#fog');
    await p2.waitForFunction(() => !!(state.fog && state.fog.agentId), null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const after = await p2.evaluate(() => ({
      fog: !!(state.fog && state.fog.agentId),
      session: !!state.session,
      hash: location.hash,
      ghost: !!state.ghostTimer,
    }));
    await p2.close();
    const ok = src && after.fog && !after.session && !/session=/.test(after.hash)
        && !after.ghost;
    return [ok, ok ? 'late session discarded; fog walk kept the canvas'
        : JSON.stringify({src, after}).slice(0, 220)];
  });

  await check('N21. late Generate after Fog does not replace the walk', async () => {
    // Old body: generate / daily / campaign / breed fetched then
    // adoptMaze always replaced the maze. A Fog that started
    // mid-flight still lost the canvas. Leave fog before the
    // fetch; discard adopt when state.fog is set after the POST.
    const src = await page.evaluate(() => {
      const after = (fn, write) => {
        const s = fn.toString();
        const drop = s.indexOf('state.fog = null');
        const w = s.indexOf(write);
        const fetch = s.indexOf('await ');
        const discard = s.indexOf('if (state.fog)', fetch);
        const adopt = s.indexOf('adoptMaze', discard);
        return drop >= 0 && drop < w && discard > fetch
            && (adopt > discard || s.indexOf('state.campaign', discard) > discard);
      };
      const a = adoptMaze.toString();
      return after(generate, '/maze/generate')
          && after(loadDaily, '/maze/daily')
          && after(loadCampaign, '/campaign')
          && after(playStage, 'stage.mazeId')
          && after(crossbreed, '/maze/breed')
          && a.indexOf('if (state.fog)') >= 0
          && a.indexOf('if (state.fog)') < a.indexOf('state.maze = maze');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '31');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 31, null, {timeout:15000});
    const before = await p2.evaluate(() => ({id: state.maze.id, seed: state.maze.seed}));
    await p2.route('**/api/v1/maze/generate', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.fill('#seed', '32');
    await p2.click('#generate');
    await p2.click('#fog');
    await p2.waitForFunction(() => !!(state.fog && state.fog.agentId), null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const after = await p2.evaluate(() => ({
      fog: !!(state.fog && state.fog.agentId),
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
    }));
    await p2.close();
    const ok = src && after.fog && after.seed === before.seed && after.id === before.id
        && after.seed !== 32;
    return [ok, ok ? 'late generate discarded; fog walk kept the maze'
        : JSON.stringify({src, before, after}).slice(0, 220)];
  });

  await check('N22. hash hydrate leaves fog before fetch; late #session= does not seat after discard', async () => {
    // Old body: #maze= fetched then adoptMaze no-op'd during fog, so the
    // bar named a maze the canvas still walked. #session= adopt discarded
    // but adoptSessionView still attached a spectator seat. Leave fog
    // before the fetch (leave-walk path); same-hash still no-ops.
    const src = await page.evaluate(() => {
      const from = loadFromHash.toString();
      const spec = spectate.toString();
      const guard = from.indexOf('hashShowsCurrent()');
      const drop = from.indexOf('state.fog = null');
      const mazeGet = from.indexOf('await api(`/maze/${h.maze}`)');
      const mazeDiscard = from.indexOf('if (state.fog)', mazeGet);
      const mazeAdopt = from.indexOf('adoptMaze', mazeDiscard);
      const specDrop = spec.indexOf('state.fog = null');
      const specFetch = spec.indexOf('/session/');
      const specAwait = spec.indexOf('await ');
      const specDiscard = spec.indexOf('if (state.fog)', specAwait);
      const specView = spec.indexOf('adoptSessionView', specDiscard);
      return guard >= 0 && drop > guard && drop < mazeGet
          && mazeDiscard > mazeGet && mazeAdopt > mazeDiscard
          && specDrop >= 0 && specDrop < specFetch
          && specDiscard > specAwait && specView > specDiscard;
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '33');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 33, null, {timeout:15000});
    const a = await p2.evaluate(() => ({id: state.maze.id, hash: location.hash}));
    await p2.fill('#seed', '34');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 34, null, {timeout:15000});
    await p2.click('#fog');
    await p2.waitForFunction(() => !!(state.fog && state.fog.agentId), null, {timeout:20000});
    const same = await p2.evaluate(async () => {
      const before = {fog: !!(state.fog && state.fog.agentId), id: state.maze.id};
      await loadFromHash();
      return {before, after: {fog: !!(state.fog && state.fog.agentId), id: state.maze && state.maze.id}};
    });
    await p2.evaluate(() => history.back());
    await p2.waitForFunction(id => state.maze && state.maze.id === id && !state.fog,
        a.id, {timeout:20000});
    const back = await p2.evaluate(() => ({
      fog: !!state.fog,
      id: state.maze && state.maze.id,
      hash: location.hash,
    }));
    await p2.fill('#seed', '35');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 35, null, {timeout:15000});
    await p2.click('#play');
    await p2.waitForFunction(() => !!state.session, null, {timeout:15000});
    const sid = await p2.evaluate(() => state.session.id);
    await p2.fill('#seed', '36');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 36, null, {timeout:15000});
    await p2.route('**/api/v1/session/**', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.evaluate(id => { location.hash = 'session=' + id; }, sid);
    await p2.click('#fog');
    await p2.waitForFunction(() => !!(state.fog && state.fog.agentId), null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const late = await p2.evaluate(() => ({
      fog: !!(state.fog && state.fog.agentId),
      session: !!state.session,
      readOnly: !!state.readOnly,
      hash: location.hash,
    }));
    await p2.close();
    const ok = src && same.before.fog && same.after.fog && same.after.id === same.before.id
        && back.id === a.id && !back.fog && back.hash === a.hash
        && late.fog && !late.session && !late.readOnly && !/session=/.test(late.hash);
    return [ok, ok ? 'Back left fog and hydrated; late #session= discarded'
        : JSON.stringify({src, same, back, late}).slice(0, 220)];
  });

  await check('N23. late Join after Fog does not steal the walk', async () => {
    // Old body: join POSTed /join then always wrote the seat. Fog
    // mid-flight hit a nulled state.session or reattached the seat.
    // Stay a watcher until join lands; discard when state.fog is set.
    // Not a leave-fog-before-fetch path (spectate honesty).
    const src = await page.evaluate(() => {
      const s = join.toString();
      const post = s.indexOf('/join');
      const discard = s.indexOf('if (state.fog)', post);
      const seat = s.indexOf('state.seat');
      const leave = s.indexOf('leaveSpectate');
      return post >= 0 && discard > post && seat > discard
          && leave > post && !s.includes('state.fog = null')
          && s.indexOf('if (!state.session)', post) > discard;
    });
    const p2 = await ctx.newPage();
    await p2.route('**/api/v1/session/**/join*', async route => {
      await new Promise(r => setTimeout(r, 1200));
      const url = new URL(route.request().url());
      const sid = url.pathname.split('/')[4];
      await route.fulfill({
        status: 200,
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({
          sessionId: sid,
          mazeId: '00000000-0000-0000-0000-000000000000',
          position: {row: 0, col: 0},
        }),
      });
    });
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '37');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 37, null, {timeout:15000});
    await p2.click('#play');
    await p2.waitForFunction(() => !!state.session, null, {timeout:15000});
    await p2.click('#join');
    await p2.click('#fog');
    await p2.waitForFunction(() => !!(state.fog && state.fog.agentId), null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const after = await p2.evaluate(() => ({
      fog: !!(state.fog && state.fog.agentId),
      session: !!state.session,
      seat: state.seat,
      joined: state.joined,
      hash: location.hash,
      ghost: !!state.ghostTimer,
    }));
    await p2.close();
    const ok = src && after.fog && !after.session && !after.seat && !after.joined
        && !/session=/.test(after.hash) && !after.ghost;
    return [ok, ok ? 'late join discarded; fog walk kept the canvas'
        : JSON.stringify({src, after}).slice(0, 220)];
  });

  await check('N24. late confirmWin / tour status after Fog do not paint the walk', async () => {
    // Old body: confirmWin GETs /session/{id} then declareWin with no
    // fog/session re-check. refreshTourStatus painted hunt status the
    // same way. Discard after the GET; startFog still must not null tour.
    const src = await page.evaluate(() => {
      const w = confirmWin.toString();
      const t = refreshTourStatus.toString();
      const d = declareWin.toString();
      const wGet = w.indexOf('/session/');
      const wFog = w.indexOf('if (state.fog)', wGet);
      const tGet = t.indexOf('/tour');
      const tFog = t.indexOf('if (state.fog)', tGet);
      const dFog = d.indexOf('if (state.fog)');
      const fogSrc = startFog.toString();
      return wGet >= 0 && wFog > wGet && w.indexOf('declareWin', wFog) > wFog
          && w.indexOf('if (!state.session)', wGet) > wFog
          && tGet >= 0 && tFog > tGet && t.indexOf('$("status")', tFog) > tFog
          && t.indexOf('if (!state.session)', tGet) > tFog
          && dFog >= 0 && dFog < d.indexOf('state.won =')
          && !fogSrc.includes('state.tour = null');
    });
    const p2 = await ctx.newPage();
    await p2.route('**/api/v1/session/**', async route => {
      const url = new URL(route.request().url());
      const segs = url.pathname.split('/').filter(Boolean);
      const method = route.request().method();
      const isTour = method === 'GET' && segs[segs.length - 1] === 'tour';
      const isSnap = method === 'GET' && segs.length === 4 && segs[2] === 'session';
      if (!isTour && !isSnap) return route.continue();
      await new Promise(r => setTimeout(r, 1200));
      if (isTour) {
        await route.fulfill({
          status: 200,
          headers: {'content-type': 'application/json'},
          body: JSON.stringify({
            remaining: [], total: 3, collected: 3, complete: true, walked: 10, optimal: 8,
          }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({completed: true, completedBy: 'web'}),
      });
    });
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '41');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 41, null, {timeout:15000});
    await p2.click('#play');
    await p2.waitForFunction(() => !!state.session, null, {timeout:15000});
    await p2.evaluate(() => {
      state.tour = state.tour || {waypoints: [], optimalCost: 0};
      void refreshTourStatus();
      void confirmWin('web');
    });
    await p2.click('#fog');
    await p2.waitForFunction(() => !!(state.fog && state.fog.agentId), null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const after = await p2.evaluate(() => ({
      fog: !!(state.fog && state.fog.agentId),
      session: !!state.session,
      won: state.won,
      status: document.getElementById('status').textContent,
      tour: !!state.tour,
      hash: location.hash,
    }));
    await p2.close();
    const painted = /reached the goal|waypoint hunt|waypoints collected/i.test(after.status || '');
    const ok = src && after.fog && !after.session && !after.won && after.tour
        && /^fog:/.test(after.status || '') && !painted && !/session=/.test(after.hash);
    return [ok, ok ? 'late win/hunt discarded; fog walk kept the canvas'
        : JSON.stringify({src, after}).slice(0, 220)];
  });

  await check('N25. late ghost after Fog does not re-arm the ticker', async () => {
    // Old body: summonGhost GETs /ghost then always armed state.ghost
    // and the ticker. Fog mid-flight cleared both; the GET still
    // re-armed the ghost onto the walk. Discard after the GET;
    // startFog still must not null tour.
    const src = await page.evaluate(() => {
      const s = summonGhost.toString();
      const get = s.indexOf('/ghost');
      const fog = s.indexOf('if (state.fog)', get);
      const fogSrc = startFog.toString();
      return get >= 0 && fog > get
          && s.indexOf('state.ghost =', fog) > fog
          && s.indexOf('if (!state.session)', get) > fog
          && s.indexOf('setInterval', fog) > fog
          && !fogSrc.includes('state.tour = null');
    });
    const p2 = await ctx.newPage();
    await p2.route('**/api/v1/maze/*/ghost', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.fulfill({
        status: 200,
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({
          mazeId: '00000000-0000-0000-0000-000000000025',
          playerName: 'speedrunner',
          score: 42,
          elapsedMs: 1500,
          moves: [{to: {row: 0, col: 1}, tMs: 200}],
        }),
      });
    });
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '43');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 43, null, {timeout:15000});
    await p2.click('#play');
    await p2.waitForFunction(() => !!state.session, null, {timeout:15000});
    await p2.click('#fog');
    await p2.waitForFunction(() => !!(state.fog && state.fog.agentId), null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const after = await p2.evaluate(() => ({
      fog: !!(state.fog && state.fog.agentId),
      session: !!state.session,
      ghost: !!state.ghost,
      timer: !!state.ghostTimer,
      hash: location.hash,
    }));
    await p2.close();
    const ok = src && after.fog && !after.session && !after.ghost && !after.timer
        && !/session=/.test(after.hash);
    return [ok, ok ? 'late ghost discarded; fog walk kept the canvas'
        : JSON.stringify({src, after}).slice(0, 220)];
  });

  await check('N26. late fog step / Fog start after Generate does not re-arm the walk', async () => {
    // Old body: fogStep POSTed /step then always applyFogView, which
    // recreates state.fog. startFog POSTed /agent then always applied.
    // Generate that replaced the maze mid-flight still got the old
    // openings carved into the new tiles. Discard after the POST;
    // startFog still must not null tour.
    const src = await page.evaluate(() => {
      const s = fogStep.toString();
      const post = s.indexOf('/step');
      const fog = s.indexOf('state.fog.agentId !== agentId', post);
      const f = startFog.toString();
      const mint = f.indexOf('/agent');
      const id = f.indexOf('mazeId');
      const discard = f.indexOf('state.maze.id !== mazeId');
      return post >= 0 && fog > post
          && s.indexOf('applyFogView(view)', fog) > fog
          && mint >= 0 && id >= 0 && id < mint && discard > mint
          && f.indexOf('applyFogView') > discard
          && !f.includes('state.tour = null');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '47');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 47, null, {timeout:15000});
    const first = await p2.evaluate(() => state.maze.id);
    await p2.route('**/api/v1/maze/*/agent', async route => {
      if (route.request().method() !== 'POST') return route.continue();
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.click('#fog');
    await p2.fill('#seed', '48');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 48, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const lateMint = await p2.evaluate(() => ({
      fog: !!state.fog,
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
    }));
    await p2.unroute('**/api/v1/maze/*/agent');
    await p2.click('#fog');
    await p2.waitForFunction(() => !!(state.fog && state.fog.agentId), null, {timeout:20000});
    const agent = await p2.evaluate(() => state.fog.agentId);
    await p2.route('**/api/v1/agent/*/step*', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.evaluate(() => {
      const dir = (state.fog.open || [])[0];
      const delta = {NORTH: [-1, 0], SOUTH: [1, 0], WEST: [0, -1], EAST: [0, 1]}[dir];
      if (delta) return fogStep(delta[0], delta[1]);
    });
    await p2.fill('#seed', '49');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 49, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const lateStep = await p2.evaluate(() => ({
      fog: !!state.fog,
      seed: state.maze && state.maze.seed,
      agent: state.fog && state.fog.agentId,
    }));
    await p2.close();
    const ok = src && !lateMint.fog && lateMint.seed === 48 && lateMint.id !== first
        && !lateStep.fog && lateStep.seed === 49 && lateStep.agent !== agent;
    return [ok, ok ? 'late fog mint/step discarded; Generate kept the canvas'
        : JSON.stringify({src, lateMint, lateStep, first, agent}).slice(0, 220)];
  });

  await check('N27. late move after Fog or a new session does not overwrite status or the new seat', async () => {
    // Old body: move() POSTed /move then always flashStatus / applyMove.
    // Fog mid-flight: a blocked reply overwrote fog status.
    // Generate + a new Open session: applyMove wrote the old hop onto
    // the new seat. Arrows and click-to-move both call move().
    // Discard after the POST; startFog still must not null tour.
    const src = await page.evaluate(() => {
      const s = move.toString();
      const post = s.indexOf('sessionId}/move');
      const fog = s.indexOf('if (state.fog)', post);
      const id = s.indexOf('sessionId');
      const maze = s.indexOf('mazeId');
      const f = startFog.toString();
      return post >= 0 && id >= 0 && maze >= 0 && id < post && maze < post
          && fog > post
          && s.indexOf('state.session.id !== sessionId', post) > fog
          && s.indexOf('state.maze.id !== mazeId', post) > fog
          && s.indexOf('positions[name] == null', post) > fog
          && s.indexOf('flashStatus', fog) > fog
          && s.indexOf('applyMove', fog) > fog
          && !f.includes('state.tour = null');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '51');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 51, null, {timeout:15000});
    await p2.click('#play');
    await p2.waitForFunction(() => !!state.session, null, {timeout:15000});
    await p2.route('**/api/v1/session/*/move', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.fulfill({
        status: 200,
        headers: {'content-type': 'application/json'},
        body: 'false',
      });
    });
    // Sample across the delayed reply so a 900ms flashStatus cannot
    // hide behind the restore. Old body writes "blocked" over fog.
    const lateFog = await p2.evaluate(async () => {
      const seen = [];
      const hopping = move(thisTabSeat(), 0, 1);
      document.getElementById('fog').click();
      const start = Date.now();
      while (Date.now() - start < 2500) {
        seen.push(document.getElementById('status').textContent);
        await new Promise(r => setTimeout(r, 40));
      }
      await hopping.catch(() => {});
      return {
        fog: !!(state.fog && state.fog.agentId),
        session: !!state.session,
        seen,
      };
    });
    await p2.unroute('**/api/v1/session/*/move');
    await p2.evaluate(() => { state.fog = null; setGodModeEnabled(true); });
    await p2.fill('#seed', '52');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 52, null, {timeout:15000});
    await p2.click('#play');
    await p2.waitForFunction(() => !!state.session, null, {timeout:15000});
    const before = await p2.evaluate(() => {
      const who = thisTabSeat();
      return {
        session: state.session.id,
        maze: state.maze.id,
        who,
        at: Object.assign({}, state.session.positions[who]),
      };
    });
    await p2.evaluate(() => { state.stomp = null; });
    await p2.route('**/api/v1/session/*/move', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.fulfill({
        status: 200,
        headers: {'content-type': 'application/json'},
        body: 'true',
      });
    });
    await p2.evaluate(() => move(thisTabSeat(), 0, 1));
    await p2.fill('#seed', '53');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 53, null, {timeout:20000});
    await p2.click('#play');
    await p2.waitForFunction(() => !!state.session, null, {timeout:15000});
    await p2.waitForTimeout(1800);
    const lateHop = await p2.evaluate(() => {
      const who = thisTabSeat();
      const at = who && state.session && state.session.positions[who];
      return {
        session: state.session && state.session.id,
        maze: state.maze && state.maze.id,
        who,
        at: at && Object.assign({}, at),
        fog: !!state.fog,
      };
    });
    await p2.close();
    const statusOk = lateFog.fog && !lateFog.session
        && lateFog.seen.some(t => /fog:/.test(t))
        && lateFog.seen.every(t => !/blocked/.test(t));
    // New seat stays at its own start, not the old hop (0, +1).
    const stayed = lateHop.at && before.at
        && !(lateHop.at.row === before.at.row && lateHop.at.col === before.at.col + 1);
    const hopOk = !lateHop.fog && lateHop.session && lateHop.session !== before.session
        && lateHop.maze !== before.maze && stayed;
    const ok = src && statusOk && hopOk;
    return [ok, ok ? 'late move discarded; fog status and new seat kept'
        : JSON.stringify({src, lateFog, lateHop, before}).slice(0, 220)];
  });

  await check('N28. late /live or /traffic after Generate does not bind the new maze', async () => {
    // Old body: bringToLife / simulateTraffic POSTed then always
    // disabled the button and armed a poller. onMutation logged the
    // tick and could re-enable #live after refreshLivingMaze discarded.
    // Discard after the POST / refresh when maze id no longer matches.
    // Fog stays — living+fog is honest (N19 / Q2).
    const src = await page.evaluate(() => {
      const life = bringToLife.toString();
      const lifePost = life.indexOf('/live');
      const mut = onMutation.toString();
      const mutRefresh = mut.indexOf('await refreshLivingMaze');
      const traf = simulateTraffic.toString();
      const trafPost = traf.indexOf('/traffic');
      const pulse = onTrafficPulse.toString();
      const pulseRefresh = pulse.indexOf('await refreshLivingMaze');
      const fog = startFog.toString();
      return lifePost >= 0 && life.indexOf('mazeId') >= 0
          && life.indexOf('mazeId') < lifePost
          && life.indexOf('state.maze.id !== mazeId', lifePost) > lifePost
          && life.indexOf('$("live").disabled = true')
              > life.indexOf('state.maze.id !== mazeId', lifePost)
          && !life.includes('if (state.fog)')
          && mut.indexOf('mazeId') >= 0
          && mut.indexOf('mazeId') < mut.indexOf('log("state"')
          && mutRefresh > mut.indexOf('log("state"')
          && mut.indexOf('state.maze.id !== mazeId', mutRefresh) > mutRefresh
          && mut.indexOf('$("live").disabled = false')
              > mut.indexOf('state.maze.id !== mazeId', mutRefresh)
          && !mut.includes('if (state.fog)')
          && trafPost >= 0 && traf.indexOf('mazeId') >= 0
          && traf.indexOf('mazeId') < trafPost
          && traf.indexOf('state.maze.id !== mazeId', trafPost) > trafPost
          && traf.indexOf('$("traffic").disabled = true')
              > traf.indexOf('state.maze.id !== mazeId', trafPost)
          && !traf.includes('if (state.fog)')
          && pulse.indexOf('mazeId') >= 0
          && pulse.indexOf('mazeId') < pulse.indexOf('log("state"')
          && pulseRefresh > pulse.indexOf('log("state"')
          && pulse.indexOf('state.maze.id !== mazeId', pulseRefresh) > pulseRefresh
          && pulse.indexOf('$("traffic").disabled = false')
              > pulse.indexOf('state.maze.id !== mazeId', pulseRefresh)
          && !pulse.includes('if (state.fog)')
          && !fog.includes('state.tour = null');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '61');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 61, null, {timeout:15000});
    const first = await p2.evaluate(() => state.maze.id);
    await p2.route('**/api/v1/maze/*/live*', async route => {
      if (route.request().method() !== 'POST') return route.continue();
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.click('#live');
    await p2.fill('#seed', '62');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 62, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const lateLive = await p2.evaluate(() => ({
      live: document.getElementById('live').disabled,
      poll: !!state.livePoll,
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
    }));
    await p2.unroute('**/api/v1/maze/*/live*');
    await p2.route('**/api/v1/maze/*/traffic', async route => {
      if (route.request().method() !== 'POST') return route.continue();
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.click('#traffic');
    await p2.fill('#seed', '63');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 63, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const lateTraffic = await p2.evaluate(() => ({
      traffic: document.getElementById('traffic').disabled,
      poll: !!state.trafficPoll,
      seed: state.maze && state.maze.seed,
    }));
    await p2.unroute('**/api/v1/maze/*/traffic');
    // Settled tick for the maze we left must not log or re-enable #live
    // after adopt already armed the new maze (or a subsequent Bring).
    const beforeTick = await p2.evaluate(() => document.getElementById('log').innerText);
    await p2.evaluate(() => { document.getElementById('live').disabled = true; });
    await p2.evaluate((oldId) => onMutation({
      mazeId: oldId,
      tick: 9,
      wallsOpened: 2,
      wallsClosed: 0,
      deadEndsRemaining: 1,
      settled: true,
    }), first);
    await p2.waitForTimeout(400);
    const lateTick = await p2.evaluate((before) => ({
      live: document.getElementById('live').disabled,
      logged: document.getElementById('log').innerText.slice(before.length),
      seed: state.maze && state.maze.seed,
    }), beforeTick);
    await p2.close();
    const ok = src && !lateLive.live && !lateLive.poll && lateLive.seed === 62
        && lateLive.id !== first
        && !lateTraffic.traffic && !lateTraffic.poll && lateTraffic.seed === 63
        && lateTick.live && !/tick 9/.test(lateTick.logged) && lateTick.seed === 63;
    return [ok, ok ? 'late live/traffic discarded; new maze stayed unbound'
        : JSON.stringify({src, lateLive, lateTraffic, lateTick, first}).slice(0, 220)];
  });

  await check('N29. late campaign hazard /live after Generate does not bind the new maze', async () => {
    // Old body: playStage POSTed hazard /live / /traffic then always
    // disabled #live and armed startLivePolling. Generate mid-flight
    // bound the maze now on screen. Discard after those POSTs when
    // maze id no longer matches the stage. Fog stays — living+fog
    // is honest (N19 / Q2 / N28).
    const src = await page.evaluate(() => {
      const s = playStage.toString();
      const post = s.indexOf('method: "POST"');
      const discard = s.indexOf('state.maze.id !== stage.mazeId', post);
      const hazard = s.slice(s.indexOf('for (const hazard'));
      return post >= 0 && discard > post
          && s.indexOf('$("live").disabled = true') > discard
          && s.indexOf('startLivePolling') > discard
          && !hazard.includes('if (state.fog)');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.click('#campaign');
    await p2.waitForFunction(() => state.campaign && state.stageIndex === 0
        && !!document.querySelector('#campaignBox a[data-stage="4"]'), null, {timeout:40000});
    await p2.route('**/api/v1/maze/*/live*', async route => {
      if (route.request().method() !== 'POST') return route.continue();
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.route('**/api/v1/maze/*/traffic', async route => {
      if (route.request().method() !== 'POST') return route.continue();
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    const liveInFlight = p2.waitForRequest(r =>
        r.method() === 'POST' && /\/maze\/[^/]+\/live/.test(r.url()), {timeout: 40000});
    await p2.evaluate(() => document.querySelector('#campaignBox a[data-stage="4"]').click());
    await liveInFlight;
    const stageId = await p2.evaluate(() => state.maze && state.maze.id);
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '64');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 64, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const late = await p2.evaluate(() => ({
      live: document.getElementById('live').disabled,
      poll: !!state.livePoll,
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
    }));
    await p2.unroute('**/api/v1/maze/*/live*');
    await p2.unroute('**/api/v1/maze/*/traffic');
    await p2.close();
    const ok = src && !late.live && !late.poll && late.seed === 64 && late.id !== stageId;
    return [ok, ok ? 'late campaign hazard discarded; generated maze stayed unbound'
        : JSON.stringify({src, late, stageId}).slice(0, 220)];
  });

  await check('N46. campaign hazard is not POSTed after Generate already replaced the stage', async () => {
    // Old body: N29 discarded the UI bind after /live. Generate that
    // already won the canvas still started the stage you left.
    // Gate before the first hazard POST. After-POST discard stays.
    const src = await page.evaluate(() => {
      const s = playStage.toString();
      const play = s.indexOf('await play()');
      const gate = s.indexOf('state.maze.id !== stage.mazeId', play);
      const loop = s.indexOf('for (const hazard');
      const post = s.indexOf('method: "POST"');
      const loopGate = s.indexOf('state.maze.id !== stage.mazeId', loop);
      return play >= 0 && gate > play && gate < post
          && loop > gate && loopGate > loop && loopGate < post
          && !s.slice(loop).includes('if (state.fog)');
    });
    return [src, src ? 'hazard POST gated on the stage still being on screen'
        : 'N46 source pin failed'];
  });

  await check('N47. Identify 503 wait does not GET /fingerprint after Generate left the maze', async () => {
    // Old body: fingerprintWhenReady retried the old id for 60s.
    // identifyGenerator discarded the paint (N30); the wait still
    // minted work. Abort before the next GET when fog or maze id
    // no longer matches.
    const src = await page.evaluate(() => {
      const s = fingerprintWhenReady.toString();
      const id = s.indexOf('state.maze.id !== id');
      const get = s.indexOf('api(`/maze/${id}/fingerprint`)');
      return id >= 0 && id < get && s.includes('state.fog') && s.includes('return null');
    });
    return [src, src ? 'warming loop aborts when the maze on screen changed'
        : 'N47 source pin failed'];
  });

  await check('N48. leftover wall-block flash does not restore old status after Generate', async () => {
    // Old body: flashStatus restored `prev` after 900ms. Generate
    // already wrote the new line; the leftover put the old session
    // text on a maze that no longer has that seat. Clear the timer
    // before adopt / leave / play / fog write status.
    const src = await page.evaluate(() => {
      const pin = fn => {
        const s = fn.toString();
        const clear = s.indexOf('clearTimeout(statusFlashTimer)');
        const write = s.indexOf('$("status").textContent');
        return clear >= 0 && write >= 0 && clear < write;
      };
      return pin(adoptMaze) && pin(leaveMaze) && pin(play) && pin(startFog);
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '61');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 61, null, {timeout:15000});
    await p2.click('#play');
    await p2.waitForFunction(() => !!state.session, null, {timeout:15000});
    const late = await p2.evaluate(async () => {
      flashStatus('blocked — that way is a wall');
      document.getElementById('seed').value = '62';
      document.getElementById('generate').click();
      const start = Date.now();
      while (Date.now() - start < 15000) {
        if (state.maze && state.maze.seed === 62 && !state.session) break;
        await new Promise(r => setTimeout(r, 40));
      }
      await new Promise(r => setTimeout(r, 1000));
      return {
        seed: state.maze && state.maze.seed,
        session: !!state.session,
        status: document.getElementById('status').textContent,
      };
    });
    await p2.close();
    const ok = src && late.seed === 62 && !late.session
        && late.status.includes('arrow keys move once a session is open')
        && !late.status.includes('blocked')
        && !late.status.includes('session ');
    return [ok, ok ? 'leftover flash did not restore the old session line'
        : JSON.stringify({src, late}).slice(0, 220)];
  });

  await check('N49. leftover solve rAF does not write progress after Generate', async () => {
    // Old body: animateSearch kept stepping after adoptMaze zeroed
    // path. A leftover frame wrote searchProgress / pathProgress
    // onto the maze now on screen and could finish a new reveal.
    const src = await page.evaluate(() => {
      const s = animateSearch.toString();
      const r = animateRace.toString();
      const a = adoptMaze.toString();
      const gen = s.indexOf('const gen = ++animGen');
      const guard = s.indexOf('if (gen !== animGen) return');
      const prog = s.indexOf('state.pathProgress = Math.max');
      return gen >= 0 && guard > gen && guard < prog
          && r.includes('const gen = ++animGen')
          && r.includes('if (gen !== animGen) return')
          && a.includes('animGen++');
    });
    return [src, src ? 'stale solve / race frames return after leave'
        : 'N49 source pin failed'];
  });

  await check('N50. Hunt drops leftover Compare / Hardest overlays', async () => {
    // Old body: startTour set state.tour and left Compare / Analyze /
    // Hardest / Lens armed. A leftover compare hover painted a solver
    // path over the Held-Karp corridor; leftover hardest was a second
    // walk that is not the score. Fog already drops these (N16).
    const src = await page.evaluate(() => {
      const s = startTour.toString();
      const discard = s.indexOf('state.maze.id !== mazeId');
      const box = s.indexOf('$("compareBox").innerHTML = ""');
      const play = s.indexOf('await play()');
      return discard >= 0 && box > discard && box < play
          && s.indexOf('state.hardest = null') > discard
          && s.indexOf('state.path = null') > discard
          && s.includes('state.analysis = null')
          && s.includes('state.lens = null')
          && s.includes('animGen++')
          && !s.includes('state.tour = null');
    });
    return [src, src ? 'Hunt empties leftover theory overlays before play'
        : 'N50 source pin failed'];
  });

  await check('N51. Solve after spectate does not keep the opener leftover-writable', async () => {
    // Old body: leaveSpectate only cleared readOnly. Solve / Analyze
    // after a watch kept the opener's session, so arrows POSTed
    // /move on a walk this tab only watched. Drop the leftover
    // seat when we were watching and have not taken one.
    const src = await page.evaluate(() => {
      const s = leaveSpectate.toString();
      const j = join.toString();
      const watch = s.indexOf('state.readOnly');
      const drop = s.indexOf('state.session = null');
      const seat = j.indexOf('state.seat');
      const leave = j.indexOf('leaveSpectate()');
      return watch >= 0 && drop > watch && s.includes('state.seat')
          && s.includes('resubscribe()')
          && seat >= 0 && leave > seat;
    });
    return [src, src ? 'watch leave drops the leftover opener seat'
        : 'N51 source pin failed'];
  });

  await check('N52. Solve after spectate does not leave a leftover #session= hash', async () => {
    // Old body: N51 dropped the seat; the bar still said #session=,
    // so refresh reminted a watch this tab already left. Pin #maze=
    // when the canvas remains. leaveMaze nulls maze first so that
    // write cannot fight History.
    const src = await page.evaluate(() => {
      const s = leaveSpectate.toString();
      const drop = leaveMaze.toString();
      const sess = s.indexOf('state.session = null');
      const keep = s.indexOf('if (state.maze)');
      const pin = s.indexOf('pinHash()');
      return sess >= 0 && keep > sess && pin > keep
          && drop.indexOf('state.maze = null') < drop.indexOf('leaveSpectate()')
          && !drop.includes('pinHash()');
    });
    return [src, src ? 'watch leave pins #maze= when the canvas remains'
        : 'N52 source pin failed'];
  });

  await check('N53. Race / Compare drop leftover Hunt coins', async () => {
    // Old body: Hunt dropped leftover Compare / Hardest (N50);
    // Race / Compare left tourWalk armed. Leftover coins painted
    // under the arena or a compare hover. Drop after maze-id
    // discard. startFog still must not null tour (N17).
    const src = await page.evaluate(() => {
      const race = raceSolvers.toString();
      const cmp = compareSolvers.toString();
      const fog = startFog.toString();
      const hunt = startTour.toString();
      const dR = race.lastIndexOf('state.maze.id !== mazeId');
      const tR = race.indexOf('state.tour = null');
      const sR = race.indexOf('state.race =');
      const dC = cmp.lastIndexOf('state.maze.id !== mazeId');
      const tC = cmp.indexOf('state.tour = null');
      const bC = cmp.lastIndexOf('$("compareBox")');
      return dR >= 0 && tR > dR && tR < sR && race.includes('state.hardest = null')
          && dC >= 0 && tC > dC && tC < bC && cmp.includes('state.hardest = null')
          && !fog.includes('state.tour = null')
          && !hunt.includes('state.tour = null');
    });
    return [src, src ? 'Race / Compare empty leftover hunt overlays'
        : 'N53 source pin failed'];
  });

  await check('N59. Hardest drops leftover Hunt coins and Race lanes', async () => {
    // Old body: Race / Compare dropped leftover Hunt (N53);
    // Hardest left tourWalk and leftover arena armed. Leftover
    // coins / leftover lanes painted over the cruel route.
    const src = await page.evaluate(() => {
      const h = hardestRoute.toString();
      const fog = startFog.toString();
      const d = h.lastIndexOf('state.maze.id !== mazeId');
      const t = h.indexOf('state.tour = null');
      const r = h.indexOf('state.race = null');
      const p = h.indexOf('state.path = null');
      const set = h.indexOf('state.hardest = h');
      return d >= 0 && t > d && t < set && r > t && r < set
          && p > r && p < set && h.includes('animGen++')
          && !fog.includes('state.tour = null');
    });
    return [src, src ? 'Hardest empties leftover hunt and arena'
        : 'N59 source pin failed'];
  });

  await check('N64. Hardest drops leftover sibling theory remints', async () => {
    // Old body: N63 dropped siblings on theory writes; Hardest
    // left leftover cuts reminting GET /analysis under gold.
    const src = await page.evaluate(() => {
      const h = hardestRoute.toString();
      const fog = startFog.toString();
      const d = h.lastIndexOf('state.maze.id !== mazeId');
      const a = h.indexOf('state.analysis = null');
      const f = h.indexOf('state.field = null');
      const set = h.indexOf('state.hardest = h');
      return d >= 0 && a > d && a < set && f > a && f < set
          && h.includes('state.lens = null')
          && h.includes('state.fingerprint = null')
          && !fog.includes('state.tour = null');
    });
    return [src, src ? 'Hardest empties leftover sibling theory'
        : 'N64 source pin failed'];
  });

  await check('N60. theory writes drop leftover Race lanes', async () => {
    // Old body: Hardest dropped leftover arena (N59); Analyze /
    // Identify / heat / sanctuaries / lens left Race armed.
    // Leftover lanes painted over the theory they asked for.
    const src = await page.evaluate(() => {
      const fog = startFog.toString();
      const hunt = startTour.toString();
      const after = (fn, write) => {
        const s = fn.toString();
        const d = s.lastIndexOf('state.maze.id !== mazeId');
        const r = s.indexOf('state.race = null');
        const w = s.indexOf(write);
        return d >= 0 && r > d && r < w && s.includes('animGen++')
            && !s.includes('state.tour = null');
      };
      return after(analyzeStructure, 'state.analysis = a')
          && after(identifyGenerator, 'state.fingerprint = f')
          && after(distanceHeatMap, 'state.field = f')
          && after(placeSanctuaries, 'state.sanctuaries = s')
          && after(heuristicLens, 'state.lens = l')
          && !fog.includes('state.tour = null')
          && !hunt.includes('state.tour = null');
    });
    return [src, src ? 'theory writes empty leftover arena'
        : 'N60 source pin failed'];
  });

  await check('N61. theory writes drop leftover Hardest walk', async () => {
    // Old body: N60 dropped leftover Race; Hardest stayed.
    // Leftover gold painted over the theory; a living tick
    // reminted GET /hardest-route.
    const src = await page.evaluate(() => {
      const fog = startFog.toString();
      const hunt = startTour.toString();
      const after = (fn, write) => {
        const s = fn.toString();
        const d = s.lastIndexOf('state.maze.id !== mazeId');
        const h = s.indexOf('state.hardest = null');
        const w = s.indexOf(write);
        return d >= 0 && h > d && h < w
            && !s.includes('state.tour = null');
      };
      return after(analyzeStructure, 'state.analysis = a')
          && after(identifyGenerator, 'state.fingerprint = f')
          && after(distanceHeatMap, 'state.field = f')
          && after(placeSanctuaries, 'state.sanctuaries = s')
          && after(heuristicLens, 'state.lens = l')
          && !fog.includes('state.tour = null')
          && !hunt.includes('state.tour = null');
    });
    return [src, src ? 'theory writes empty leftover hardest'
        : 'N61 source pin failed'];
  });

  await check('N62. theory writes drop leftover Compare hover', async () => {
    // Old body: N60 / N61 dropped leftover Race / Hardest;
    // Compare hover stayed. Leftover solver path painted
    // over the theory; a living tick reminted POST /solve.
    const src = await page.evaluate(() => {
      const fog = startFog.toString();
      const hunt = startTour.toString();
      const after = (fn, write) => {
        const s = fn.toString();
        const d = s.lastIndexOf('state.maze.id !== mazeId');
        const c = s.indexOf('caption === "compare"');
        const p = s.indexOf('state.path = null');
        const w = s.indexOf(write);
        return d >= 0 && c > d && c < w && p > c && p < w
            && !s.includes('state.tour = null');
      };
      return after(analyzeStructure, 'state.analysis = a')
          && after(identifyGenerator, 'state.fingerprint = f')
          && after(distanceHeatMap, 'state.field = f')
          && after(placeSanctuaries, 'state.sanctuaries = s')
          && after(heuristicLens, 'state.lens = l')
          && !fog.includes('state.tour = null')
          && !hunt.includes('state.tour = null');
    });
    return [src, src ? 'theory writes empty leftover Compare hover'
        : 'N62 source pin failed'];
  });

  await check('N63. theory writes drop leftover sibling remints', async () => {
    // Old body: Field dropped sanctuaries / lens; Analyze left
    // leftover heat reminting GET /distance-field. Field left
    // leftover cuts reminting GET /analysis.
    const src = await page.evaluate(() => {
      const fog = startFog.toString();
      const hunt = startTour.toString();
      const after = (fn, write, drop) => {
        const s = fn.toString();
        const d = s.lastIndexOf('state.maze.id !== mazeId');
        const g = s.indexOf(drop);
        const w = s.indexOf(write);
        return d >= 0 && g > d && g < w
            && !s.includes('state.tour = null');
      };
      return after(analyzeStructure, 'state.analysis = a', 'state.field = null')
          && after(identifyGenerator, 'state.fingerprint = f', 'state.analysis = null')
          && after(distanceHeatMap, 'state.field = f', 'state.analysis = null')
          && after(placeSanctuaries, 'state.sanctuaries = s', 'state.analysis = null')
          && after(heuristicLens, 'state.lens = l', 'state.analysis = null')
          && !fog.includes('state.tour = null')
          && !hunt.includes('state.tour = null');
    });
    return [src, src ? 'theory writes empty leftover sibling remints'
        : 'N63 source pin failed'];
  });

  await check('N54. leaveMaze restores catalog generate defaults', async () => {
    // Old body: leaveMaze dropped the canvas and left the adopted
    // recipe. Back onto "" / #generator= then Generate rebuilt
    // the maze the bar no longer names. Restore catalog defaults.
    const src = await page.evaluate(() => {
      const s = leaveMaze.toString();
      const rows = s.indexOf('$("rows").value = 21');
      const seed = s.indexOf('$("seed").value = ""');
      const braid = s.indexOf('$("braid").value = "0"');
      const draw = s.indexOf('drawEmpty');
      return rows >= 0 && rows < draw && seed > rows && seed < draw
          && braid > seed && braid < draw
          && s.includes('syncBraid("braid")')
          && s.includes('$("cols").value = 31')
          && !s.includes('pinHash()');
    });
    return [src, src ? 'leaveMaze clears the leftover adopted recipe'
        : 'N54 source pin failed'];
  });

  await check('N55. Open session drops leftover Race lanes', async () => {
    // Old body: play() seated a session and left Race armed.
    // Leftover arena painted over the walk. Drop after the
    // session POST discard. Hunt calls play() after installing
    // tour — must not null tour.
    const src = await page.evaluate(() => {
      const s = play.toString();
      const post = s.indexOf('/maze/${mazeId}/session');
      const discard = s.indexOf('state.maze.id !== mazeId', post);
      const race = s.indexOf('state.race = null', discard);
      const seat = s.indexOf('state.session =', discard);
      return post >= 0 && discard > post && race > discard && race < seat
          && s.includes('animGen++')
          && !s.includes('state.tour = null');
    });
    return [src, src ? 'Play empties leftover arena before seating'
        : 'N55 source pin failed'];
  });

  await check('N56. leaving a watch drops leftover Hunt coins', async () => {
    // Old body: N51 dropped the seat and kept the spectated tour.
    // Solve / Fog then Play scored a new walk against leftover
    // waypoints; a living tick asked tourFor with no seat.
    const src = await page.evaluate(() => {
      const s = leaveSpectate.toString();
      const fog = startFog.toString();
      const drop = s.indexOf('state.session = null');
      const tour = s.indexOf('state.tour = null');
      const keep = s.indexOf('if (state.maze)');
      return drop >= 0 && tour > drop && tour < keep
          && !fog.includes('state.tour = null');
    });
    return [src, src ? 'watch leave drops leftover spectated hunt'
        : 'N56 source pin failed'];
  });

  await check('N57. Open session drops leftover Compare hover', async () => {
    // Old body: play() dropped Race (N55) and left Compare armed.
    // Hover painted a leftover solver path over the walk.
    const src = await page.evaluate(() => {
      const s = play.toString();
      const post = s.indexOf('/maze/${mazeId}/session');
      const discard = s.indexOf('state.maze.id !== mazeId', post);
      const cap = s.indexOf('caption === "compare"', discard);
      const path = s.indexOf('state.path = null', discard);
      const box = s.indexOf('$("compareBox").innerHTML = ""', discard);
      const seat = s.indexOf('state.session =', discard);
      return post >= 0 && discard > post && cap > discard && path > cap
          && box > path && box < seat
          && !s.includes('state.tour = null');
    });
    return [src, src ? 'Play empties leftover Compare hover before seating'
        : 'N57 source pin failed'];
  });

  await check('N58. Open session drops leftover Hardest walk', async () => {
    // Old body: play() dropped Race / Compare and left Hardest
    // armed. Leftover gold painted over the seat; a living tick
    // reminted it.
    const src = await page.evaluate(() => {
      const s = play.toString();
      const post = s.indexOf('/maze/${mazeId}/session');
      const discard = s.indexOf('state.maze.id !== mazeId', post);
      const cap = s.indexOf('caption === "hardest"', discard);
      const drop = s.indexOf('state.hardest = null', discard);
      const box = s.indexOf('$("compareBox").innerHTML = ""', discard);
      const seat = s.indexOf('state.session =', discard);
      return post >= 0 && discard > post && cap > discard && drop > cap
          && box > drop && box < seat
          && !s.includes('state.tour = null');
    });
    return [src, src ? 'Play empties leftover Hardest before seating'
        : 'N58 source pin failed'];
  });

  await check('N30. late /solve after Generate does not paint the maze now on screen', async () => {
    // Old body: solve / race / compare POSTed /solve then painted
    // after only a fog check. Generate mid-flight applied the old
    // expansions / #compareBox onto the maze now on screen; Race
    // / Compare could POST later /solve against the new id.
    // Discard after the fetch when maze id no longer matches.
    // Fog discard stays (N18). startFog still must not null tour.
    const src = await page.evaluate(() => {
      const after = (fn) => {
        const s = fn.toString();
        const id = s.indexOf('mazeId');
        const w = s.indexOf('await ');
        const f = s.indexOf('if (state.fog)', w);
        const d = s.indexOf('state.maze.id !== mazeId', w);
        return id >= 0 && id < w && w >= 0 && f > w && d > w;
      };
      const race = raceSolvers.toString();
      const cmp = compareSolvers.toString();
      const fog = startFog.toString();
      return after(solve) && after(raceSolvers) && after(compareSolvers)
          && after(analyzeStructure) && after(identifyGenerator)
          && after(distanceHeatMap) && after(heuristicLens)
          && race.includes('/maze/${mazeId}/solve')
          && !race.slice(race.indexOf('const mazeId')).includes('/maze/${state.maze.id}/solve')
          && cmp.includes('/maze/${mazeId}/solve')
          && !cmp.slice(cmp.indexOf('const mazeId')).includes('/maze/${state.maze.id}/solve')
          && !fog.includes('state.tour = null');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0
        && document.getElementById('solver').options.length > 1
        && document.getElementById('rival').options.length > 1, null, {timeout:20000});
    await p2.evaluate(() => {
      const s = document.getElementById('solver');
      const r = document.getElementById('rival');
      if (s.value === r.value) {
        const i = [...r.options].findIndex(o => o.value !== s.value);
        if (i >= 0) r.selectedIndex = i;
      }
    });
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '71');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 71, null, {timeout:15000});
    const first = await p2.evaluate(() => state.maze.id);
    await p2.route('**/api/v1/maze/*/solve/**', async route => {
      if (route.request().method() !== 'POST') return route.continue();
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.click('#solve');
    await p2.fill('#seed', '72');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 72, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const lateSolve = await p2.evaluate(() => ({
      path: !!(state.path && state.path.length),
      expansions: (state.expansions || []).length,
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
    }));
    await p2.click('#race');
    await p2.fill('#seed', '73');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 73, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const lateRace = await p2.evaluate(() => ({
      race: !!state.race,
      path: !!(state.path && state.path.length),
      seed: state.maze && state.maze.seed,
    }));
    await p2.click('#compare');
    await p2.fill('#seed', '74');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 74, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const lateCompare = await p2.evaluate(() => ({
      box: document.getElementById('compareBox').innerText.trim(),
      caption: state.caption,
      path: !!(state.path && state.path.length),
      seed: state.maze && state.maze.seed,
    }));
    await p2.close();
    const ok = src && !lateSolve.path && lateSolve.expansions === 0
        && lateSolve.seed === 72 && lateSolve.id !== first
        && !lateRace.race && !lateRace.path && lateRace.seed === 73
        && lateCompare.box === '' && lateCompare.caption == null
        && !lateCompare.path && lateCompare.seed === 74;
    return [ok, ok ? 'late /solve discarded; generated maze stayed unpainted'
        : JSON.stringify({src, lateSolve, lateRace, lateCompare, first}).slice(0, 220)];
  });

  await check('N31. late /tour after Generate does not play or paint the maze now on screen', async () => {
    // Old body: startTour / hardest / sanctuaries / ASCII fetched then
    // painted after only a fog check. Generate mid-flight assigned the
    // old tour / route / rings / dump onto the maze now on screen; Hunt
    // could even play() a session on the new id. Discard after the
    // fetch when maze id no longer matches. Fog discard stays (N18).
    const src = await page.evaluate(() => {
      const after = (fn) => {
        const s = fn.toString();
        const id = s.indexOf('mazeId');
        const w = s.indexOf('await ');
        const f = s.indexOf('if (state.fog)', w);
        const d = s.indexOf('state.maze.id !== mazeId', w);
        return id >= 0 && id < w && w >= 0 && f > w && d > w;
      };
      const hunt = startTour.toString();
      return after(startTour) && after(hardestRoute) && after(placeSanctuaries)
          && after(showAscii)
          && hunt.includes('/maze/${mazeId}/tour')
          && hunt.indexOf('await play()') > hunt.indexOf('state.maze.id !== mazeId');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '81');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 81, null, {timeout:15000});
    const first = await p2.evaluate(() => state.maze.id);
    await p2.route('**/api/v1/maze/*/tour*', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.click('#tour');
    await p2.fill('#seed', '82');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 82, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const lateHunt = await p2.evaluate(() => ({
      tour: !!state.tour,
      session: !!state.session,
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
    }));
    await p2.route('**/api/v1/maze/*/hardest-route*', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.click('#hardest');
    await p2.fill('#seed', '83');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 83, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const lateHardest = await p2.evaluate(() => ({
      hardest: !!state.hardest,
      box: document.getElementById('compareBox').innerText.trim(),
      caption: state.caption,
      seed: state.maze && state.maze.seed,
    }));
    await p2.route('**/api/v1/maze/*/sanctuaries*', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.click('#sanctuaries');
    await p2.fill('#seed', '84');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 84, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const lateSanct = await p2.evaluate(() => ({
      sanctuaries: !!state.sanctuaries,
      box: document.getElementById('compareBox').innerText.trim(),
      caption: state.caption,
      seed: state.maze && state.maze.seed,
    }));
    await p2.route('**/api/v1/maze/*', async route => {
      const req = route.request();
      const path = new URL(req.url()).pathname;
      const accept = (req.headers()['accept'] || '').toLowerCase();
      const dump = req.method() === 'GET'
          && /\/api\/v1\/maze\/[^/]+$/.test(path)
          && accept.includes('text/plain');
      if (!dump) {
        await route.continue();
        return;
      }
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.click('#ascii');
    await p2.fill('#seed', '85');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 85, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const lateAscii = await p2.evaluate(() => ({
      shown: !document.getElementById('asciiOut').hidden,
      text: document.getElementById('asciiOut').textContent,
      seed: state.maze && state.maze.seed,
    }));
    await p2.close();
    const ok = src && !lateHunt.tour && !lateHunt.session
        && lateHunt.seed === 82 && lateHunt.id !== first
        && !lateHardest.hardest && lateHardest.box === '' && lateHardest.caption == null
        && lateHardest.seed === 83
        && !lateSanct.sanctuaries && lateSanct.box === '' && lateSanct.caption == null
        && lateSanct.seed === 84
        && !lateAscii.shown && !lateAscii.text && lateAscii.seed === 85;
    return [ok, ok ? 'late /tour discarded; generated maze stayed unpainted'
        : JSON.stringify({src, lateHunt, lateHardest, lateSanct, lateAscii, first}).slice(0, 220)];
  });

  await check('N32. late Open session after Generate does not seat the maze now on screen', async () => {
    // Old body: play() POSTed /session after only a fog check.
    // Generate mid-flight pinned #session= and wrote the seat
    // onto the generated maze. Capture maze id; discard after
    // the POST when maze id no longer matches. Fog discard stays (N20).
    const src = await page.evaluate(() => {
      const s = play.toString();
      const id = s.indexOf('mazeId');
      const w = s.indexOf('await ');
      const f = s.indexOf('if (state.fog)', w);
      const d = s.indexOf('state.maze.id !== mazeId', w);
      const apply = s.indexOf('state.session =');
      return id >= 0 && id < w && w >= 0 && f > w && d > w
          && apply > d
          && s.includes('/maze/${mazeId}/session')
          && s.indexOf('pinHash()') > d
          && s.indexOf('summonGhost()') > d;
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '86');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 86, null, {timeout:15000});
    const first = await p2.evaluate(() => state.maze.id);
    await p2.route('**/api/v1/maze/*/session*', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.click('#play');
    await p2.fill('#seed', '87');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 87, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const after = await p2.evaluate(() => ({
      session: !!state.session,
      hash: location.hash,
      ghost: !!state.ghostTimer,
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
    }));
    await p2.close();
    const ok = src && !after.session && !/session=/.test(after.hash)
        && !after.ghost && after.seed === 87 && after.id !== first;
    return [ok, ok ? 'late session discarded; generated maze stayed unseated'
        : JSON.stringify({src, after, first}).slice(0, 220)];
  });

  await check('N33. late spectator /session/{id}/tour after Generate does not paint the maze now on screen', async () => {
    // Old body: hydrateSpectatorOverlays GETs /session/{id}/tour then
    // always wrote state.tour. Generate / Fog / a new #session=
    // mid-flight painted the old hunt onto the maze now on screen.
    // Capture session + maze id; discard after the GET. Sibling
    // summonGhost is the same discard. startFog still must not
    // null tour (N17). Progress only — not GET /maze/{id}/tour.
    const src = await page.evaluate(() => {
      const s = hydrateSpectatorOverlays.toString();
      const sid = s.indexOf('sessionId');
      const mid = s.indexOf('mazeId');
      const w = s.indexOf('await ');
      const f = s.indexOf('if (state.fog)', w);
      const dSess = s.indexOf('state.session.id !== sessionId', w);
      const dMaze = s.indexOf('state.maze.id !== mazeId', w);
      const write = s.indexOf('state.tour =');
      const ghost = s.indexOf('summonGhost()');
      return sid >= 0 && sid < w && mid >= 0 && mid < w && w >= 0
          && f > w && dSess > w && dMaze > w && write > dMaze
          && ghost > write
          && s.includes('/session/${sessionId}/tour')
          && !s.includes('/maze/${');
    });
    await page.fill('#rows', '15'); await page.fill('#cols', '15'); await page.fill('#seed', '88');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 88, null, {timeout:15000});
    await page.click('#tour');
    await page.waitForFunction(() => state.tour && state.session
        && state.tour.path && state.tour.path.length > 1, null, {timeout:20000});
    const host = await page.evaluate(() => ({
      sid: state.session.id,
      maze: state.maze.id,
      coins: (state.tour.waypoints || []).length,
    }));
    const p2 = await ctx.newPage();
    await p2.route('**/api/v1/session/*/tour*', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.goto(`http://localhost:8080/#session=${host.sid}`, { waitUntil: 'domcontentloaded' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.waitForFunction(() => state.session && state.maze, null, {timeout:20000});
    await p2.fill('#seed', '89');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 89, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const lateGen = await p2.evaluate(() => ({
      tour: !!state.tour,
      session: !!state.session,
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
    }));
    const p3 = await ctx.newPage();
    await p3.route('**/api/v1/session/*/tour*', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p3.goto(`http://localhost:8080/#session=${host.sid}`, { waitUntil: 'domcontentloaded' });
    await p3.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p3.waitForFunction(() => state.session && state.maze, null, {timeout:20000});
    await p3.click('#fog');
    await p3.waitForFunction(() => state.fog && state.fog.seen, null, {timeout:15000});
    await p3.waitForTimeout(1800);
    const lateFog = await p3.evaluate(() => ({
      tour: !!state.tour,
      fog: !!(state.fog && state.fog.agentId),
      session: !!state.session,
    }));
    await page.fill('#seed', '90');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 90, null, {timeout:15000});
    await page.click('#play');
    await page.waitForFunction(() => !!state.session, null, {timeout:15000});
    const sidB = await page.evaluate(() => state.session.id);
    const p4 = await ctx.newPage();
    await p4.route('**/api/v1/session/*/tour*', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p4.goto(`http://localhost:8080/#session=${host.sid}`, { waitUntil: 'domcontentloaded' });
    await p4.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p4.waitForFunction(id => state.session && state.session.id === id, host.sid,
        {timeout:20000});
    await p4.evaluate(id => { location.hash = 'session=' + id; }, sidB);
    await p4.waitForFunction(id => state.session && state.session.id === id, sidB,
        {timeout:20000});
    await p4.waitForTimeout(1800);
    const lateSess = await p4.evaluate(() => ({
      tour: !!state.tour,
      sid: state.session && state.session.id,
    }));
    await p2.close();
    await p3.close();
    await p4.close();
    const ok = src && !lateGen.tour && !lateGen.session
        && lateGen.seed === 89 && lateGen.id !== host.maze
        && !lateFog.tour && lateFog.fog && !lateFog.session
        && !lateSess.tour && lateSess.sid === sidB;
    return [ok, ok ? 'late spectator /tour discarded; new maze / fog / session stayed unpainted'
        : JSON.stringify({src, lateGen, lateFog, lateSess, host, sidB}).slice(0, 220)];
  });

  await check('N34. late spectator /session/{id} poll after Generate does not re-seat the maze now on screen', async () => {
    // Old body: spectate poll GETs /session/{id} then always
    // adoptSessionView. Generate / Fog / a new #session= mid-flight
    // wrote the old walk onto the maze now on screen. Capture
    // session + maze id; discard after the GET. startFog still
    // must not null tour (N17). Must not GET /maze.
    const src = await page.evaluate(() => {
      const s = startSpectatePolling.toString();
      const poll = s.indexOf('setInterval');
      const sid = s.indexOf('sessionId', poll);
      const mid = s.indexOf('mazeId', poll);
      const w = s.indexOf('await ', poll);
      const f = s.indexOf('if (state.fog)', w);
      const dSess = s.indexOf('state.session.id !== sessionId', w);
      const dMaze = s.indexOf('state.maze.id !== mazeId', w);
      const write = s.indexOf('adoptSessionView', dMaze);
      const body = s.slice(poll);
      return poll >= 0 && sid >= 0 && sid < w && mid >= 0 && mid < w && w >= 0
          && f > w && dSess > w && dMaze > w && write > dMaze
          && body.includes('/session/${sessionId}')
          && !body.includes('/session/${state.session.id}')
          && !body.includes('/maze/${');
    });
    await page.fill('#rows', '15'); await page.fill('#cols', '15'); await page.fill('#seed', '91');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 91, null, {timeout:15000});
    await page.click('#tour');
    await page.waitForFunction(() => state.tour && state.session
        && state.tour.path && state.tour.path.length > 1, null, {timeout:20000});
    const host = await page.evaluate(() => ({
      sid: state.session.id,
      maze: state.maze.id,
    }));
    const delaySidSnapshot = async (target, sid) => {
      await target.route('**/ws', route => route.abort());
      await target.route('**/ws/**', route => route.abort());
      await target.route('**/api/v1/session/*', async route => {
        const url = new URL(route.request().url());
        const parts = url.pathname.split('/').filter(Boolean);
        const extra = parts[4];
        if (route.request().method() === 'GET' && !extra && parts[3] === sid) {
          await new Promise(r => setTimeout(r, 1200));
        }
        await route.continue();
      });
    };
    const p2 = await ctx.newPage();
    await delaySidSnapshot(p2, host.sid);
    await p2.goto(`http://localhost:8080/#session=${host.sid}`, { waitUntil: 'domcontentloaded' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.waitForFunction(() => state.session && state.maze && state.spectatePoll,
        null, {timeout:20000});
    await p2.waitForTimeout(1100);
    await p2.fill('#seed', '92');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 92, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const lateGen = await p2.evaluate(() => ({
      session: !!state.session,
      readOnly: !!state.readOnly,
      trails: Object.keys(state.trails || {}).length,
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
    }));
    const p3 = await ctx.newPage();
    await delaySidSnapshot(p3, host.sid);
    await p3.goto(`http://localhost:8080/#session=${host.sid}`, { waitUntil: 'domcontentloaded' });
    await p3.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p3.waitForFunction(() => state.session && state.maze && state.spectatePoll,
        null, {timeout:20000});
    await p3.waitForFunction(() => state.tour, null, {timeout:15000});
    await p3.waitForTimeout(1100);
    await p3.click('#fog');
    await p3.waitForFunction(() => state.fog && state.fog.seen, null, {timeout:15000});
    await p3.waitForTimeout(1800);
    const lateFog = await p3.evaluate(() => ({
      tour: !!state.tour,
      fog: !!(state.fog && state.fog.agentId),
      session: !!state.session,
    }));
    await page.fill('#seed', '93');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 93, null, {timeout:15000});
    await page.click('#play');
    await page.waitForFunction(() => !!state.session, null, {timeout:15000});
    const sidB = await page.evaluate(() => state.session.id);
    const p4 = await ctx.newPage();
    await delaySidSnapshot(p4, host.sid);
    await p4.goto(`http://localhost:8080/#session=${host.sid}`, { waitUntil: 'domcontentloaded' });
    await p4.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p4.waitForFunction(id => state.session && state.session.id === id && state.spectatePoll,
        host.sid, {timeout:20000});
    await p4.waitForTimeout(1100);
    await p4.evaluate(id => { location.hash = 'session=' + id; }, sidB);
    await p4.waitForFunction(id => state.session && state.session.id === id, sidB,
        {timeout:20000});
    await p4.waitForTimeout(1800);
    const lateSess = await p4.evaluate(() => ({
      sid: state.session && state.session.id,
    }));
    await p2.close();
    await p3.close();
    await p4.close();
    const ok = src && !lateGen.session && !lateGen.readOnly && lateGen.trails === 0
        && lateGen.seed === 92 && lateGen.id !== host.maze
        && lateFog.tour && lateFog.fog && !lateFog.session
        && lateSess.sid === sidB;
    return [ok, ok ? 'late spectator /session poll discarded; new maze / fog / session stayed unseated'
        : JSON.stringify({src, lateGen, lateFog, lateSess, host, sidB}).slice(0, 220)];
  });

  await check('N43. spectate poll after STOMP connects does not rewind a hop the frame already applied', async () => {
    // Old body: poll armed because !state.stomp, then kept GETting
    // /session after CONNECT. A snapshot that left before the next
    // move overwrote applyMove. After the GET, discard when
    // state.stomp is set; connectStomp clears the leftover interval.
    const src = await page.evaluate(() => {
      const s = startSpectatePolling.toString();
      const poll = s.indexOf('setInterval');
      const w = s.indexOf('await ', poll);
      const stomp = s.indexOf('if (state.stomp)', w);
      const clear = s.indexOf('clearInterval(state.spectatePoll)', stomp);
      const write = s.indexOf('adoptSessionView', stomp);
      const c = connectStomp.toString();
      const assign = c.indexOf('state.stomp = client');
      const drop = c.indexOf('clearInterval(state.spectatePoll)', assign);
      const resub = c.indexOf('resubscribe()', drop);
      return poll >= 0 && w > poll && stomp > w && clear > stomp && write > clear
          && assign >= 0 && drop > assign && resub > drop;
    });
    return [src, src ? 'spectate poll discards after STOMP; CONNECT drops the leftover interval'
        : 'N43 source pin failed'];
  });

  await check('N44. living / traffic poll after STOMP connects does not write an older grid', async () => {
    // Old body: pollers armed because !state.stomp kept GET /maze
    // after CONNECT. A snapshot that left before the next tick
    // overwrote the /state frame. Pollers stop when state.stomp
    // is set; poll-initiated refresh discards after the GET.
    const src = await page.evaluate(() => {
      const live = startLivePolling.toString();
      const traf = startTrafficPolling.toString();
      const refresh = refreshLivingMaze.toString();
      const c = connectStomp.toString();
      const assign = c.indexOf('state.stomp = client');
      return live.includes('state.stomp') && live.includes('refreshLivingMaze(true)')
          && traf.includes('state.stomp') && traf.includes('refreshLivingMaze(true)')
          && refresh.includes('fromPoll && state.stomp')
          && assign >= 0
          && c.indexOf('clearInterval(state.livePoll)', assign) > assign
          && c.indexOf('clearInterval(state.trafficPoll)', assign) > assign;
    });
    return [src, src ? 'living/traffic polls discard after STOMP; CONNECT drops leftover intervals'
        : 'N44 source pin failed'];
  });

  await check('N45. STOMP drop re-arms living / traffic / spectate polls CONNECT cleared', async () => {
    // Old body: CONNECT dropped the fallbacks; disconnect left
    // them dead. A watched walk or eroding stage froze. After
    // state.stomp = null, re-arm the same polls — no POST /live.
    const src = await page.evaluate(() => {
      const c = connectStomp.toString();
      const lost = c.indexOf('STOMP connection lost');
      const nul = c.lastIndexOf('state.stomp = null', lost);
      const arm = c.indexOf('armStompFallbacks()', lost);
      const a = armStompFallbacks.toString();
      return lost >= 0 && nul >= 0 && nul < lost && arm > lost
          && a.includes('startSpectatePolling()')
          && a.includes('startLivePolling(')
          && a.includes('startTrafficPolling(')
          && !a.includes('/live')
          && !a.includes('POST');
    });
    return [src, src ? 'disconnect re-arms STOMP-less polls; no second /live'
        : 'N45 source pin failed'];
  });

  await check('N35. late confirmWin / tour status after Generate do not paint the maze now on screen', async () => {
    // Old body: confirmWin GETs /session/{id} then declareWin after
    // only a fog + session-exists check. refreshTourStatus painted
    // hunt status the same way. Generate + a new Play mid-flight
    // wrote a win (status, leaderboard, campaign) onto the maze now
    // on screen. Capture session + maze id; discard after the GET.
    // tourVerdict sibling too. N24 fog discard stays. startFog
    // still must not null tour (N17). Must not GET /maze.
    const src = await page.evaluate(() => {
      const w = confirmWin.toString();
      const t = refreshTourStatus.toString();
      const v = tourVerdict.toString();
      const d = declareWin.toString();
      const wGet = w.indexOf('/session/${sessionId}');
      const wFog = w.indexOf('if (state.fog)', wGet);
      const wSess = w.indexOf('state.session.id !== sessionId', wGet);
      const wMaze = w.indexOf('state.maze.id !== mazeId', wGet);
      const tGet = t.indexOf('/session/${sessionId}/tour');
      const tFog = t.indexOf('if (state.fog)', tGet);
      const tSess = t.indexOf('state.session.id !== sessionId', tGet);
      const tMaze = t.indexOf('state.maze.id !== mazeId', tGet);
      const vAwait = v.indexOf('await refreshTourStatus()');
      const vFog = v.indexOf('if (state.fog)', vAwait);
      const vMaze = v.indexOf('state.maze.id !== mazeId', vAwait);
      const dTv = d.indexOf('tourVerdict');
      const dMaze = d.indexOf('state.maze.id !== mazeId', dTv);
      const fogSrc = startFog.toString();
      return w.indexOf('const sessionId') >= 0 && w.indexOf('const mazeId') > w.indexOf('const sessionId')
          && w.indexOf('const mazeId') < wGet && wGet >= 0 && wFog > wGet && wSess > wFog
          && wMaze > wSess && w.indexOf('declareWin', wMaze) > wMaze
          && !w.includes('/session/${state.session.id}') && !w.includes('/maze/${')
          && t.indexOf('const sessionId') >= 0 && t.indexOf('const mazeId') > t.indexOf('const sessionId')
          && t.indexOf('const mazeId') < tGet && tGet >= 0 && tFog > tGet && tSess > tFog
          && tMaze > tSess && t.indexOf('$("status")', tMaze) > tMaze
          && !t.includes('/session/${state.session.id}') && !t.includes('/maze/${')
          && !t.includes('tourFor')
          && v.indexOf('const mazeId') >= 0 && v.indexOf('const mazeId') < vAwait
          && vAwait >= 0 && vFog > vAwait && vMaze > vFog && !v.includes('/maze/${')
          && d.indexOf('const mazeId') >= 0 && d.indexOf('const mazeId') < d.indexOf('state.won =')
          && dTv >= 0 && dMaze > dTv && d.indexOf('$("status")', dMaze) > dMaze
          && !fogSrc.includes('state.tour = null');
    });
    const p2 = await ctx.newPage();
    await p2.route('**/api/v1/session/**', async route => {
      const url = new URL(route.request().url());
      const segs = url.pathname.split('/').filter(Boolean);
      const method = route.request().method();
      const isTour = method === 'GET' && segs[segs.length - 1] === 'tour';
      const isSnap = method === 'GET' && segs.length === 4 && segs[2] === 'session';
      if (!isTour && !isSnap) return route.continue();
      await new Promise(r => setTimeout(r, 1200));
      if (isTour) {
        await route.fulfill({
          status: 200,
          headers: {'content-type': 'application/json'},
          body: JSON.stringify({
            remaining: [], total: 3, collected: 3, complete: true, walked: 10, optimal: 8,
          }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({completed: true, completedBy: 'web'}),
      });
    });
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '94');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 94, null, {timeout:15000});
    await p2.click('#play');
    await p2.waitForFunction(() => !!state.session, null, {timeout:15000});
    const first = await p2.evaluate(() => ({sid: state.session.id, maze: state.maze.id}));
    await p2.evaluate(() => {
      state.tour = state.tour || {waypoints: [], optimalCost: 0};
      void refreshTourStatus();
      void confirmWin('web');
    });
    await p2.fill('#seed', '95');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 95, null, {timeout:20000});
    await p2.click('#play');
    await p2.waitForFunction(() => !!state.session, null, {timeout:15000});
    await p2.evaluate(() => {
      state.tour = state.tour || {waypoints: [], optimalCost: 0};
    });
    await p2.waitForTimeout(1800);
    const after = await p2.evaluate(() => ({
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
      sid: state.session && state.session.id,
      won: state.won,
      status: document.getElementById('status').textContent,
      tour: !!state.tour,
    }));
    await p2.close();
    const painted = /reached the goal|waypoint hunt|waypoints collected/i.test(after.status || '');
    const ok = src && after.seed === 95 && after.id !== first.maze
        && after.sid && after.sid !== first.sid && !after.won && !painted;
    return [ok, ok ? 'late win/hunt discarded; generated maze stayed unpainted'
        : JSON.stringify({src, after, first}).slice(0, 220)];
  });

  await check('N37. late ghost after Generate + Play does not seat the maze now on screen', async () => {
    // Old body: summonGhost GETs /ghost then armed state.ghost
    // after only fog + session-exists. Generate + Play mid-flight
    // seated the old recording on the maze now on screen. Capture
    // maze id; discard after the GET. Fog discard stays (N25).
    // Ghost is maze-bound, not seat-bound. startFog still must
    // not null tour (N17). Must not GET /maze.
    const src = await page.evaluate(() => {
      const s = summonGhost.toString();
      const id = s.indexOf('mazeId');
      const get = s.indexOf('/ghost');
      const fog = s.indexOf('if (state.fog)', get);
      const maze = s.indexOf('state.maze.id !== mazeId', get);
      const fogSrc = startFog.toString();
      return id >= 0 && id < get && get >= 0 && fog > get
          && s.indexOf('if (!state.session)', get) > fog
          && maze > fog
          && s.indexOf('state.ghost =', maze) > maze
          && s.includes('/maze/${mazeId}/ghost')
          && !s.includes('/maze/${state.maze.id}')
          && !s.includes('state.session.id !== sessionId')
          && !fogSrc.includes('state.tour = null');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '96');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 96, null, {timeout:15000});
    const first = await p2.evaluate(() => state.maze.id);
    await p2.route('**/api/v1/maze/*/ghost', async route => {
      const url = route.request().url();
      await new Promise(r => setTimeout(r, 1200));
      if (url.includes(first)) {
        await route.fulfill({
          status: 200,
          headers: {'content-type': 'application/json'},
          body: JSON.stringify({
            mazeId: first,
            playerName: 'speedrunner',
            score: 42,
            elapsedMs: 1500,
            moves: [{to: {row: 0, col: 1}, tMs: 200}],
          }),
        });
        return;
      }
      await route.fulfill({status: 404, body: ''});
    });
    await p2.click('#play');
    await p2.waitForFunction(() => !!state.session, null, {timeout:15000});
    await p2.fill('#seed', '97');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 97, null, {timeout:20000});
    await p2.click('#play');
    await p2.waitForFunction(() => !!state.session, null, {timeout:15000});
    await p2.waitForTimeout(1800);
    const after = await p2.evaluate(() => ({
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
      session: !!state.session,
      ghost: state.ghost && state.ghost.name,
      timer: !!state.ghostTimer,
    }));
    await p2.close();
    const ok = src && after.seed === 97 && after.id !== first
        && after.session && after.ghost !== 'speedrunner' && !after.timer;
    return [ok, ok ? 'late ghost discarded; generated maze stayed unseated'
        : JSON.stringify({src, after, first}).slice(0, 220)];
  });

  await check('N38. late living GET /agent after Play does not re-arm fog', async () => {
    // Old body: refreshLivingMaze GETs /agent then applyFogView after
    // only maze-id stale(). Play on the same maze leaves fog; maze
    // id still matches, so a late GET recreates state.fog on the
    // session walk. Capture agent id; discard after the GET.
    // Fog path still must not GET /maze. startFog still must not
    // null tour (N17). Living-under-fog stays (N19 / Q2).
    const src = await page.evaluate(() => {
      const s = refreshLivingMaze.toString();
      const id = s.indexOf('agentId');
      const get = s.indexOf('await api(`/agent/${');
      const discard = s.indexOf('state.fog.agentId !== agentId', get);
      const apply = s.indexOf('applyFogView', discard);
      const snap = s.indexOf('await api(`/maze/${forMaze}`)');
      const fogSrc = startFog.toString();
      return id >= 0 && id < get && get >= 0 && discard > get && apply > discard
          && !s.slice(s.indexOf('if (state.fog)'), snap).includes('await api(`/maze/${forMaze}`)')
          && !fogSrc.includes('state.tour = null');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '98');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 98, null, {timeout:15000});
    const mazeId = await p2.evaluate(() => state.maze.id);
    await p2.click('#fog');
    await p2.waitForFunction(() => !!(state.fog && state.fog.agentId), null, {timeout:20000});
    await p2.route('**/api/v1/agent/*', async route => {
      const path = new URL(route.request().url()).pathname;
      const view = route.request().method() === 'GET'
          && /\/api\/v1\/agent\/[^/]+$/.test(path);
      if (!view) {
        await route.continue();
        return;
      }
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.evaluate(() => { refreshLivingMaze(); });
    await p2.click('#play');
    await p2.waitForFunction(() => !!state.session && !state.fog, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const after = await p2.evaluate(() => ({
      fog: !!state.fog,
      session: !!state.session,
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
    }));
    await p2.close();
    const ok = src && !after.fog && after.session && after.seed === 98 && after.id === mazeId;
    return [ok, ok ? 'late /agent discarded; Play kept the session walk'
        : JSON.stringify({src, after, mazeId}).slice(0, 220)];
  });

  await check('N40. late Daily / Breed / #maze= after Generate does not steal the maze now on screen', async () => {
    // Old body: Daily / Breed / Campaign / #maze= discarded adopt
    // after only fog. Generate mid-flight replaced the canvas, then
    // the late fetch still adoptMaze'd over it. Capture maze id
    // (or none); discard when fog is on OR the canvas id changed.
    // playStage compares the canvas it left, not the stage maze —
    // re-clicking the same rung still adopts. Fog discard stays
    // (N21 / N22). Generate stays fog-only — it is the winner.
    const src = await page.evaluate(() => {
      const after = (fn, write) => {
        const s = fn.toString();
        const id = s.indexOf('mazeId');
        const fetch = s.indexOf('await ');
        const fog = s.indexOf('if (state.fog)', fetch);
        const discard = s.indexOf('state.maze.id !== mazeId', fetch);
        const out = s.indexOf(write, Math.max(fog, discard));
        return id >= 0 && id < fetch && fog > fetch && discard > fog && out > discard;
      };
      const stage = playStage.toString();
      const from = loadFromHash.toString();
      const mazeGet = from.indexOf('await api(`/maze/${h.maze}`)');
      const mazeIdCap = from.indexOf('const mazeId', from.indexOf('if (h.maze)'));
      const mazeDiscard = from.indexOf('if (state.fog)', mazeGet);
      const mazeIdDiscard = from.indexOf('state.maze.id !== mazeId', mazeGet);
      const mazeAdopt = from.indexOf('adoptMaze', mazeIdDiscard);
      const gen = generate.toString();
      return after(loadDaily, 'adoptMaze')
          && after(crossbreed, 'adoptMaze')
          && after(loadCampaign, 'state.campaign')
          && after(playStage, 'adoptMaze')
          && stage.indexOf('state.maze.id !== mazeId') < stage.indexOf('adoptMaze')
          && stage.indexOf('state.maze.id !== stage.mazeId') > stage.indexOf('adoptMaze')
          && mazeIdCap >= 0 && mazeIdCap < mazeGet && mazeGet >= 0
          && mazeDiscard > mazeGet && mazeIdDiscard > mazeDiscard && mazeAdopt > mazeIdDiscard
          && !gen.includes('state.maze.id !== mazeId');
    });
    const p2 = await ctx.newPage();
    await p2.goto('http://localhost:8080/', { waitUntil: 'networkidle' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '99');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 99, null, {timeout:15000});
    const first = await p2.evaluate(() => state.maze.id);
    await p2.route('**/api/v1/maze/daily', async route => {
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.click('#daily');
    await p2.fill('#seed', '100');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 100, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const lateDaily = await p2.evaluate(() => ({
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
      daily: !!state.dailyId,
    }));
    await p2.unroute('**/api/v1/maze/daily');
    await p2.route(`**/api/v1/maze/${first}`, async route => {
      if (route.request().method() !== 'GET') {
        await route.continue();
        return;
      }
      await new Promise(r => setTimeout(r, 1200));
      await route.continue();
    });
    await p2.evaluate(id => { location.hash = 'maze=' + id; }, first);
    await p2.fill('#seed', '101');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 101, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const lateHash = await p2.evaluate(() => ({
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
    }));
    await p2.close();
    const ok = src && lateDaily.seed === 100 && lateDaily.id !== first && !lateDaily.daily
        && lateHash.seed === 101 && lateHash.id !== first;
    return [ok, ok ? 'late Daily / #maze= discarded; generated maze stayed'
        : JSON.stringify({src, lateDaily, lateHash, first}).slice(0, 220)];
  });

  await check('N41. late #session= after Generate does not steal the maze now on screen', async () => {
    // Old body: spectate GET /session then adoptMaze before the fog
    // check, and had no maze-id discard. Generate mid-flight
    // replaced the canvas, then the late GET still adopted over it.
    // Capture maze id (or none); skip adoptMaze / adoptSessionView
    // when fog is on or the canvas id changed. Leave-fog-before-fetch
    // stays (N22). Stay until join lands. Poll discard stays (N34).
    const src = await page.evaluate(() => {
      const s = spectate.toString();
      const id = s.indexOf('mazeId');
      const fetch = s.indexOf('await ');
      const fog = s.indexOf('if (state.fog)', fetch);
      const discard = s.indexOf('state.maze.id !== mazeId', fetch);
      const adopt = s.indexOf('adoptMaze', Math.max(fog, discard));
      const view = s.indexOf('adoptSessionView', adopt);
      const drop = s.indexOf('state.fog = null');
      const sess = s.indexOf('/session/');
      return id >= 0 && id < fetch && fetch >= 0
          && fog > fetch && discard > fog && adopt > discard && view > adopt
          && drop >= 0 && drop < sess;
    });
    await page.fill('#rows', '15'); await page.fill('#cols', '15'); await page.fill('#seed', '102');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 102, null, {timeout:15000});
    await page.click('#play');
    await page.waitForFunction(() => !!state.session, null, {timeout:15000});
    const host = await page.evaluate(() => ({
      sid: state.session.id,
      maze: state.maze.id,
    }));
    const p2 = await ctx.newPage();
    await p2.route('**/api/v1/session/*', async route => {
      const url = new URL(route.request().url());
      const parts = url.pathname.split('/').filter(Boolean);
      const extra = parts[4];
      if (route.request().method() === 'GET' && !extra && parts[3] === host.sid) {
        await new Promise(r => setTimeout(r, 1200));
      }
      await route.continue();
    });
    const pending = p2.waitForRequest(r => {
      const url = new URL(r.url());
      const parts = url.pathname.split('/').filter(Boolean);
      return r.method() === 'GET' && parts[2] === 'session' && parts[3] === host.sid && !parts[4];
    });
    await p2.goto(`http://localhost:8080/#session=${host.sid}`, { waitUntil: 'domcontentloaded' });
    await p2.waitForFunction(() => document.getElementById('generator').options.length > 0,
        null, {timeout:20000});
    await pending;
    await p2.fill('#rows', '15'); await p2.fill('#cols', '15'); await p2.fill('#seed', '103');
    await p2.click('#generate');
    await p2.waitForFunction(() => state.maze && state.maze.seed === 103, null, {timeout:20000});
    await p2.waitForTimeout(1800);
    const late = await p2.evaluate(() => ({
      seed: state.maze && state.maze.seed,
      id: state.maze && state.maze.id,
      session: !!state.session,
      readOnly: !!state.readOnly,
    }));
    await p2.close();
    const ok = src && late.seed === 103 && late.id !== host.maze
        && !late.session && !late.readOnly;
    return [ok, ok ? 'late #session= discarded; generated maze stayed'
        : JSON.stringify({src, late, host}).slice(0, 220)];
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

  await check('Q2. fog locks overlays that draw() would swallow', async () => {
    await page.fill('#rows','15'); await page.fill('#cols','15'); await page.fill('#seed','8');
    await page.click('#generate');
    await page.waitForFunction(() => state.maze && state.maze.seed === 8, null, {timeout:15000});
    await page.click('#fog');
    await page.waitForFunction(() => state.fog && state.fog.seen, null, {timeout:15000});
    const d = await page.evaluate(() => ({
      solve: document.getElementById('solve').disabled,
      analyze: document.getElementById('analyze').disabled,
      fingerprint: document.getElementById('fingerprint').disabled,
      ascii: document.getElementById('ascii').disabled,
      live: document.getElementById('live').disabled,
    }));
    await page.click('#generate');
    await page.waitForFunction(() => !state.fog && !document.getElementById('solve').disabled,
        null, {timeout:15000});
    return [d.solve && d.analyze && d.fingerprint && d.ascii && !d.live,
        `overlays locked; live still armed`];
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
      gen: document.getElementById('generator').value,
    }));
    await p2.close();
    return [/generator=prims/.test(q.path) && q.sel === 'prims' && q.gen === 'prims'
        && /generator=prims/.test(q.hash),
        `${q.sel}/${q.gen} via ${q.path} ${q.hash}`];
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
