# Native dialogue UTF-8 readability

The existing realm dialogue contract (`docs/realms/DCS-1-CAST-SCRIPT.md`) uses
wrapped, paged and typewritten NPC text. `SDaedalusDialogue::Say` converts
`FString` to UTF-8; the widget converts each `Dialogue::Visible` row back for
display. The portable model previously counted and cut bytes between those
conversions. For example, `Caf\u00E9` at width four split the two bytes of the
accented character, and `A\u00E9\u732B\U0001F680Z` took eleven byte steps instead
of five character steps.

`DaedalusDialogueCore.h` now wraps, reveals and counts complete UTF-8 scalar
values. `Style.Cols` and typewriter rates describe code points. Existing ASCII
styles, controls, choices, page order and blip behavior remain the same. Retro
uppercase and voice-name hashing fold ASCII only; non-ASCII bytes remain intact.
No new Unicode letter/audio classification is introduced. Malformed byte input
is preserved with one-byte forward progress; it is not normalized or repaired.
Wrap widths below one use one so splitting always progresses.

This is a portable-model correction, not a text-layout engine. Combining
sequences/emoji clusters may span several reveal steps; code points are not
graphemes or rendered column widths. Font coverage, shaping, right-to-left text,
localization and Unreal rendering have not been verified by this work.

## Integration

No public model API, Slate widget, Hero code, cast script, asset, dependency,
input binding or gameplay activation changes are needed. The existing dialogue
widget uses the corrected model after a later authorized native module rebuild.
No engine/UHT build or live integration was performed in this code-only lane.
The branch is independent of pirate and Portal save work.

Later native acceptance should display a line containing an accent, CJK text
and a four-byte character at a wrap boundary, check each typewriter step and
exercise A/B page skip and choices. That visual acceptance remains pending with
the sole editor/host writer.

## Focused evidence

`engines/unreal/core-test/dialogue_core_test.cpp`: **60/60 checks pass** with
installed MSVC C++17 `/W4 /WX`, using only the portable header/test. The same
test source against the immutable pre-change header passed 45/60, reproducing
15 Unicode failures. Coverage includes exact complete prefixes, long/mixed-word
wrapping, forced breaks, page completion, skip/choice outcomes, ASCII themes and
blips, and bounded malformed-byte behavior across rows. Independent targeted
source review found no blocking defect. No unrelated suites were rerun.
