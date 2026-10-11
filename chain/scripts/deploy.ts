// SPDX-License-Identifier: MIT
/**
 * Deploy RealmIslands (ADR-028). The fast-food-punks pipeline's rules, ported:
 *
 *  - DRY RUN by default: prints the plan, the fee quote and the worst-case cost, writes
 *    deployments/<network>.dryrun.json, sends nothing.
 *  - REALM_BROADCAST=1 sends, and only after the exact phrase "DEPLOY <NETWORK>" is typed, piped
 *    ("DEPLOY SEPOLIA" | npm run deploy:sepolia) or set in REALM_CONFIRM.
 *  - Every tx gets explicit EIP-1559 fees and a hard per-tx cap (DEPLOY_MAX_TX_FEE_ETH, default 0.002).
 *  - deployments/<network>.json records what was done; a re-run skips a finished deploy whose code is
 *    still on chain.
 *  - Mainnet is refused outright.
 *
 * Inputs (.env): DEPLOYER_PRIVATE_KEY (testnet-only), REALM_SIGNER (the address of the realm's deed key,
 * printed by the server at boot), REALM_BASE_URI (…/api/v1/world/world-zero/tokens/), REALM_OWNER
 * (defaults to the deployer).
 */
import { ethers, network } from "hardhat";
import { confirmBroadcast } from "./lib/confirm";
import { quoteFees, fmtQuote, maxTxFeeWei, sendWithPolicy, GAS_LIMIT_HEADROOM_PCT } from "./lib/fees";
import { DeploymentRecord, recordPath } from "./lib/record";

const STEP = "deploy:realmIslands";

async function main() {
  const broadcast = process.env.REALM_BROADCAST === "1";
  const chainId = Number((await ethers.provider.getNetwork()).chainId);
  if (chainId === 1) throw new Error("RealmIslands is not deployed to mainnet from this script (ADR-028).");
  const [deployer] = await ethers.getSigners();
  if (!deployer) throw new Error(`no deployer account for ${network.name}: set DEPLOYER_PRIVATE_KEY in chain/.env`);
  const local = network.name === "hardhat" || network.name === "localhost";

  const signer = (process.env.REALM_SIGNER || (local ? (await ethers.getSigners())[2]?.address : "") || "").trim();
  if (!ethers.isAddress(signer)) throw new Error("REALM_SIGNER must be the realm's deed-signer address (the server prints it at boot)");
  const owner = (process.env.REALM_OWNER || deployer.address).trim();
  if (!ethers.isAddress(owner)) throw new Error("REALM_OWNER must be an address");
  const base = (process.env.REALM_BASE_URI || (local ? "http://localhost:8088/api/v1/world/world-zero/tokens/" : "")).trim();
  if (!/^(https?|ipfs):\/\/.+\/$/.test(base)) throw new Error("REALM_BASE_URI must be a URL ending in / (…/api/v1/world/world-zero/tokens/)");

  const record = new DeploymentRecord(recordPath(network.name, !broadcast), {
    target: network.name, network: network.name, chainId, mode: broadcast ? "broadcast" : "dry-run",
    deployer: deployer.address, owner,
  });
  const factory = await ethers.getContractFactory("RealmIslands", deployer);
  const req = await factory.getDeployTransaction(owner, signer, base);
  const quote = await quoteFees(ethers.provider as any);
  const estimate = await ethers.provider.estimateGas({ ...req, from: deployer.address });
  const gasLimit = (estimate * (100n + GAS_LIMIT_HEADROOM_PCT)) / 100n;
  const balance = await ethers.provider.getBalance(deployer.address);

  console.log(`== RealmIslands | network ${network.name} (chainId ${chainId}) | mode ${broadcast ? "BROADCAST" : "dry run"} ==`);
  console.log(`deployer ${deployer.address} | balance ${ethers.formatEther(balance)} ETH`);
  console.log(`owner ${owner} | realm signer ${signer}`);
  console.log(`baseURI ${base}`);
  console.log(`fees | ${fmtQuote(quote)} | per-tx cap ${ethers.formatEther(maxTxFeeWei())} ETH`);
  console.log(`deploy gas ~${estimate} (limit ${gasLimit}) | worst case ${ethers.formatEther(gasLimit * quote.maxFeePerGas)} ETH`);

  const done = record.get(STEP);
  if (done?.status === "done" && done.address && (await ethers.provider.getCode(done.address)) !== "0x") {
    console.log(`✔ ${STEP} already done: ${done.address} (deployments record). Nothing to send.`);
    return report(done.address, chainId);
  }
  if (!broadcast) {
    record.set(STEP, { status: "hold", note: "dry run: nothing sent" });
    console.log(`dry run only. To send: REALM_BROADCAST=1, then type "DEPLOY ${network.name.toUpperCase()}". Record: ${record.file}`);
    return;
  }
  const phrase = `DEPLOY ${network.name.toUpperCase()}`;
  if (!local) console.log(`This sends a REAL transaction on ${network.name} from the key in chain/.env.`);
  const ok = await confirmBroadcast(phrase);
  if (!ok.ok) throw new Error(`cancelled: ${ok.reason}`);

  const r = await sendWithPolicy(deployer, req, STEP, { provider: ethers.provider as any });
  const address = r.contractAddress!;
  record.set(STEP, { status: "done", address, txHashes: [r.hash], gasUsed: r.gasUsed.toString() }, "realmIslands");

  const islands = await ethers.getContractAt("RealmIslands", address);
  const checks = [
    ["owner", (await islands.owner()).toLowerCase() === owner.toLowerCase()],
    ["signer", (await islands.signer()).toLowerCase() === signer.toLowerCase()],
    ["name", (await islands.name()) === "Realm Islands"],
  ] as const;
  for (const [what, pass] of checks) if (!pass) throw new Error(`post-deploy check failed: ${what}`);
  console.log(`✔ ${STEP} ${address} | gas ${r.gasUsed} | tx ${r.hash} | checks: owner, signer, name`);
  report(address, chainId);
}

function report(address: string, chainId: number) {
  console.log("\nPoint the realm at it (daedalus-server env):");
  console.log(`  DAEDALUS_WALLET_DEED_CONTRACT=${address}`);
  console.log(`  DAEDALUS_WALLET_CHAIN_ID=${chainId}`);
}

main().catch((e) => {
  console.error(e instanceof Error ? e.message : e);
  process.exitCode = 1;
});
