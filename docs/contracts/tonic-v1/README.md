# TONIC 1: Java brew calculation to Unreal

POST `/api/v1/kennel/brew`, application/json request, text/plain success response.
The server packages the canonical `tools/islands/kennel-isle/tonics.json` at build time;
no working-directory-relative file or second recipe database is required.

All request fields are required: `herbs` (1–3 distinct known case-sensitive herb names),
`coat` (None, Spots, Stripes, Labyrinth), `drinker` (cane_corso, packMember, other),
`stage` (1–3), `charm` (boolean), `seed` (signed 64-bit integer). Native JSON writers must
preserve the integer seed exactly, without conversion through floating point.

Configure `daedalus.kennel.host-subject` to the verified JWT subject of the trusted engine.
Blank defaults deny all. Use the production JWT security chain; no anonymous dev bypass.
This endpoint is a pure calculation: it does not spend herbs, advance trough decay, enforce
companion ownership, or persist effects. The authoritative gameplay host must validate those
facts, choose the seed, consume inputs once, and apply the response once. Repeating a request
returns the same calculation, not an idempotent inventory transaction.

## Grammar

UTF-8 ASCII subset, LF output, single spaces, decimal numbers, no locale-dependent commas.
This final multiline grammar replaces the earlier unimplemented one-line suggestion.

```text
TONIC 1
brew <recipeId> <factor> <durationSec> <secondRoll> <mode> <breedChancePct>
mod <stat> <op> <value>
... zero or more additional mod lines ...
grant <ability>
... zero or more additional grant lines ...
end
```

Exactly one header, one brew line and final end line. Recipe/mod/grant order is canonical
recipe-file order. Identifiers are case-sensitive ASCII alphanumeric plus underscore;
mode is `overTime` or `pulse`; op is `add` or `mul`; secondRoll is 0 or 1. Factor is finite
0–2; duration is nonnegative seconds; breed chance is finite 0–100. Modifier values are
finite decimal numbers, already scaled by Java; do not multiply by factor again.
Native bounds: 4096 bytes total, 512 bytes per line, 64-character identifiers, at most
32 mod and 32 grant lines. Reject unknown versions/records, malformed or nonfinite values,
missing end, trailing nonempty content and bounds violations without applying partial effects.
`mod` applies the recipe's pulse/overTime mode for its duration. Grants and breeding chance
must not be silently dropped; if the native host does not support a field, refuse the brew.
The native host owns effect execution/expiry and authoritative breeding decisions.

## Fixtures and refusal behavior

`barkbalm-request.json` -> HTTP 200, exact bytes `barkbalm.tonic`.
`http-cases.json` defines success and refusal cases. HTTP status is the error contract;
error bodies belong to the existing Spring error handler and must not be parsed as TONIC.
401 = missing/invalid production bearer; 403 = wrong identity or unconfigured host;
400 = malformed/invalid request; 422 = valid known herbs with no recipe; 429 = per-caller rate limit (default 120/minute).
No refusal applies effects, consumes ingredients, or falls back to a random tonic.
Native HTTP calls stay off the game thread. No production token appears in fixtures.
