#!/usr/bin/env node
// Notices tool failures, tells the agent to restart, and pivots after a repeated hang.

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PIVOT_AFTER = 3;
const RETRY_AFTER = 1;
const STALE_MS = 20 * 60 * 1000;
const STATE_FILE = join(dirname(fileURLToPath(import.meta.url)), "state", "stay-on-task.json");

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

function stopFollowup() {
  const state = loadState();
  const recent = Date.now() - (state.updatedAt || 0) < STALE_MS;
  if (!recent || state.lastAction === "clear") {
    return null;
  }
  if (state.lastAction === "pivot") {
    return [
      "Stay-on-task restart: the last approach hung (same error " + PIVOT_AFTER + "+ times).",
      "Do not resume that approach. Pick the next remaining task on the goal and continue.",
    ].join(" ");
  }
  return [
    "Stay-on-task restart: the last turn errored.",
    "Resume the same task immediately. If you already failed twice on one command, change method.",
  ].join(" ");
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
    ? code !== 0
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
  const followup = stopFollowup();
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

console.log("{}");
process.exit(0);
