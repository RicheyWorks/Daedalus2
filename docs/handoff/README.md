# GitHub-side chores — the fifteen-minute handoff

Everything in this folder needs a browser or `gh` login the automation doesn't have. Each
item is packaged so it takes minutes, not thought. Delete this folder when all three boxes
are ticked.

## 1. File the three LoadBalancerPro issues

`lbp-issue-1.md`, `lbp-issue-2.md`, `lbp-issue-3.md` — one GitHub issue each, in the
LoadBalancerPro tracker. The title is in the comment at the top of each file; the body is
everything below it, paste-ready. They are verbatim extractions of
`docs/upstream-requests-loadbalancerpro.md` (ADR-001 action item 6). File them in order —
issues 1 and 2 block integration outright; issue 3 carries the ADR-002 measurement.

- [ ] Filed 1, 2, 3 — then mark ADR-001 item 6 `[x]` and note the issue numbers there.

## 2. Re-triage the open Dependabot PRs

```powershell
gh auth status                                   # make sure gh is logged in
.\docs\handoff\triage-dependabot.ps1             # dry run — read the verdicts
.\docs\handoff\triage-dependabot.ps1 -Close      # close the superseded ones
```

The dry run prints CLOSE/KEEP per PR with the reason. KEEP rows (JavaFX, resilience4j,
springdoc, build plugins, actions/*) are yours to judge individually.

- [ ] Triage run — then strike the item in BACKLOG.md.

## 3. Activate the Codecov upload (optional — CI already guards on it)

1. Sign in at codecov.io with GitHub and add `RicheyWorks/Daedalus2`.
2. Copy the repository upload token Codecov shows you.
3. Repo → Settings → Secrets and variables → Actions → New repository secret:
   name `CODECOV_TOKEN`, value the token.

Nothing else changes — `ci.yml`'s upload step is already in place and skips itself while the
secret is absent.

- [ ] Secret set — the next push to main uploads coverage.
