# Scoped Python source quality

This stdlib helper routes static analysis for exactly two published source roots:
`tools/team_handoff` and `tools/world_package`. It never imports or executes their
application code. The existing offline unit/schema workflows and full reactor
checks remain separate and unchanged.

`scopes.json` has a finite version-1 schema validated in code: exactly the two
approved identifier/path pairs and the complete shared dependency list, with no
extra fields or commands. Duplicate JSON keys, missing entries, unknown paths,
and mismatched pairs refuse with exit 2 before writing workflow outputs. Expanding
the allowlist requires a reviewed implementation/config change; arbitrary future
scope execution is not supported.

## Comparisons and conservative fallback

The workflow checks out depth 2 and passes explicit GitHub event identities.

- For pull requests, the helper verifies that checked-out `HEAD` is the event's
  synthetic merge SHA and that its two parents are exactly the recorded base SHA
  and PR source-head SHA. It compares **base to merge snapshot**, which measures
  the PR's actual contribution after integration without including unrelated
  changes already on main. A source-head checkout alone is not accepted as that
  merge context.
- For pushes, checked-out `HEAD` must match the recorded after SHA, the recorded
  before SHA must be an available commit and its ancestor, and the entire
  before/after range is compared. The helper never substitutes `HEAD~1`.
- Manual runs select both modules. Missing/zero/invalid identities, unavailable
  history, stale merge parents, unsupported events, failed/timed-out Git calls,
  malformed diff records, and over-limit diffs conservatively select both, with
  a stable reason in the output. No fetch, network query, application execution,
  or guess at another comparison occurs in the helper. A shallow multi-commit
  push may therefore run both checks instead of selecting fewer.

The raw diff is `git diff --name-status -z --find-renames --no-ext-diff
--no-textconv BASE HEAD --`. NUL-delimited records preserve spaces, tabs,
newlines and literal backslashes. Renames/copies route both endpoints; deleted
and type-changed paths still route their source module. Prefixes match complete
directory boundaries, so `tools/team_handoff_extra` does not match. The diff is
bounded at 1 MiB and the scope map at 64 KiB. Non-UTF-8 or noncanonical relative
paths fall back to both rather than disappearing from selection.

Changes under `tools/python_quality` or to the quality, census-static, takeover
offline, or package-preflight workflows select both. A verified complete empty
or unrelated diff selects neither module. The routing helper's own tests/lint
still run. The workflow intentionally has no event path filters: routing the
complete Git diff avoids a large PR silently missing a required module check
because of a truncated event path list.

The only emitted matrix values are fixed `scope`/`path` pairs; no changed filename
becomes a command or shell fragment. Module lint jobs run serially. They log
Ruff's actual file inventory, refuse an empty inventory, and ignore Git ignore
rules so ignored Python source cannot silently evade the scoped check. Deleting
an entire selected module fails its nonempty lint check; it does not produce a
green empty match. Invalid policy fails the routing job, preventing a successful
pipeline with omitted module checks.

## Shared tooling and local checks

Both configurations use Ruff 0.17.2, Python target `py310`, and explicit
`E4`, `E7`, `E9`, `F` rules. The routing workflow and existing `census-ruff` job
install the same `requirements-lint.txt`. Census retains its job/check name,
explicit scope/config and version refusal, adding only the shared pin, pip cache,
and dependency trigger. Existing schema-test dependency pins are not replaced.

`setup-python` caches pip downloads/wheels using the shared requirements file.
It does not cache source, receipts, evidence, private inputs, or test outcomes.
Cache restore/save logs establish reuse; no benchmark or median-speed reduction
is claimed.

From the repository root, in a Python 3.10+ environment with Git available:

```sh
python -m pip install --only-binary=:all: --requirement tools/python_quality/requirements-lint.txt
python -B -m unittest tools.python_quality.test_changed_scopes -v
python -m ruff check --config tools/python_quality/ruff.toml --no-respect-gitignore tools/python_quality
python -B -m tools.python_quality.changed_scopes --event workflow_dispatch
```

Tests use synthetic NUL records and small temporary Git repositories only. They
do not read or mutate real checkout metadata, production inputs, or the two
application modules. Existing module owners retain fixes for any actual lint
findings; this pipeline does not suppress baseline findings to become green.
