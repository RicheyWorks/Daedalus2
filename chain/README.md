# chain/ — Realm Islands, the island deeds (ADR-028)

`RealmIslands` is an ERC-721 whose token id is the island's lane slot. The island's seed and radius
live on chain, and the same seed always grows the same island. A deed is minted by **voucher**: the
realm signs an EIP-712 `Deed` for the wallet that owns the island's claim, and that wallet redeems
it with `mint(deed, signature)`.

The pipeline pieces (`scripts/lib/confirm.ts`, `fees.ts`, `record.ts`) are ported from
fast-food-punks-token, with the same rules:
- a dry run by default
- a typed confirmation phrase before anything is sent
- explicit EIP-1559 fees
- a hard per-transaction fee cap
- a deployment record that makes re-runs safe
- no mainnet

```
npm ci
npm test                    # 6 tests, incl. the voucher the Java realm signed (test/fixtures)
npm run deploy:dry-run      # Sepolia plan + fee quote; sends nothing
"DEPLOY SEPOLIA" | npm run deploy:sepolia
```

`deploy:sepolia` needs `chain/.env` (see `.env.example`):
- `DEPLOYER_PRIVATE_KEY`: a testnet-only key with Sepolia ETH
- `REALM_SIGNER`: the address the server logs at boot as "Island deed vouchers are signed by …"
- `REALM_BASE_URI`

It prints the two settings the server needs next: `DAEDALUS_WALLET_DEED_CONTRACT` and
`DAEDALUS_WALLET_CHAIN_ID`.

In a sandbox that cannot download the native compiler, `HARDHAT_SOLCJS=1` uses the solc npm package
(the same 0.8.37).
