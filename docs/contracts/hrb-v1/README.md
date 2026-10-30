# HRB 1: herb-chord record

POST `/api/v1/audio/herb-chord` with JSON `{"herbs":[{"id":"mint","potency":1.0}, ...]}`; HTTP 200 returns text/plain HRB 1.
This is the herb/chord record AUD 1 does not carry (PR44 lists herb chords as pending for that reason). It is additive:
AUD 1 and its fixtures are unchanged, so a native AUD 1 consumer needs no change. It reuses `HerbChord.sound`; it renders no PCM,
plays nothing and makes no network call.

Input: 1 to 8 herbs. `id` is 1-32 ASCII characters from `[a-z0-9_-]` (the core lower-cases ids for the pitch class, so
upper case is rejected rather than silently folded). `potency` is finite 0-1. Invalid values are rejected, never clamped.
Auth and limits match AUD 1: `daedalus.audio.host-subject` must equal the authenticated engine identity (blank denies all);
401 missing/invalid bearer, 403 wrong subject or unconfigured host, 400 invalid input, 429 per-caller limit (shared `audioDesign` template, default 120/minute).

## Wire grammar

```text
HRB 1
chord <root 0-11> <quality> <effect> <strength>
freq <hz>
... one freq line per distinct pitch class, ascending ...
end
```

Exactly one header, one chord record, 1-12 freq records, one end record. LF, ASCII, single spaces, strength and hz with three decimals,
no locale-dependent commas. quality is one of unison, fifth, major, minor, sus, dim, aug, maj7, min7, dom7, cluster. effect is one of
STEADY, HEAL, CALM, FOCUS, WARD, HASTE, CHAOS. strength is 0-1. The same request gives identical bytes.
Native code must reject unknown versions/records, nonfinite values and a missing end, and keep the previous valid result.
Effect execution, asset mapping and any audible chord playback stay native; a valid HRB 1 reply proves nothing about audible playback.

## Fixtures

`mint-yarrow-sage-request.json` -> exact bytes `mint-yarrow-sage.hrb` (checked by `IslandHerbChordTest`).
Design/parity fixture only, not a recording and not proof of Unreal playback.