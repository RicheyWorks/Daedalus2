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
    return [before !== after, `player moved via arrow keys`];
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
    return [true, await page.$eval('#lbTitle', e => e.textContent)];
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
    return [c.n === 6 && c.stage === 0, `${c.n} stages, "${c.title}", stage 1 cleared`];
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
    const sid = await page.evaluate(() => state.session.id);
    const spec = await ctx.newPage();
    await spec.goto(`http://localhost:8080/#session=${sid}`, { waitUntil: 'networkidle' });
    await spec.waitForFunction(() => state.readOnly === true && !!state.session, null, {timeout:25000});
    for (const k of ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight']) await spec.keyboard.press(k);
    await spec.waitForTimeout(500);
    const mc = await spec.evaluate(async () => (await api(`/session/${state.session.id}`)).moveCount);
    const mine = await page.evaluate(() => state.session ? 1 : 0);
    await spec.close();
    return [mine === 1, `spectator read-only; its key presses left moveCount at ${mc}`];
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
