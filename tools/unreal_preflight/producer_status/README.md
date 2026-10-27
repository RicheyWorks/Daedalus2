# producer_status

Read-only one-command status for a long-running producer launched with a `launch.json` (`pid`, `start`) and a
`stdout.log` of JSON milestone lines (`CHUNK_SAVED` with `chunk`, `saved_counts`, `next_index`).

```
python tools/unreal_preflight/producer_status/producer_status.py --launch-dir <boss-launch-dir> --run-root <producer-root>
```

Shows PID liveness, last chunk, counts, next index, pace and ETA to `--target`, free RAM vs `--ram-floor`, team-link
lease age/remaining (GET `/locks` only) and any `failure.json`. Exit 0 OK, 1 attention, 2 bad input. It never writes,
kills, or unlocks anything.
