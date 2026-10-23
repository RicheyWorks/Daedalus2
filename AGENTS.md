# Repository guidance

## UX, DX and AX

Assess these together when making design and implementation decisions:

- UX: player clarity, accessibility and a usable experience.
- DX: maintainable code that is easy to understand and debug.
- AX: discoverable, predictable tools, schemas and workflows with useful errors
  and resumable operations.

Prefer improvements across all three, native or existing capabilities, and
minimal reversible changes. Preserve working behavior and data; disclose
unavoidable tradeoffs. Use focused checks appropriate to changed logic and
actual production blockers.

## UI design

Prioritize clear hierarchy, layout and meaningful primary labels. Remove
redundant taglines, helper text and secondary labels; if explanatory copy is
compensating for a confusing screen, fix its layout and grouping first.
Retain essential interaction cues, accessibility information, error and recovery
messages, and kid-friendly guidance.
