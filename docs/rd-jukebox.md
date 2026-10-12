# rd-jukebox: the Reaction / Diffusion / Song jukebox

A jukebox prop stands on the first island of the realm (`/realm.html`). Tap it, or press **♪ Jukebox**.

- **Guest (no wallet):** plays the seed songs in `daedalus.jukebox.seed-songs-dir` (`name.mp3` + optional `name.webp` cover).
- **Wallet signed in (ADR-028 SIWE):** lists the RDSong tokens that wallet holds on Robinhood Chain and plays a token
  in **its own on-chain HTML** (`tokenHTML(id)`, the engine pinned to that token), framed in the panel.
- **Skin:** a Gray-Scott reaction-diffusion coat grown from the song's seed (`token:<id>` / `seed:<name>`), which
  evolves while the song plays. It is a deterministic stand-in: it is not the engine's exact coat (see open questions).
- **Genre (original/rock/jazz/reggae/orchestral) + studio quality:** routed through `/api/v1/jukebox/arrangement`.
  Stubbed today: it answers `available:false` and the original plays.

Read-only on chain: the server only makes `eth_call`s (`totalSupply`, `ownerOf`, `isRevealed`, `tokenHTML`), never signs or sends a transaction.

## Why it isn't a `MazePlugin`

The plugin SPI (`daedalus-plugin-api`) contributes maze generators/solvers, events and `worldCapabilities()`.
It can't add HTTP routes, static assets or realm props, and plugins are not Spring beans. So the jukebox is a
separate package instead (`com.daedalus.server.jukebox` + `JukeboxController` + `static/jukebox.js`). realm.js
gets only three hooks: it exposes `scene`, `camera` and `groundAt` on `window.daedalusRealm`, and it fires `realm:islands`.

## Config (`daedalus.jukebox.*`, env)

| key | env | default |
|---|---|---|
| enabled | `DAEDALUS_JUKEBOX_ENABLED` | `false` |
| chain-id | `DAEDALUS_JUKEBOX_CHAIN_ID` | `46630` (testnet; mainnet is 4663) |
| rpc-url | `DAEDALUS_JUKEBOX_RPC_URL` | `https://rpc.testnet.chain.robinhood.com` |
| contract | `DAEDALUS_JUKEBOX_CONTRACT` | `0x286562588c32692e49befd2f7ec628a6cbef7162` (testnet open-mint RDSong) |
| seed-songs-dir | `DAEDALUS_JUKEBOX_SEED_SONGS_DIR` | empty (no guest songs) |
| scan-batch / max-scan / cache-seconds | `DAEDALUS_JUKEBOX_SCAN_BATCH` … | 50 / 60000 / 30 |
| studio-url | `DAEDALUS_JUKEBOX_STUDIO_URL` | empty (stub) |

For mainnet, set chain-id 4663, a mainnet RPC (ideally a paid one) and the mainnet RDSong address. If the contract is empty, holders get an empty list rather than an error.

## Holder lookup and load

RDSong is ERC721A with no on-chain enumeration, so the server makes one batched `ownerOf` sweep over `[0, totalSupply)`
and caches it for `cache-seconds`. A crowd at the jukebox therefore costs one sweep per window. A rate limit or node error
inside a batch fails the request (HTTP 502) instead of being read as "not owned". At 50k supply a sweep is 1,000
batched calls, which is too many for a public RPC. Before mainnet, use a Transfer-log indexer or an
`ERC721AQueryable.tokensOfOwner` view.

## Security

- `/owned` takes the address from the signed-in principal (the SIWE subject), never from a parameter.
- Token HTML is served with `Content-Security-Policy: sandbox allow-scripts` and `X-Frame-Options: SAMEORIGIN`, and the
  iframe has `sandbox="allow-scripts"`. The token's script runs in an opaque origin and can't read the realm's JWT.
  Every other response keeps `X-Frame-Options: DENY` (`JukeboxFraming`).
- Seed files must match `[a-z0-9][a-z0-9-]*\.(mp3|webp)` inside the configured directory, so no path traversal is possible.
- `/owned` and `/tokens/{id}/html` are rate-limited per caller (`jukebox` limiter).

## rd-studio interface (for Prometheus)

`GET /api/v1/jukebox/arrangement?source=<seed:name|token:id>&genre=<original|rock|jazz|reggae|orchestral>&studio=<bool>`
→ `{source, genre, studio, available, url, note}`. When `available` is true, the jukebox plays `url` (an audio file,
e.g. MP3 or Opus) instead of the original.

