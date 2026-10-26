// Pure decision logic for stay-on-task.mjs (kept separate so it can be unit tested).

export const PIVOT_AFTER = 3;
export const STALE_MS = 20 * 60 * 1000;
export const MAX_FAILURE_ENTRIES = 20;
export const BACKLOG_MAX_PER_HOUR = 6;
export const HOUR_MS = 60 * 60 * 1000;

export const BACKLOG_MESSAGE =
  "Next backlog item: read bot-team\\BOARD\\CURSOR-BACKLOG.md, take the first unchecked item, " +
  "mark it IN PROGRESS, and start. Post a 30 minute report to buffffff with bot-team\\link\\cursor-post.ps1.";

export const RETRY_MESSAGE =
  "Stay-on-task restart: the last turn errored. Resume the same task immediately. " +
  "If you already failed twice on one command, change method.";

export const PIVOT_MESSAGE =
  "Stay-on-task restart: the last approach hung (same error " + PIVOT_AFTER + "+ times). " +
  "Do not resume that approach. Pick the next remaining task on the goal and continue.";

// Commands whose nonzero exit (usually 1) just means "no match" / "differs".
const BENIGN_CMD = /(^|[\s|;&(])(git\s+(diff|grep)|grep|egrep|fgrep|rg|findstr|select-string)\b/i;

export function isBenignExit(command, code) {
  if (code == null || code === 0) return true;
  return code === 1 && BENIGN_CMD.test(String(command || ""));
}

export function hasUncheckedItem(text) {
  return /^\s*(?:[-*+]|\d+[.)])?\s*\[ \]/m.test(String(text || ""));
}

export function capFailures(failures, max = MAX_FAILURE_ENTRIES) {
  const entries = Object.entries(failures || {});
  if (entries.length <= max) return failures || {};
  entries.sort((a, b) => (b[1]?.lastAt || 0) - (a[1]?.lastAt || 0));
  return Object.fromEntries(entries.slice(0, max));
}

// state: {lastAction, lastFailureAt, lastSuccessAt, backlogSends:[ts]}
// ctx: {now, dirty, statusCompleted, backlogHasItem}
// returns {message|null, state}
export function decideStop(state, ctx) {
  const s = { ...(state || {}) };
  const now = ctx.now;
  const failAt = s.lastFailureAt || 0;
  const okAt = s.lastSuccessAt || 0;
  const pending = s.lastAction && s.lastAction !== "clear"
    && failAt > okAt && now - failAt < STALE_MS;

  if (pending) {
    const action = s.lastAction;
    s.lastAction = "clear";
    s.updatedAt = now;
    if (action === "pivot") return { message: PIVOT_MESSAGE, state: s };
    if (ctx.dirty || !ctx.statusCompleted) return { message: RETRY_MESSAGE, state: s };
    // clean, completed turn: drop the stale retry silently
  } else if (s.lastAction && s.lastAction !== "clear") {
    s.lastAction = "clear";
    s.updatedAt = now;
  }

  const sends = (s.backlogSends || []).filter((t) => now - t < HOUR_MS);
  s.backlogSends = sends;
  if (ctx.backlogHasItem && sends.length < BACKLOG_MAX_PER_HOUR) {
    s.backlogSends = [...sends, now];
    return { message: BACKLOG_MESSAGE, state: s };
  }
  return { message: null, state: s };
}