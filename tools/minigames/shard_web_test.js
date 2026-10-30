// Headless parity: the browser core in web/shardring/index.html vs. fixtures from prism_shard.py.
// Usage: node shard_web_test.js <fixture.json>   (prints OK or exits 1)
"use strict";
const fs = require("fs"), path = require("path");
const html = fs.readFileSync(path.join(__dirname, "web", "shardring", "index.html"), "utf8");
const src = html.match(/<script id="shardring-core">([\s\S]*?)<\/script>/)[1];
const mod = { exports: {} };
new Function("module", src)(mod);
const S = mod.exports;
const fx = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
let fail = 0;
for (const c of fx.cases) {
  const g = new S.Game(c.seed, c.difficulty);
  const draws = [g.current, g.next];
  const r = S.PyRandom(`shardring:${c.seed}:${c.difficulty}`);
  const seq = []; for (let i = 0; i < c.sequence.length; i++) seq.push(r.choice(g.hues));
  if (JSON.stringify(seq) !== JSON.stringify(c.sequence)) { console.log("sequence mismatch", c.seed, c.difficulty); fail++; }
  if (JSON.stringify(draws) !== JSON.stringify(c.sequence.slice(0, 2))) { console.log("start mismatch", c.seed); fail++; }
  const moves = [];
  while (!g.over) { const f = g.greedyMove(); moves.push(f); g.place(f); }
  const st = g.status();
  if (JSON.stringify(moves) !== JSON.stringify(c.moves) || JSON.stringify(st) !== JSON.stringify(c.final)) {
    console.log("game mismatch", c.seed, c.difficulty); fail++;
  }
}
if (S.sha512(Array.from(Buffer.from("abc"))).map(b => b.toString(16).padStart(2, "0")).join("") !== fx.sha512_abc) { console.log("sha512 mismatch"); fail++; }
console.log(fail ? `FAIL ${fail}` : `OK ${fx.cases.length} cases`);
process.exit(fail ? 1 : 0);
