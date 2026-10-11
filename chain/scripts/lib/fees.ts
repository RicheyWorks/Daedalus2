// SPDX-License-Identifier: MIT
// Ported verbatim from fast-food-punks-token scripts/pipeline/fees.ts (RicheyWorks, MIT).
import { ethers as E } from "ethers";

/**
 * Explicit EIP-1559 fees for every pipeline transaction (Oct 9 2026 fix).
 *
 * Why: on the first Sepolia run hardhat-ethers filled in its own 1 gwei tip while the network was
 * clearing at ~0.001 gwei, so every tx paid ~1000x the market rate. Now each tx gets:
 *   maxPriorityFeePerGas = DEPLOY_PRIORITY_FEE_GWEI, else eth_maxPriorityFeePerGas, else the
 *                          eth_feeHistory median reward (last 10 blocks), else 0.01 gwei
 *   maxFeePerGas         = DEPLOY_MAX_FEE_GWEI, else 2 * latest baseFee + tip
 * and a HARD per-tx cap: gasLimit * maxFeePerGas must stay <= DEPLOY_MAX_TX_FEE_ETH (default
 * 0.002 ETH) or the tx is refused before it is signed.
 */

export const DEFAULT_MAX_TX_FEE_ETH = "0.002";
export const FALLBACK_TIP_WEI = E.parseUnits("0.01", "gwei");
/** gasLimit = estimate * (100 + GAS_LIMIT_HEADROOM_PCT) / 100 */
export const GAS_LIMIT_HEADROOM_PCT = 15n;

export interface FeeEnv {
  /** enforce | warn | off: overrides the detected EIP-7825 / EIP-8037 per-tx gas cap policy */
  FFP_TX_GAS_CAP?: string;
  DEPLOY_PRIORITY_FEE_GWEI?: string;
  DEPLOY_MAX_FEE_GWEI?: string;
  DEPLOY_MAX_TX_FEE_ETH?: string;
}

export interface FeeQuote {
  maxFeePerGas: bigint;
  maxPriorityFeePerGas: bigint;
  baseFeePerGas: bigint;
  /** where the tip came from: env | eth_maxPriorityFeePerGas | eth_feeHistory | fallback */
  tipSource: string;
  maxFeeSource: "env" | "2*base+tip";
}

/** Minimal provider surface (ethers JsonRpcProvider / HardhatEthersProvider both fit). */
export interface FeeProvider {
  send(method: string, params: unknown[]): Promise<any>;
  getBlock(tag: string): Promise<{ baseFeePerGas?: bigint | null } | null>;
}

const gwei = (v: string, name: string) => {
  if (!/^\d+(\.\d+)?$/.test(v.trim())) throw new Error(`${name} must be a number of gwei (got "${v}")`);
  return E.parseUnits(v.trim(), "gwei");
};

export async function quoteFees(p: FeeProvider, env: FeeEnv = process.env): Promise<FeeQuote> {
  const block = await p.getBlock("latest");
  const baseFeePerGas = BigInt(block?.baseFeePerGas ?? 0n);
  let tip: bigint | undefined;
  let tipSource = "env";
  if (env.DEPLOY_PRIORITY_FEE_GWEI) tip = gwei(env.DEPLOY_PRIORITY_FEE_GWEI, "DEPLOY_PRIORITY_FEE_GWEI");
  if (tip === undefined) {
    try {
      tip = BigInt(await p.send("eth_maxPriorityFeePerGas", []));
      tipSource = "eth_maxPriorityFeePerGas";
    } catch { /* not supported by this RPC */ }
  }
  if (tip === undefined) {
    try {
      const h = await p.send("eth_feeHistory", ["0xa", "latest", [50]]);
      const rewards = (h?.reward ?? []).map((r: string[]) => BigInt(r[0])).sort((a: bigint, b: bigint) => (a < b ? -1 : a > b ? 1 : 0));
      if (rewards.length) {
        tip = rewards[Math.floor(rewards.length / 2)];
        tipSource = "eth_feeHistory";
      }
    } catch { /* fall through */ }
  }
  if (tip === undefined) {
    tip = FALLBACK_TIP_WEI;
    tipSource = "fallback";
  }
  let maxFeePerGas = 2n * baseFeePerGas + tip;
  let maxFeeSource: FeeQuote["maxFeeSource"] = "2*base+tip";
  if (env.DEPLOY_MAX_FEE_GWEI) {
    maxFeePerGas = gwei(env.DEPLOY_MAX_FEE_GWEI, "DEPLOY_MAX_FEE_GWEI");
    maxFeeSource = "env";
  }
  if (maxFeePerGas < tip) throw new Error(`maxFeePerGas ${maxFeePerGas} is below the tip ${tip}: check DEPLOY_MAX_FEE_GWEI / DEPLOY_PRIORITY_FEE_GWEI`);
  return { maxFeePerGas, maxPriorityFeePerGas: tip, baseFeePerGas, tipSource, maxFeeSource };
}

