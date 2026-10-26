# ADR-028: Wallet sign-in, and island deeds on chain

**Status:** Accepted
**Date:** 2026-10-11
**Deciders:** RicheyWorks
**Prompted by:** "use anything you can find already built in my repo to continue building. that's
why I built all this."

## Question

ADR-026 made islands ownable and ADR-027 gave each one a deed in ERC-721 metadata. Two gaps were
left. First, only one admin account could sign in, so players had no identity. Second, a deed was
only metadata: nothing on any chain said who owns an island. What is the least new code that closes
both, and what already exists to build it from?

## Decision

**Build it from three projects that already exist.**

| Need | Donor | Taken |
|---|---|---|
| Who signed this? | ComputerPets `com.enterprisepet.nft` | `WalletSignature` (personal_sign recovery) and `EthereumAddress` (normalise; a bare `0x` matches nothing), ported into `daedalus-wallet` |
| Deploying safely | fast-food-punks-token `scripts/pipeline` | `confirm.ts`, `fees.ts` and `record.ts` verbatim; Hardhat 2.29.1, OpenZeppelin 5.7.0, solc 0.8.37 viaIR cancun, same as its contracts |
| Being one identity everywhere | Daedalus `JwtTokenService` | the same JWT the admin login issues, with the wallet address as subject |

**1. A provider module, not the engine.** `daedalus-wallet` depends on web3j's `crypto` artifact
only: secp256k1, Keccak and EIP-55. There is no RPC client and no OkHttp, which ComputerPets' pom
notes conflicts with OpenTelemetry. `daedalus-core` stays free of web3 (World One §4.5). The server
mounts the wallet routes only with `daedalus.wallet.enabled=true`.

**2. Sign-In with Ethereum (EIP-4361).** `GET /auth/wallet/nonce?address=` returns the complete
message. The server writes it, so a client passes it to `personal_sign` unchanged and cannot get a
field wrong. `POST /auth/wallet` checks, in this order:
- the text is exactly EIP-4361 (`MALFORMED`)
- it names this server's domain (`WRONG_DOMAIN`) and chain (`WRONG_CHAIN`)
- it is not future-dated (`NOT_YET_VALID`) or expired (`EXPIRED`)
- the signer is the address the message names (`BAD_SIGNATURE`)
- the nonce is fresh and unused (`STALE_NONCE`)

It returns a JWT whose subject is the lowercase address. The nonce is consumed **last**, so a forged
signature cannot burn someone else's outstanding nonce. Nonces are single use, last 10 minutes, and
at most 10,000 are held, so the unauthenticated route cannot grow memory. Since ADR-026, a signed-in
caller is who they are, so the address now claims islands, builds and names builders.

**3. Deeds mint by voucher.** `RealmIslands` (`chain/`) is an ERC-721 with `Ownable2Step`. The token
id is the lane slot, and `seedOf`/`radiusOf` are on chain. `tokenURI` is the realm's
`/tokens/{slot}` from ADR-027. `mint(Deed, signature)` checks four things:
- the voucher is before its deadline
- the realm's key signed it (EIP-712, domain `RealmIslands`/`1`, bound to chain and contract)
- the token goes only to `deed.to`; anyone may submit it and pay the gas
- the slot has not been minted before (ERC-721 refuses a second mint)

`POST /world/{id}/islands/{slot}/deed-voucher` signs a voucher only when the caller is a signed-in
**wallet** and owns the island's claim. An admin-login token is not a wallet, so it gets nothing. The
realm key holds no funds, signs nothing else, and is rotated with `setSigner`; the server never
prints it. The EIP-712 hashing is written out by hand in `DeedVoucher` so every byte can be
compared with the contract.

**4. The realm.**
- **Connect wallet** signs in with the injected wallet (MetaMask, Rabby…).
- Once signed in, the name box gives way to the wallet's short address.
- On your own island, **Mint deed** fetches a voucher and calls `mint` from your wallet, switching
  chain first if needed.
- ethers 6.17.0 is loaded only when a wallet is used.

