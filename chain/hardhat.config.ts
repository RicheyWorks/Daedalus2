// SPDX-License-Identifier: MIT
import { HardhatUserConfig, subtask } from "hardhat/config";
import { TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD } from "hardhat/builtin-tasks/task-names";
import "@nomicfoundation/hardhat-toolbox";
import * as dotenv from "dotenv";
import * as path from "path";

dotenv.config();

// Same settings as fast-food-punks-token: never ask the telemetry question (it reads stdin and broke
// piped confirmations), accounts only from .env, the compiler pinned.
process.env.HARDHAT_DISABLE_TELEMETRY_PROMPT ??= "true";

const SOLC = "0.8.37";

// HARDHAT_SOLCJS=1 compiles with the solc npm package (solcjs, the same 0.8.37) instead of downloading
// the native compiler from binaries.soliditylang.org: for sandboxes that cannot reach that host. The
// bytecode is identical; it is only slower. Unset on a normal machine.
if (process.env.HARDHAT_SOLCJS === "1") {
  subtask(TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD, async (args: { solcVersion: string }, _hre, runSuper) => {
    if (args.solcVersion !== SOLC) return runSuper();
    const compilerPath = path.join(__dirname, "node_modules", "solc", "soljson.js");
    return { compilerPath, isSolcJs: true, version: SOLC, longVersion: require("solc/package.json").version };
  });
}

const key = (process.env.DEPLOYER_PRIVATE_KEY || process.env.PRIVATE_KEY || "").trim();
const hasKey = /^(0x)?[0-9a-fA-F]{64}$/.test(key);
const accounts = hasKey ? [key.startsWith("0x") ? key : `0x${key}`] : [];

const config: HardhatUserConfig = {
  solidity: {
    version: SOLC,
    settings: {
      optimizer: { enabled: true, runs: 200 },
      viaIR: true,
      evmVersion: "cancun",
      metadata: { bytecodeHash: "ipfs" },
    },
  },
  networks: {
    hardhat: {},
    localhost: { url: process.env.LOCALHOST_RPC_URL || "http://127.0.0.1:8545" },
    sepolia: {
      chainId: 11155111,
      url: process.env.SEPOLIA_RPC_URL || "https://ethereum-sepolia-rpc.publicnode.com",
      accounts,
    },
    // No mainnet entry on purpose: island deeds launch on a testnet first (ADR-028).
  },
  etherscan: { apiKey: process.env.ETHERSCAN_API_KEY || "" },
  sourcify: { enabled: false },
};

export default config;