export function maxTxFeeWei(env: FeeEnv = process.env): bigint {
  const v = (env.DEPLOY_MAX_TX_FEE_ETH ?? DEFAULT_MAX_TX_FEE_ETH).trim();
  if (!/^\d+(\.\d+)?$/.test(v)) throw new Error(`DEPLOY_MAX_TX_FEE_ETH must be a number of ETH (got "${v}")`);
  return E.parseEther(v);
}

/** Throws (before anything is signed) when the worst-case fee of one tx exceeds the cap. */
export function assertUnderCap(label: string, gasLimit: bigint, maxFeePerGas: bigint, capWei: bigint) {
  const worst = gasLimit * maxFeePerGas;
  if (worst > capWei)
    throw new Error(
      `fee cap: ${label} could cost up to ${E.formatEther(worst)} ETH (gas ${gasLimit} x ${E.formatUnits(maxFeePerGas, "gwei")} gwei), ` +
        `above the per-tx cap of ${E.formatEther(capWei)} ETH (DEPLOY_MAX_TX_FEE_ETH). Nothing was sent.`,
    );
}

export function fmtQuote(q: FeeQuote) {
  return `tip ${E.formatUnits(q.maxPriorityFeePerGas, "gwei")} gwei (${q.tipSource}), maxFee ${E.formatUnits(q.maxFeePerGas, "gwei")} gwei (${q.maxFeeSource}), base ${E.formatUnits(q.baseFeePerGas, "gwei")} gwei`;
}

export interface FeePolicy {
  /** where fees are read from (the live target network) */
  provider: FeeProvider;
  env?: FeeEnv;
  log?: (...a: any[]) => void;
}

// ---------------- EIP-7825 per-transaction gas cap (FFP-WO-0086) ----------------

/** EIP-7825 (Fusaka): a tx with gasLimit > 2^24 is invalid (txpool + block validation). */
export const TX_GAS_CAP = 16_777_216n;
/** EIP-8037 (Glamsterdam): tx.gas may exceed TX_GAS_CAP (the overflow is the state-gas reservoir), up to 2^32 - 1. */
export const TX_MAX_TOTAL_GAS = 4_294_967_295n;
/**
 * Chains known to run EIP-8037, where 2^24 caps only the regular (execution) gas of a tx.
 * Sepolia: Glamsterdam since Oct 6 2026 (blocks carry blockAccessListHash, EIP-7928); the Oct 10
 * LP mint used 36,961,176 gas with gasLimit 42,867,403 and was valid there.
 */
export const EIP8037_CHAINS: Record<number, string> = { 11155111: "Sepolia (Glamsterdam, EIP-8037, since Oct 6 2026)" };

export type GasCapMode = "enforce" | "warn" | "off";
export interface GasCapPolicy { mode: GasCapMode; reason: string }
export interface GasCapProvider { send(method: string, params: unknown[]): Promise<any>; getNetwork?(): Promise<{ chainId: bigint }> }

const capCache = new WeakMap<object, GasCapPolicy>();

/**
 * enforce: refuse any tx whose estimate is above 2^24 before it is signed (and never set a
 *          gasLimit above it): networks with EIP-7825 but without EIP-8037 reject such a tx.
 * warn:    EIP-8037 chains (Sepolia today; mainnet once Glamsterdam is live there): a total above 2^24
 *          is valid (state gas), so log a warning and go on; refuse only above 2^32 - 1.
 * Detected from the latest block (blockAccessListHash = Glamsterdam) or the chain id; FFP_TX_GAS_CAP
 * = enforce | warn | off overrides it.
 */