## Verified

- **Java against ethers.** Every signature and EIP-712 digest in `WalletTest` was made by ethers
  6.17.0 (what wallets and the fast-food-punks pipeline use). Java recovers the same signer, computes
  the same digest and produces the same voucher signature, byte for byte.
- **Java against the contract.** `chain/test/fixtures/java-deed-voucher.json` was signed by
  `DeedVoucher`. `WalletTest` re-signs it and must get the same bytes; the Hardhat test deploys
  RealmIslands at the fixture's address and must mint with it. A drift on either side fails a test.
- **Contract:** 6 tests: mint, forgery and tampering on every field, another chain, a second mint,
  expiry, signer rotation killing old vouchers, two-step ownership, and the Java voucher.
- **Server:** 6 tests: sign-in, replay, each refusal, owner-only vouchers, an admin token refused,
  deeds off without a key or contract, the key never printed. The prod posture test now mounts the
  wallet routes and probes all four.
- **Browser, end to end.** A page with an injected test wallet (Hardhat account 1, on a local
  Hardhat chain with RealmIslands deployed by the pipeline) signs in, claims Isle 0 and presses
  **Mint deed**. On chain, `ownerOf(0)` is that wallet, `seedOf(0)` is 11, and `tokenURI(0)` is the
  realm's metadata. Without a token, no voucher. 55/55 checks, twice, each on a fresh chain.
- **Pipeline:** the dry run sends nothing; a wrong phrase cancels; the fee cap refused a local deploy
  whose worst case (0.006 ETH at 1 gwei) was above 0.002 ETH; a re-run skips a deploy whose code is
  on chain.

## What the slice found

- **The fee cap works as designed.** Hardhat's local chain prices gas at 1 gwei, Sepolia at about
  0.0001. The ported 0.002 ETH cap refused the local deploy before signing, so local runs raise the
  cap (`DEPLOY_MAX_TX_FEE_ETH=0.01`) and Sepolia keeps it.
- **A stale parent POM hid a dependency.** The first server build could not see web3j because the
  installed parent POM predated the new version entry. The fix was reinstalling the parent; along the
  way the key moved behind `DeedSigner`, so the server never touches web3j types.
- **The config audit has a house style.** `ConfigCoverageTest` recognises
  `@ConfigurationProperties("daedalus.x")`, not the `prefix =` form; the wallet properties now use the
  former.
- **A layout bug the screenshot showed.** On the owner row the builder field shrank to "bui" beside
  **Deed minted**: an `#side input` rule out-ranked `.owner-act input`. It now takes a full row, and
  the harness measures it.
- **A test race.** With 2-second days, Isle 1's kinds label and the server could be a day apart. The
  check now polls until they agree.
- **The harness can't rerun the wallet section on the same chain**, because a slot mints once. Each
  run starts a fresh chain.

## Going live on Sepolia (owner's steps; nothing here has a funded key)

1. Generate a deed key with no funds and set it as `DAEDALUS_WALLET_DEED_SIGNER_KEY`. The server
   logs its address at boot.
2. Set `chain/.env` (`DEPLOYER_PRIVATE_KEY` with Sepolia ETH, `REALM_SIGNER` = that address,
   `REALM_BASE_URI`), run `npm run deploy:dry-run`, then `"DEPLOY SEPOLIA" | npm run deploy:sepolia`.
3. Set `DAEDALUS_WALLET_ENABLED=true`, `DAEDALUS_WALLET_DEED_CONTRACT` and the domain/URI the realm
   is served on.

## Held

- **The realm following the chain** (ADR-029). After a deed is transferred on chain, the realm's
  claim should follow `ownerOf`, read through ComputerPets' `EthereumNftService` pattern. Until then
  the realm's claim is authoritative, and the island row cannot yet say "minted" after a reload.
- **Mainnet:** the deploy script refuses chain 1; that waits for a Safe owner and an audit, as
  fast-food-punks did.
- **IPFS-pinned metadata:** the portrait is deterministic, so its CID can be pinned at mint.