`HttpStudioArranger` is the live implementation and is used when `DAEDALUS_JUKEBOX_STUDIO_URL` is set (for example
`http://127.0.0.1:8787`). With the variable empty, the stub plays the original song. Contract:

```
GET {studio-url}/arrange?source=seed:e00015&genre=jazz&studio=true
200 {"url": "/audio/<key>.mp3", "engine": "...", "key": "<key>", "note": "..."}   # rendered: available=true
404                                                                                 # not rendered: play the original
GET {studio-url}/health            # lists the cached engine seeds (e00015, e00084, e00165 × 5 genres today)
GET {studio-url}/audio/<key>.mp3   # key must match [a-z0-9_-]+__[a-z]+__(studio|plain)__[A-Za-z0-9.-]+
```

- The browser never talks to rd-studio directly. Audio is proxied at `/api/v1/jukebox/studio/audio/{key}` (whole
  files only; range requests are not supported), so the studio can stay on localhost and no CSP change is needed.
- `token:<id>` returns 404 for now, so tokens play their own on-chain HTML.
- Hits are cached for 10 minutes and misses for 15 seconds.

## Token coat (real genome)

`GET /tokens/{id}/hash` reads the RDSong `tokenHash(uint256)` view (`0xa3864397`). It is gated on reveal. Then:

- `/coat.png?hash=0x<64hex>&size=256|512|1024` is proxied from rd-studio's `/coat.png`. The client tiles it on the cabinet
  with `RepeatWrapping`.
- `/coat?hash=` returns the genome and traits, which set the material's roughness.

Seed songs, and tokens without a studio, keep the deterministic client-side Gray-Scott coat.

**Regex check:** `/tokenData\s*=\s*\{[^}]*?hash\s*:\s*["'](0x[0-9a-fA-F]{64})/` matches a real `tokenHTML(5)`
response (`window.tokenData={hash:"0x19227c7c…6ff19198",tokenId:"5",edition:"6009"}`). It extracts exactly the value
`tokenHash(5)` returns, and `RdSongReaderLiveTest` asserts this (`RD_JUKEBOX_LIVE=1`). The server uses the view
because it is cheaper and does not depend on the HTML layout.

## Radio (ported from ComputerPets)

The radio tab is a port of ComputerPets' house radio (`desktop/renderer/house-music.js`: `parseAreaPlace`,
`COUNTRY_CODES`, `parseStations`, `safeStream`, the scoring and merge; `desktop/main.cjs`: the Radio Browser fetch with
mirror fallback). It lives in `jukebox/radio/` (`RadioArea`, `RadioStation`, `RadioRanking`, `RadioService`,
`RadioBrowserDirectory`). Thanks to ComputerPets.

Additions over the original:

- Browser geolocation (opt-in "Near me" button) using Radio Browser's `geo_lat/geo_long/geo_distance` search.
- A typed place is remembered in localStorage.
- Strict local-FM-first ordering:
  1. **Local FM**: local and FM, where FM means the name or tags contain "FM" or an 87.5–108.0 frequency.
  2. **Other local**: AM, internet and unknown local stations.
  3. **More stations**: everything else.

  "Local" means within 120 km when coordinates are known. Otherwise the city (or state) must match the typed place and
  the country must match. Within the local tiers, stations are sorted by distance, then by the ComputerPets score.
- Graceful fallbacks:
  - No location: popular stations, with a note.
  - No local FM: a note is shown.
  - No results: a message is shown.
  - A dead stream is marked "off the air" and the next station plays.
- Stream safety: https streams play directly. http streams go through `/radio/stream/{id}`, which only relays stations
  the server itself listed (not arbitrary URLs) and only audio content types, with 64 concurrent relays and a 4-hour cap.
  This avoids mixed-content blocks and an open proxy.

## World-aware look

The panel is a native realm `.panel` that uses the realm CSS variables (`--panel`, `--line`, `--text`, `--dim`,
`--gold`, `--accent`). It sits under the `#top` card on the left, clear of the right-hand sidebar, and becomes a bottom
sheet at 720px and below. Accent colours and the cabinet materials come from the current world's block palette
(`realm.js` `COLORS`, exposed as `state.blockColors`). Sky Islands uses wood, log and blossom; Parcels uses road, paving
and neon; Bricks uses brick colours; Gallery uses stone, paving and lamp. Anything else falls back to Sky Islands. The
look is re-applied live when the world style changes.

## Limitations

- Holder lookup is a full `ownerOf` sweep (see above), which is not viable at mainnet scale without an indexer.
- rd-studio renders only the three cached engine seeds. Tokens fall back to their on-chain player.
- Radio Browser data quality varies: some local FM stations don't say "FM" anywhere and land in "Other local".
