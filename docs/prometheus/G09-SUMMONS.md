# G09 PRISM03 Prism Shard summon spirits (Prismheart demo)

Contest gap G09 (MINIGAME-CONTEST-20261019), owner prometheus.

- Rules: `tools/rpg_demo/summons.js`. It is pure, has no DOM, and also loads under Node. Each Warden in
  `data/rpg/prism-bosses.json` that drops "<Spirit> summon" becomes a spirit once that Warden is beaten. Spirits
  persist with the existing save, because the save already keeps the beaten Wardens.
- Battle: a SUMMON command is added after RUN, and it only appears once a spirit answers. The existing commands
  keep their places. Any standing hero can call an unlocked spirit. It costs MP (6 + level/3), strikes every foe
  with the Warden's element (power 20 + 2 x level; weak spot x2, same element x0.5) and answers once per battle.
  A Warden victory adds "THE SHARD HUMS. <SPIRIT> WILL ANSWER A SUMMON NOW."
- Sound (ear rules): each shard gets a three-note chord from the same 7 low D pentatonic bells as the
  Labyrinth Echo Bell gate (146.832-349.227 Hz). The notes are sine, low-passed at 1.2 kHz, gain 0.3, rolled
  110 ms apart, decaying over 1.6 s, through the demo's effects bus and limiter.
- Hooks: index.html loads `summons.js` and calls it from the battle menu, actions and drawing; all additions are
  additive. build_demo.py copies summons.js. bot.py learns SUMMON. `PRISM_DEMO.summons()` serves the tests.
- Test: `python tools/rpg_demo/summons_test.py DEMO_DIR` (18 checks).
- Realm guard: `PrismSummons.table(bosses, realm)` returns no spirits unless data.json `realm_key` is missing (the
  default Prism build) or is "prism". The display name `realm` ("Prismheart", "PortalRealm") is not used.
  index.html passes `D.realm_key`, so a Portal build (G08) gets no SUMMON command and no spirits, even though the hook is shared.
