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

## Hardening (rd-studio r4, indexer, relay guard, sound engine)

**rd-studio r4 contract** (`CHANGES_FOR_FLEX.md`). `HttpStudioArranger` talks to it:
- `/arrange` 200 → READY (`key` has no extension; the extension comes from `url`; the key must match
  `(e\d{5}|t\d{5})__[a-z]+__(studio|plain)__[a-z]+-v\d{1,3}-n(off|\d{2})__[A-Za-z0-9.-]+\.(mp3|flac)`).
  202 → RENDERING with `jobId` + `retryAfterMs`; the client plays the original and polls (bounded, backing off).
  404 = unknown source (final), 422 = failed QA (final, never retried), 400 = bad params, 503 = busy: the breaker
  opens for the Retry-After and, once half-open, `/ready` is probed before any `/arrange`.
- Only `seed:e\d{5}` and `token:0..49999` (no leading zeros) are sent; file seeds play their original without a call.
- Timeouts: connect 800 ms, request 1.5 s, audio stream 20 s. Retries only for refused connections and 502/504
  (2 retries, 60 ms jittered 0.5x–1.5x). Breaker: 3 failures → open 20 s. Requests coalesce; results cache
  (hit/unknown 10 min, failed QA 1 h, rendering = its Retry-After, down 5 s).
- `/health` + `/metrics` (`rd_studio_latency_ms{q="0.95"}`, `rd_studio_queue_depth`) feed `/config.studioHealth`
  (UP/DEGRADED/DOWN, engine, p95Ms, queue, lastError) and the panel's status chip.
- Render options on `/api/v1/jukebox/arrangement`: `format=mp3|flac` (24-bit FLAC), `preset=neutral|harman|crossfeed|warm|bass`,
  `vinyl=0..100` (snapped to 10s), `noise=off|-60..-30` (surface noise off by default). Anything else → 400.
- Audio proxy forwards If-None-Match, passes ETag/304 and the studio's immutable Cache-Control, sets audio/flac or
  audio/mpeg, and refuses or cuts anything over 32 MiB.
- `coat.png`: validated PNG (signature + IHDR size), ≤ 8 MB, cached by coat engine + hash + size; served with a sha256 ETag,
  304 on If-None-Match, `max-age=31536000, immutable`.

**Holder lookup at scale.** `TransferIndexer` follows `Transfer` logs from the deploy block (`DAEDALUS_JUKEBOX_DEPLOY_BLOCK`,
else binary search, else 0 on a non-archive node), `DAEDALUS_JUKEBOX_CONFIRMATIONS` (20) behind head, in chunks
(`DAEDALUS_JUKEBOX_LOG_CHUNK`, 5M; halves on range errors). It's reorg-safe: the last indexed block hash is re-checked
and a mismatch rebuilds. It's persisted atomically to `DAEDALUS_JUKEBOX_INDEX_FILE` and resumes. Until it's warm,
supply ≤ `DAEDALUS_JUKEBOX_SCAN_FALLBACK_MAX` (2000) uses the old scan, and larger supply answers 503 + Retry-After 30.
`DAEDALUS_JUKEBOX_RPC_URL` takes a comma list: failover, jittered backoff, Retry-After and JSON-RPC rate-limit errors honoured.

**Radio relay.** `RelayGuard` allows only http(s), ports 80/443/≥1024, no userinfo, no local names, and every resolved
address must be public (loopback, link-local/metadata, RFC1918, CGNAT, documentation, benchmarking, multicast, ULA and the v6
wrappers of these are refused). Redirects are followed by hand (≤ 3), each hop re-checked. Only audio/* or application/ogg
is relayed. Caps: 64 relays, 3 per listener, 4 h, 640 MiB, 20 s idle, 5 s connect; rate limit `jukeboxRelay` 20/min.
`DAEDALUS_JUKEBOX_RELAY_FAKE_IP_CIDRS` (default empty) is for sandboxes whose DNS answers every host with a fake IP
(e.g. 198.18.0.0/15): DNS names resolving there are allowed, and IP literals in that range are still refused.

**Sound engine** (`static/jukebox-audio.js`). Every source → 10-band EQ → tone filter → gain (low/med/high) →
**ear-safety limiter** (-10 dB, 20:1, 1 ms, fixed, frozen) → 0.89 ceiling → analyser → output. The chain is checked
every frame. Tampering is restored, and a bypass suspends audio. Output device via `setSinkId` where supported. Line-in via
`getUserMedia`. Keys tab: 2-octave keyboard, per-voice instrument (seed sample or synth), ADSR, brightness, wave, blend.
The voice schema for rd-studio isn't in r4, so `VOICE_SCHEMA_READY = false` (keys play live only). Token HTML still plays
in a sandboxed iframe outside the limiter, unless rd-studio has a `token:<id>` render (token 1 does).

**Load** (`tools/jukebox-load/load.py BASE secs panel arrange relay`).

## Limitations

- Holder lookup is a full `ownerOf` sweep (see above), which is not viable at mainnet scale without an indexer.
- rd-studio renders only the three cached engine seeds. Tokens fall back to their on-chain player.
- Radio Browser data quality varies: some local FM stations don't say "FM" anywhere and land in "Other local".
