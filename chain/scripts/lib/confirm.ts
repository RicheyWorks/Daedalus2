// SPDX-License-Identifier: MIT
// Ported from fast-food-punks-token scripts/pipeline/confirm.ts (RicheyWorks, MIT); the env var is REALM_CONFIRM here.
import * as readline from "readline";
import { Readable, Writable } from "stream";

/**
 * FFP-WO-0100: the broadcast confirmation.
 *
 * - REALM_CONFIRM (env) for non-interactive runs: must equal the phrase exactly (case and spaces);
 *   anything else cancels. No prompt is shown when it is set.
 * - Otherwise one line is read from stdin (typed, or piped: "DEPLOY SEPOLIA" | npm run ...).
 *   If stdin ends without a line, the answer is "" and the run is cancelled (it used to hang or
 *   leave a closed stream behind for Hardhat to trip on).
 * - The answer is trimmed of the line ending / surrounding blanks only (PowerShell pipes add CRLF);
 *   the phrase itself must match exactly.
 */
export function askLine(q: string, input: Readable = process.stdin, output: Writable = process.stdout): Promise<string> {
  return new Promise((resolve) => {
    const rl = readline.createInterface({ input, output, terminal: false });
    let done = false;
    const finish = (a: string) => {
      if (done) return;
      done = true;
      rl.close();
      // let Hardhat (a child process) start with a clean stdin: we never read it again
      if (input === process.stdin) process.stdin.pause();
      resolve(a.replace(/^\uFEFF/, "").trim());
    };
    output.write(q);
    rl.once("line", (l) => finish(l));
    rl.once("close", () => finish(""));
  });
}

export interface ConfirmResult {
  ok: boolean;
  source: "env" | "stdin";
  reason?: string;
}

export async function confirmBroadcast(
  phrase: string,
  env: NodeJS.ProcessEnv = process.env,
  ask: (q: string) => Promise<string> = (q) => askLine(q),
): Promise<ConfirmResult> {
  const fromEnv = env.REALM_CONFIRM;
  if (fromEnv !== undefined && fromEnv !== "") {
    if (fromEnv === phrase) return { ok: true, source: "env" };
    return { ok: false, source: "env", reason: `REALM_CONFIRM is set but is not exactly "${phrase}"` };
  }
  const a = await ask(`Type "${phrase}" to continue: `);
  if (a === phrase) return { ok: true, source: "stdin" };
  return { ok: false, source: "stdin", reason: a === "" ? "no answer (stdin closed)" : `answer was not exactly "${phrase}"` };
}