export async function gasCapPolicy(p: GasCapProvider, env: Record<string, string | undefined> = process.env): Promise<GasCapPolicy> {
  const forced = (env.FFP_TX_GAS_CAP ?? "").trim();
  if (forced) {
    if (!["enforce", "warn", "off"].includes(forced)) throw new Error(`FFP_TX_GAS_CAP must be enforce | warn | off (got "${forced}")`);
    return { mode: forced as GasCapMode, reason: "FFP_TX_GAS_CAP" };
  }
  const cached = capCache.get(p as object);
  if (cached) return cached;
  let res: GasCapPolicy | undefined;
  try {
    const b = await p.send("eth_getBlockByNumber", ["latest", false]);
    if (b && b.blockAccessListHash) res = { mode: "warn", reason: "latest block has blockAccessListHash (Glamsterdam: EIP-8037 state-gas reservoir)" };
  } catch { /* fall back to the chain id */ }
  if (!res) {
    let chainId: number | undefined;
    try { chainId = p.getNetwork ? Number((await p.getNetwork()).chainId) : Number(BigInt(await p.send("eth_chainId", []))); } catch { chainId = undefined; }
    res = chainId !== undefined && EIP8037_CHAINS[chainId]
      ? { mode: "warn", reason: EIP8037_CHAINS[chainId] }
      : { mode: "enforce", reason: `EIP-7825 (no EIP-8037 marker on chain ${chainId ?? "?"})` };
  }
  capCache.set(p as object, res);
  return res;
}

/**
 * Applies the per-tx gas cap to one tx before it is signed. Returns the gasLimit to use (clamped
 * to 2^24 when the estimate fits but the headroom would not) and an optional warning; throws when
 * the tx would be invalid. Nothing is sent when it throws.
 */
export function checkTxGasCap(label: string, estimate: bigint, gasLimit: bigint, policy: GasCapPolicy): { gasLimit: bigint; warning?: string } {
  if (policy.mode === "off") return { gasLimit };
  if (policy.mode === "enforce") {
    if (estimate > TX_GAS_CAP)
      throw new Error(`gas cap: ${label} needs ~${estimate} gas, above the EIP-7825 per-transaction cap of ${TX_GAS_CAP} (2^24) on this network (${policy.reason}). ` +
        "The network would reject it. Nothing was sent. Split the step, or run where EIP-8037 applies (FFP_TX_GAS_CAP=warn only if you know the chain accepts it).");
    return { gasLimit: gasLimit > TX_GAS_CAP ? TX_GAS_CAP : gasLimit };
  }
  if (estimate > TX_MAX_TOTAL_GAS) throw new Error(`gas cap: ${label} needs ~${estimate} gas, above the EIP-8037 total cap ${TX_MAX_TOTAL_GAS}. Nothing was sent.`);
  const capped = gasLimit > TX_MAX_TOTAL_GAS ? TX_MAX_TOTAL_GAS : gasLimit;
  return estimate > TX_GAS_CAP
    ? { gasLimit: capped, warning: `⚠ gas cap: ${label} needs ~${estimate} gas (> 2^24 = ${TX_GAS_CAP}). Valid here only because ${policy.reason}: only its regular gas is capped. A network with EIP-7825 but without EIP-8037 would reject this tx.` }
    : { gasLimit: capped };
}

/**
 * Fills fees + gasLimit on a tx request, enforces the cap, sends it and waits.
 * `chain` is the provider of the chain the tx is sent to (same as policy.provider on a live run;
 * the fork in a dry run): maxFee is raised to at least 2*its baseFee + tip so a fork accepts it.
 */
