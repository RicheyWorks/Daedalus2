#!/usr/bin/env node
// On clean agent stop during viewing autopilot, ask for the next polish slice
// so the user does not have to type "next".

import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const STATE_FILE = join(dirname(fileURLToPath(import.meta.url)), "state", "viewing-autopilot.json");

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

function load() {
  try {
    return asObject(readFileSync(STATE_FILE, "utf8"));
  } catch {
    return { enabled: false };
  }
}

function save(state) {
  mkdirSync(dirname(STATE_FILE), { recursive: true });
  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

const raw = await readStdin();
const input = asObject(raw);
const name = String(input.hook_event_name || input.event || "").toLowerCase();
const state = load();

if (name.includes("sessionstart")) {
  if (!existsSync(STATE_FILE)) {
    save({ enabled: true, updatedAt: Date.now(), reason: "default-on for Daedalus viewing" });
  }
  const on = load().enabled !== false;
  console.log(JSON.stringify({
    additional_context: on
      ? "Viewing autopilot is ON. Ship polish slices continuously: pick → implement → changelog → commit/push → next slice. Do not wait for the user to say next. Keep the goal active until they say stop/pause."
      : "Viewing autopilot is OFF. Wait for explicit next/continue.",
  }));
  process.exit(0);
}

if (name.includes("stop") && !name.includes("subagent")) {
  const on = state.enabled !== false;
  if (!on) {
    console.log("{}");
    process.exit(0);
  }
  // stay-on-task owns failure restarts; this hook only continues clean stops
  const status = String(input.status || input.reason || input.stop_reason || "").toLowerCase();
  const looksError = status.includes("error") || status.includes("fail") || status.includes("abort");
  if (looksError) {
    console.log("{}");
    process.exit(0);
  }
  state.lastContinueAt = Date.now();
  save(state);
  console.log(JSON.stringify({
    followup_message: [
      "Viewing autopilot: continue.",
      "Pick the next maze-viewing polish slice (not controls).",
      "Implement, changelog, targeted tests, commit and push, then keep going.",
      "Do not wait for the user. Only stop if they said stop/pause, or polish is exhausted.",
    ].join(" "),
  }));
  process.exit(0);
}

console.log("{}");
process.exit(0);
