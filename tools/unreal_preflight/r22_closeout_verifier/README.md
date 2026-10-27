# r22_closeout_verifier

Read-only verifier for an R22 producer session that saved its last chunk but failed at the lease-release step
(for example the team-link broker was down). It writes one hash-sealed attestation; it changes nothing else.

```
python tools/unreal_preflight/r22_closeout_verifier/verify_closeout.py attest --campaign-root <GrandCollectionR18> --session <runs/r22-...> --out <your scratch>/att.json
python tools/unreal_preflight/r22_closeout_verifier/verify_closeout.py check --attestation <your scratch>/att.json
```

It proves: the failure is a broker-connection failure only; saved == source counts, kinds equal, contiguous history,
`next_index == end + 1`; the latest native receipt is the last chunk's, saved clean, with exactly that chunk's items;
no newer source chunk or receipt; the recorded producer PID is gone (or reused by a later process); the coordinator
lock names that same dead PID/owner/session; the broker lease view (GET `/locks` only) shows no foreign holder.
`check` re-hashes every pinned input and re-runs the probes; any flipped byte, live owner or foreign lease refuses.

It refuses to write inside the campaign root or the runs folder, never renames/deletes/unlocks, never calls a broker
write route and never touches the editor. An attestation is evidence for a reviewed recovery, not permission to run.
Exit 0 admissible, 1 refused, 2 bad input.