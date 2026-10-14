# Gallery City: the memory mosaic expedition

Buckwild crew owner: `buckwild-sol`. Browser entry: `/gallery-city.html`; realm atlas: `/metaverse.html`.

The city remains the surviving fragment defined by ADR-035: five by five blocks, twelve named streets,
68 addressed parcels, downtown height 32 and outskirts height 20, an Origin spire and drone pad. The
browser visitor follows a proposed memory-mosaic story: survey streets and parcels, study actual maze
art, gather three local echoes and return to the spire before preparing a crossing.

## Source delivered

- `gallery-city-core.js`: deterministic visitor layout, validated server geometry, bounded path routing,
  parcel lookup, proximity-driven objectives and a versioned journal with validated restoration.
- `gallery-city.js`: canvas city exploration, keyboard/touch movement, tap routing, pan/zoom, nearby
  inspector, same-server artwork viewer, progress and storage. It reads `/api/v1/worlds`, then the mounted
  GALLERY world's `/gallery` and `/art` endpoints. No world is created or edited by opening this page.
- `gallery-city.html` and `.css`: responsive city and journal interface, accessible control labels,
  original code-native silhouettes and land status. No external assets or new dependencies.

The server response supplies actual parcel addresses, geometry, height limits, ownership and builder
labels. Visitor building silhouettes and collision are presentation, not an assertion about the world's
current cubes. The draft mirrors the fixed GalleryOps footprint but uses its own illustrative gallery
selection; it does not claim Java SplittableRandom parity. Missing server/gallery/art reads are visible.
Large server seeds that JavaScript cannot represent exactly are treated as instance labels, never used
to regenerate, sign or identify a deed. The typed visitor seed is checked against the signed 64-bit range.

Every journal is keyed by schema, source, world instance and seed. A restored journal filters invalid
parcel/street/echo identifiers, refuses invalid coordinates and preserves local prerequisites. Browser
storage refusal leaves the current visit in memory. Reset affects this visitor journal alone.

Art is loaded exclusively from the server's `/api/v1/art/maze/{seed}.png`; studying it requires a loaded
image and proximity to the selected gallery. Draft samples are labelled and do not claim placed frames.
Local surveys and recovered echoes grant no shared inventory, quest rewards, land claims or NFTs.

## Release and integration steps

1. Serve the claimed static files in the existing Spring application and accept the browser experience
   in the normal integration lane. This sprint has run no tests, builds or browser acceptance.
2. Bind expedition objectives to the authoritative quest/inventory system before any shared rewards;
   leave local visitor saves separate from authenticated land or party state.
3. Bind actual voxel collision and drone travel through the existing realm client/native owners.
4. Connect the canonical `(realm, number)` registry and parcel deed flow. Existing legacy island vouchers
   do not mint Gallery parcels. Reconcile transfers, builder grants and durable metadata.
5. Publish confirmed contract/network/metadata/supply and launch terms through the owner's release lane.

Current delivery stage: source written and reviewed by reading. Runtime behavior, native placement and
public NFT land release are pending. Existing source/editor/contract owners retain their lanes.