export async function sendWithPolicy(signer: any, req: Record<string, any>, label: string, policy: FeePolicy) {
  const env = policy.env ?? process.env;
  const q = await quoteFees(policy.provider, env);
  const chain = signer.provider;
  let maxFeePerGas = q.maxFeePerGas;
  if (chain && chain !== policy.provider) {
    const b = await chain.getBlock("latest");
    const floor = 2n * BigInt(b?.baseFeePerGas ?? 0n) + q.maxPriorityFeePerGas;
    if (floor > maxFeePerGas) maxFeePerGas = floor;
  }
  const from = await signer.getAddress();
  const est: bigint = await chain.estimateGas({ ...req, from });
  const cap = checkTxGasCap(label, est, (est * (100n + GAS_LIMIT_HEADROOM_PCT)) / 100n, await gasCapPolicy(chain, env as any));
  if (cap.warning) (policy.log ?? console.log)(cap.warning);
  const gasLimit = cap.gasLimit;
  assertUnderCap(label, gasLimit, maxFeePerGas, maxTxFeeWei(env));
  const tx = await signer.sendTransaction({ ...req, type: 2, gasLimit, maxFeePerGas, maxPriorityFeePerGas: q.maxPriorityFeePerGas });
  const r = await tx.wait();
  if (!r || r.status !== 1) throw new Error(`${label}: tx ${tx.hash} reverted`);
  return r;
}

// ---------------- dry-run cost model ----------------

export interface GasMultipliers { create: number; call: number }
/** Measured Oct 9 2026 (live eth_estimateGas on Sepolia vs the in-process fork): contract
 *  creation ~6.8x (token 13.87M vs 2.05M, mock ERC1155 10.13M vs 1.47M); a mint ~4.8x
 *  (14.03M vs 2.93M). The fork runs older gas rules than live Sepolia. */
export const DEFAULT_MULTIPLIERS: GasMultipliers = { create: 7, call: 5 };

export function multipliersFromEnv(env: Record<string, string | undefined> = process.env): GasMultipliers {
  const num = (v: string | undefined, d: number, n: string) => {
    if (v === undefined || v === "") return d;
    const x = Number(v);
    if (!Number.isFinite(x) || x < 1) throw new Error(`${n} must be a number >= 1 (got "${v}")`);
    return x;
  };
  return {
    create: num(env.FFP_CREATE_GAS_MULTIPLIER, DEFAULT_MULTIPLIERS.create, "FFP_CREATE_GAS_MULTIPLIER"),
    call: num(env.FFP_CALL_GAS_MULTIPLIER, DEFAULT_MULTIPLIERS.call, "FFP_CALL_GAS_MULTIPLIER"),
  };
}

export interface StepGas { step: string; gasUsed: bigint }
export interface CostEstimate {
  forkGas: bigint;
  projectedGas: bigint;
  /** expected spend at base + tip */
  expectedGasWei: bigint;
  /** worst case at maxFeePerGas (what the balance must cover) */
  worstGasWei: bigint;
  steps: number;
}

/** Steps that are calls but deploy a contract inside (lp:create deploys the Uniswap V3 pool,
 *  ~22 KB of code: under EIP-8037 that code deposit dominates), so they scale like a creation. */
export const CREATE_LIKE_STEPS = new Set(["lp:create"]);

/** Scale fork gas to live-network gas (deploy:* and CREATE_LIKE_STEPS by `create`, the rest by `call`) and price it. */
export function projectCost(steps: StepGas[], q: Pick<FeeQuote, "maxFeePerGas" | "maxPriorityFeePerGas" | "baseFeePerGas">, m: GasMultipliers): CostEstimate {
  const scale = (g: bigint, f: number) => (g * BigInt(Math.round(f * 1000))) / 1000n;
  let forkGas = 0n, projectedGas = 0n;
  for (const s of steps) {
    forkGas += s.gasUsed;
    projectedGas += scale(s.gasUsed, s.step.startsWith("deploy:") || CREATE_LIKE_STEPS.has(s.step) ? m.create : m.call);
  }
  const expectedPrice = q.baseFeePerGas + q.maxPriorityFeePerGas;
  return {
    forkGas, projectedGas,
    expectedGasWei: projectedGas * (expectedPrice < q.maxFeePerGas ? expectedPrice : q.maxFeePerGas),
    worstGasWei: projectedGas * q.maxFeePerGas,
    steps: steps.length,
  };
}
