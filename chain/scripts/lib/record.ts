// SPDX-License-Identifier: MIT
// Ported verbatim from fast-food-punks-token scripts/pipeline/record.ts (RicheyWorks, MIT).
import * as fs from "fs";
import * as path from "path";

/**
 * deployments/<target>.json: the single source of truth for what a pipeline run has done.
 * Every step is recorded as soon as it succeeds, so a re-run skips finished steps and resumes
 * after a failure (idempotent). Addresses are re-checked on-chain before a step is skipped.
 */

export type StepStatus = "done" | "hold" | "skipped";

export interface StepEntry {
  status: StepStatus;
  at: string;
  txHashes?: string[];
  gasUsed?: string;
  address?: string;
  note?: string;
  data?: Record<string, unknown>;
}

export interface RecordData {
  schema: 1;
  target: string;
  network: string;
  chainId: number;
  mode: string;
  deployer: string;
  owner: string;
  createdAt: string;
  updatedAt: string;
  addresses: Record<string, string>;
  steps: Record<string, StepEntry>;
  meta: Record<string, unknown>;
}

export class DeploymentRecord {
  readonly file: string;
  data: RecordData;

  constructor(file: string, init: Omit<RecordData, "schema" | "createdAt" | "updatedAt" | "addresses" | "steps" | "meta">, fresh = false) {
    this.file = file;
    if (!fresh && fs.existsSync(file)) {
      const prev = JSON.parse(fs.readFileSync(file, "utf8")) as RecordData;
      if (prev.chainId !== init.chainId)
        throw new Error(`${file} belongs to chainId ${prev.chainId}, but this run is on chainId ${init.chainId}. Use another target or move the file.`);
      if (prev.deployer.toLowerCase() !== init.deployer.toLowerCase())
        throw new Error(`${file} was written by deployer ${prev.deployer}; this run uses ${init.deployer}. Refusing to mix deployers.`);
      this.data = { ...prev, mode: init.mode };
    } else {
      const now = new Date().toISOString();
      this.data = { schema: 1, ...init, createdAt: now, updatedAt: now, addresses: {}, steps: {}, meta: {} };
    }
  }

  has(step: string): boolean {
    return this.data.steps[step]?.status === "done";
  }

  get(step: string): StepEntry | undefined {
    return this.data.steps[step];
  }

  address(name: string): string | undefined {
    return this.data.addresses[name];
  }

  set(step: string, entry: Omit<StepEntry, "at">, addressName?: string) {
    this.data.steps[step] = { ...entry, at: new Date().toISOString() };
    if (addressName && entry.address) this.data.addresses[addressName] = entry.address;
    this.save();
  }

  setMeta(key: string, value: unknown) {
    this.data.meta[key] = value;
    this.save();
  }

  totalGas(): bigint {
    return Object.values(this.data.steps).reduce((s, e) => s + BigInt(e.gasUsed ?? "0"), 0n);
  }

  save() {
    this.data.updatedAt = new Date().toISOString();
    fs.mkdirSync(path.dirname(this.file), { recursive: true });
    const tmp = `${this.file}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(this.data, (_, v) => (typeof v === "bigint" ? v.toString() : v), 2) + "\n");
    fs.renameSync(tmp, this.file);
  }
}

export const DEPLOYMENTS_DIR = path.join(__dirname, "..", "..", "deployments");

export function recordPath(target: string, dryRun: boolean): string {
  if (!/^[a-z0-9-]+$/.test(target)) throw new Error(`bad target name ${target}`);
  return path.join(DEPLOYMENTS_DIR, `${target}${dryRun ? ".dryrun" : ""}.json`);
}
