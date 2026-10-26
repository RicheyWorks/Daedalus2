// SPDX-License-Identifier: MIT
// REST + RFC 7807 naming. app.js passes the token; this file does not read `state`.
"use strict";
(function (global) {
  const API = "/api/v1";

  const CAPACITY_WHY = {
    "living-capacity": "too many mazes are already alive — wait for one to settle",
    "traffic-capacity": "too many mazes are already tracked — wait for one to settle",
    "session-capacity": "too many sessions are already open — wait for one to idle out",
    "agent-capacity": "too many fog walks are already open — wait for one to arrive or idle out",
    "maze-capacity": "too many mazes are already cached — wait for one to idle out",
    "tour-capacity": "too many waypoint hunts are already seated — wait for one to idle out",
  };

  const GONE_WHY = {
    maze: "that maze is gone",
    session: "that session is gone",
    agent: "that fog walk is gone",
  };

  const BUDGET_WHY = {
    "solver-budget": "this solver spent its node budget without finding a route",
  };

  async function problemWhy(res) {
    try {
      const body = await res.json();
      if (!body) return "";
      const why = body.detail || body.title;
      const bits = [body.kind, why].filter(Boolean);
      return bits.length ? " — " + bits.join(": ") : "";
    } catch (notProblemJson) {
      return "";
    }
  }

  function nameCapacity(msg) {
    const m = String(msg || "");
    for (const kind of Object.keys(CAPACITY_WHY)) {
      const why = CAPACITY_WHY[kind];
      if (m.includes(kind) || m === why) return why;
    }
    if (/already animating/.test(m)) return CAPACITY_WHY["living-capacity"];
    if (/already tracking/.test(m)) return CAPACITY_WHY["traffic-capacity"];
    return null;
  }

  function nameGone(msg) {
    const m = String(msg || "");
    for (const kind of Object.keys(GONE_WHY)) {
      if (m === GONE_WHY[kind]) return GONE_WHY[kind];
    }
    if (!/404/.test(m)) return null;
    if (/ — maze:/.test(m) || /on \/maze\/[^/\s]+(?:\s| —|$)/.test(m)) return GONE_WHY.maze;
    if (/ — session:/.test(m)
        || /on \/session\/[^/\s]+(?:\/(?:move|join))?(?:\s| —|$)/.test(m)) {
      return GONE_WHY.session;
    }
    if (/ — agent:/.test(m) || /on \/agent\/[^/\s]+(?:\/step)?(?:\s| —|$)/.test(m)) {
      return GONE_WHY.agent;
    }
    return null;
  }

  function nameBudget(msg) {
    const m = String(msg || "");
    const why = BUDGET_WHY["solver-budget"];
    if (m === why || m.includes("solver-budget")) return why;
    if (/gave up after expanding/.test(m)) return why;
    if (/422/.test(m) && /\/solve\//.test(m)) return why;
    return null;
  }

  function permalinkLoadFailed(getErr, rebuildErr) {
    const cap = rebuildErr && nameCapacity(rebuildErr.message);
    if (cap) return "permalink maze aged out — " + cap;
    return nameGone(getErr && getErr.message) || "permalink maze not found on this server";
  }

  function failBody(res, path, why, loginHint) {
    const hint = res.status === 401 && loginHint
        ? " — sign in (prod requires a token)" : "";
    const raw = res.status + " " + res.statusText + " on " + path + why + hint;
    return new Error(nameCapacity(raw) || nameGone(raw) || nameBudget(raw) || raw);
  }

  async function request(path, opts, token) {
    opts = opts || {};
    const headers = Object.assign({}, opts.headers);
    if (token) headers.Authorization = "Bearer " + token;
    const res = await fetch(API + path, Object.assign({}, opts, {headers}));
    if (!res.ok) {
      const why = await problemWhy(res);
      throw failBody(res, path, why, path !== "/auth/login");
    }
    const text = await res.text();
    return text ? JSON.parse(text) : null;
  }

  async function requestPlain(path, token) {
    const headers = {Accept: "text/plain"};
    if (token) headers.Authorization = "Bearer " + token;
    const res = await fetch(API + path, {headers});
    if (!res.ok) {
      const why = await problemWhy(res);
      throw failBody(res, path, why, true);
    }
    return res.text();
  }

  global.DaedalusApi = {
    API, CAPACITY_WHY, GONE_WHY, BUDGET_WHY,
    problemWhy, nameCapacity, nameGone, nameBudget, permalinkLoadFailed,
    request, requestPlain,
  };
})(window);
