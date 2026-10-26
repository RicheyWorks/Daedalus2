#!/usr/bin/env node
// Notices tool failures, tells the agent to restart, and pivots after a repeated hang.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { execSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { capFailures, decideStop, hasUncheckedItem, isBenignExit } from "./stay-on-task-lib.mjs";

const RETRY_AFTER = 1;
const STALE_MS = 20 * 60 * 1000;
const HOOK_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(HOOK_DIR, "..", "..");
const STATE_FILE = join(HOOK_DIR, "state", "stay-on-task.json");
const PIVOT_AFTER = 3;

function readStdin() {
  return new Promise((resolve) => {
    const chunks = [];
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => chunks.push(c));
    process.stdin.on("end", () => resolve(chunks.join("")));
    process.stdin.on("error", () => resolve(""));
  });
}

function asObject(raw) {
  try {
    const parsed = JSON.parse((raw || "{}").replace(/^\uFEFF/, "").trim());
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function pick(obj, keys) {
  for (const key of keys) {
    const value = obj?.[key];
    if (value != null && value !== "") {
      return String(value);
    }
  }
  return "";
}

function eventName(input) {
  return pick(input, ["hook_event_name", "event", "event_name"]).toLowerCase();
}

function signature(input) {
  const tool = pick(input, ["tool_name", "toolName", "tool", "name"]) || "unknown";
  const err = pick(input, [
    "error",
    "error_message",
    "message",
    "stderr",
    "failure",
    "reason",
  ]);
  const cmd = pick(input, ["command", "cmd"]);
  const blob = (err || cmd || tool).replace(/\s+/g, " ").slice(0, 120);
  return `${tool}::${blob}`;
}

function loadState() {
  try {
    return asObject(readFileSync(STATE_FILE, "utf8"));
  } catch {
    return { failures: {}, lastAction: "clear", updatedAt: 0 };
  }
}

function saveState(state) {
  mkdirSync(dirname(STATE_FILE), { recursive: true });
  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

function countFailure(input) {
  const state = loadState();
  const now = Date.now();
  const sig = signature(input);
  const prev = state.failures?.[sig];
  const fresh = !prev || now - (prev.lastAt || 0) > STALE_MS;
  const count = fresh ? 1 : (prev.count || 0) + 1;
  state.failures = state.failures || {};
  state.failures[sig] = { count, lastAt: now, sig };
  state.failures = capFailures(state.failures);
  state.lastFailureAt = now;
  state.lastSig = sig;
  state.lastAction = count >= PIVOT_AFTER ? "pivot" : "retry";
  state.updatedAt = now;
  saveState(state);
  return { count, sig, action: state.lastAction };
}

function failureContext(hit) {
  if (hit.action === "pivot") {
    return [
      "STAY-ON-TASK: the same failure has now happened " + hit.count + " times (" + hit.sig + ").",
      "Stop this approach. Do not retry the same command or edit.",
      "On this restart, move on to the next remaining piece of work.",
      "Leave a one-line note of what blocked you, then continue the goal.",
    ].join(" ");
  }
  if (hit.count >= RETRY_AFTER) {
    return [
      "STAY-ON-TASK: a tool error was noticed (" + hit.sig + ", hit " + hit.count + ").",
      "Restart the current task immediately. Do not idle.",
      "If this is the second hit, change the method — do not rerun the same failing command.",
    ].join(" ");
  }
  return "";
}

function markSuccess() {
  const state = loadState();
  state.lastAction = "clear";
  state.lastSuccessAt = Date.now();
  state.updatedAt = Date.now();
  saveState(state);
}

function backlogPath() {
  const candidates = [
    process.env.CURSOR_BACKLOG_PATH,
    join(REPO_ROOT, "..", "bot-team", "BOARD", "CURSOR-BACKLOG.md"),
    "C:\\Users\\730ri\\projects\\bot-team\\BOARD\\CURSOR-BACKLOG.md",
  ].filter(Boolean);
  return candidates.find((p) => { try { return existsSync(p); } catch { return false; } }) || null;
}

function backlogHasItem() {
  const p = backlogPath();
  if (!p) return false;
  try { return hasUncheckedItem(readFileSync(p, "utf8")); } catch { return false; }
}

function repoDirty() {
  try {
    return execSync("git status --porcelain --untracked-files=no", {
      cwd: REPO_ROOT, encoding: "utf8", timeout: 3000, stdio: ["ignore", "pipe", "ignore"],
    }).trim().length > 0;
  } catch {
    return false;
  }
}

function stopFollowup(input) {
  const status = pick(input, ["status", "reason", "stop_reason"]).toLowerCase();
  const { message, state } = decideStop(loadState(), {
    now: Date.now(),
    dirty: repoDirty(),
    statusCompleted: status === "" || status === "completed",
    backlogHasItem: backlogHasItem(),
  });
  state.failures = capFailures(state.failures);
  saveState(state);
  return message;
}
const raw = await readStdin();
const input = asObject(raw);
const name = eventName(input);

function exitCode(input) {
  const raw = pick(input, ["exit_code", "exitCode", "status", "code"]);
  if (raw === "") {
    return null;
  }
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

const code = exitCode(input);
const looksLikeFailure = (code != null)
    ? !isBenignExit(pick(input, ["command", "cmd"]), code)
    : (name.includes("failure")
        || Boolean(pick(input, ["error", "error_message", "failure"])));

if (name.includes("sessionstart")) {
  console.log(JSON.stringify({
    additional_context: [
      "Stay-on-task is active.",
      "If a tool errors, restart the same task.",
      "If the same hang repeats three times, stop that approach and move on.",
    ].join(" "),
  }));
  process.exit(0);
}

if (name.includes("stop") && !name.includes("subagent")) {
  const followup = stopFollowup(input);
  if (followup) {
    console.log(JSON.stringify({ followup_message: followup }));
  } else {
    console.log("{}");
  }
  process.exit(0);
}

if (looksLikeFailure) {
  const hit = countFailure(input);
  console.log(JSON.stringify({ additional_context: failureContext(hit) }));
  process.exit(0);
}

if (code === 0) {
  markSuccess();
}

console.log("{}");
process.exit(0);
