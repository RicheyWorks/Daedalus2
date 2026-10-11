# Realm browser harness (ADR-018)

Two real Chromium pages on `/realm.html` against a running server. Page A raises an island and
taps a cube in and out; page B must see every change arrive over STOMP; a third fresh page must
rebuild the same world from REST alone. Console errors on any page fail the run.

The CDN scripts are served from `node_modules` (same versions; the SockJS and STOMP files match
the page's SRI hashes byte for byte), so the run works offline and in CI.

```bash
# server on a throwaway world
DAEDALUS_WORLD_FILE=/tmp/realm.daew SERVER_PORT=8088 java -jar daedalus-server/target/daedalus-server-*-exec.jar &
cd harness/realm && npm install && npx playwright install chromium
node realm_two_browsers.mjs http://localhost:8088 .
```

It writes `realm_island.png` and `realm_built.png` to the output directory.
