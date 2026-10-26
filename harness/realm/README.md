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

## Wallet and deeds (ADR-028)

Set `REALM_RPC` to run the wallet section: a page with an injected test wallet (Hardhat's public
account 1) signs in, claims Isle 0 and mints its deed. It needs a fresh local chain with RealmIslands
on it and a server that signs with the matching key:

```
cd chain && npm run node                       # terminal 1: local chain
cd chain && npm run deploy:local               # RealmIslands at 0x5FbDB2315678afecb367f032d93F642f64180aa3
DAEDALUS_WALLET_ENABLED=true DAEDALUS_WALLET_CHAIN_ID=31337 \
  DAEDALUS_WALLET_DEED_CONTRACT=0x5FbDB2315678afecb367f032d93F642f64180aa3 \
  DAEDALUS_WALLET_DEED_SIGNER_KEY=5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a \
  java -jar daedalus-server/target/daedalus-server-*-exec.jar
REALM_RPC=http://127.0.0.1:8545 node realm_two_browsers.mjs http://localhost:8088 shots
```

A slot mints once, so restart the chain (and redeploy) before running the wallet section again.
The keys above are Hardhat's published test keys: local chains only, never real funds.
