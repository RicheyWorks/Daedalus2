import test from "node:test";
import assert from "node:assert/strict";
import { decideStop, isBenignExit, hasUncheckedItem, capFailures, RETRY_MESSAGE, PIVOT_MESSAGE, BACKLOG_MESSAGE } from "../stay-on-task-lib.mjs";

const now = 10_000_000;
const ctx = (o = {}) => ({ now, dirty: false, statusCompleted: true, backlogHasItem: false, ...o });

test("clean turn after retry sends nothing", () => {
  const r = decideStop({ lastAction: "retry", lastFailureAt: now - 1000 }, ctx());
  assert.equal(r.message, null);
  assert.equal(r.state.lastAction, "clear");
});
test("retry fires when failure newer than success and work is dirty", () => {
  const r = decideStop({ lastAction: "retry", lastFailureAt: now - 1000, lastSuccessAt: now - 5000 }, ctx({ dirty: true }));
  assert.equal(r.message, RETRY_MESSAGE);
});
test("retry suppressed when a success came after the failure", () => {
  const r = decideStop({ lastAction: "retry", lastFailureAt: now - 5000, lastSuccessAt: now - 1000 }, ctx({ dirty: true }));
  assert.equal(r.message, null);
});
test("pivot message kept", () => {
  const r = decideStop({ lastAction: "pivot", lastFailureAt: now - 1000 }, ctx());
  assert.equal(r.message, PIVOT_MESSAGE);
});
test("retry never re-sent on the next stop", () => {
  const r1 = decideStop({ lastAction: "retry", lastFailureAt: now - 1000 }, ctx({ dirty: true }));
  const r2 = decideStop(r1.state, ctx({ dirty: true }));
  assert.notEqual(r2.message, RETRY_MESSAGE);
});
test("backlog followup capped at 6 per hour", () => {
  let s = {};
  let sent = 0;
  for (let i = 0; i < 10; i++) {
    const r = decideStop(s, ctx({ backlogHasItem: true }));
    if (r.message === BACKLOG_MESSAGE) sent++;
    s = r.state;
  }
  assert.equal(sent, 6);
  const later = decideStop(s, { ...ctx({ backlogHasItem: true }), now: now + 61 * 60 * 1000 });
  assert.equal(later.message, BACKLOG_MESSAGE);
});
test("no backlog item ends cleanly", () => {
  assert.equal(decideStop({}, ctx()).message, null);
});
test("benign exits", () => {
  assert.ok(isBenignExit("git diff --exit-code", 1));
  assert.ok(isBenignExit("rg foo src", 1));
  assert.ok(isBenignExit("Get-Content x | Select-String y", 1));
  assert.ok(isBenignExit("findstr /c:x a.txt", 1));
  assert.ok(!isBenignExit("npm test", 1));
  assert.ok(!isBenignExit("rg foo", 2));
});
test("unchecked items detected", () => {
  assert.ok(hasUncheckedItem("0. [ ] Merge PR"));
  assert.ok(hasUncheckedItem("- [ ] thing"));
  assert.ok(!hasUncheckedItem("- [x] done\n1. [x] done"));
});
test("failures capped", () => {
  const f = {};
  for (let i = 0; i < 50; i++) f["s" + i] = { lastAt: i };
  const c = capFailures(f);
  assert.equal(Object.keys(c).length, 20);
  assert.ok(c.s49 && !c.s0);
});