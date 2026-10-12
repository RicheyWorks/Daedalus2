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

To connect rd-studio, implement `StudioArranger` (Java) against a service that meets this contract:

```
GET {studio-url}/arrange?source=token:123&genre=jazz&studio=true
200 {"url": "https://…/token-123-jazz-studio.mp3"}     # pre-rendered / cached render
404                                                     # not rendered yet: jukebox plays the original
```

The input is rd-studio's note stream for the seed or token (`events.py`), plus genre and studio flags. The output is a
cacheable audio URL. Renders are deterministic per (source, genre, studio), so they can be pre-rendered offline (GPU path)
and served statically.
