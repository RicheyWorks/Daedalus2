# SPDX-License-Identifier: MIT
"""Focused REAL HTTP proof; no local-origin fulfillment or game/API stubs.

    python tools/rpg_demo/portal_http_test.py PORTAL_DIR PRISM_DIR EVIDENCE_DIR

Reuses built packages. Checks client body length/SHA/MIME, then one browser/context
loads both realms, uses actual inn saves and reloads their separate journeys.
"""
import hashlib
import http.client
import json
import mimetypes
from pathlib import Path
import sys
from urllib.parse import quote

from bot import Bot
from demo_http import DemoHTTP


def sha(body):
    return hashlib.sha256(body).hexdigest()


def main(argv):
    if len(argv) != 3:
        raise SystemExit(__doc__)
    portal, prism, evidence = [Path(arg).resolve() for arg in argv]
    if portal == prism:
        raise ValueError("Builds must be distinct")
    evidence.mkdir(parents=True, exist_ok=False)
    checks, clients, errors, network = [], [], [], []
    packages = {"portal": portal, "prism": prism}
    inputs = {realm: {p.relative_to(root).as_posix(): sha(p.read_bytes())
                      for p in root.rglob("*") if p.is_file()} for realm, root in packages.items()}

    host = DemoHTTP(packages)
    page = context = browser = None

    def capture_failure():
        if page is None:
            return
        try:
            state = page.evaluate("({url:location.href,mode:window.PRISM_DEMO?PRISM_DEMO.state().mode:null,status:document.getElementById('status')?.textContent,hidden:document.getElementById('status')?.hidden,resources:performance.getEntriesByType('resource').map(r=>({url:r.name,encodedBodySize:r.encodedBodySize,decodedBodySize:r.decodedBodySize,duration:r.duration}))})")
            (evidence / "failure-state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
            page.screenshot(path=str(evidence / "http-failure.png"), timeout=3000)
        except Exception as diagnosis:
            errors.append("failure capture: " + str(diagnosis))

    def check(name, ok, detail=None):
        checks.append({"name": name, "pass": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name, flush=True)
        if not ok:
            capture_failure()
            raise AssertionError(name)

    try:
        with host:
            def request(path, expected=None, status=200, method="GET"):
                connection = http.client.HTTPConnection("127.0.0.1", host.server.server_port, timeout=8)
                try:
                    connection.request(method, path)
                    response = connection.getresponse()
                    body = response.read(host.max_asset_bytes + 1)
                    receipt = {"path": path, "method": method, "status": response.status,
                               "content_length": response.getheader("Content-Length"),
                               "mime": response.getheader("Content-Type"), "body_bytes": len(body), "sha256": sha(body)}
                    clients.append(receipt)
                    check(method + " " + path + " status", response.status == status, receipt)
                    if expected is not None:
                        wanted = expected.read_bytes()
                        check(method + " " + path + " exact body + length + MIME",
                              receipt["content_length"] == str(len(wanted))
                              and (body == b"" if method == "HEAD" else len(body) == len(wanted) and sha(body) == sha(wanted))
                              and receipt["mime"] == (mimetypes.guess_type(str(expected))[0] or "application/octet-stream"), receipt)
                    return receipt
                finally:
                    connection.close()

            for realm, root in packages.items():
                # Includes both assets that actually reset in the earlier HTTP attempt.
                for name in ("index.html", "data.json", "backdrops.png", "sprites.png",
                             "controllers/daedalus-pad.js", "controllers/controller-bundle.json"):
                    request("/" + realm + "/" + quote(name), root / name)
            request("/portal/backdrops.png?probe=reload", portal / "backdrops.png")
            request("/prism/backdrops.png", prism / "backdrops.png", method="HEAD")
            for path in ("/missing/index.html", "/portal/", "/portal/%2e%2e/prism/index.html", "/portal/%5c..%5cindex.html"):
                request(path, status=404)

            # Imported only after the bounded direct HTTP probes have completed.
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, args=["--renderer-process-limit=1"])
                context = browser.new_context(viewport={"width": 1024, "height": 896})
                # Optional external typography is unrelated to the served demo assets.
                context.route("https://fonts.googleapis.com/**", lambda route: route.abort())
                context.route("https://fonts.gstatic.com/**", lambda route: route.abort())
                saves = {}

                def title(realm, reload=False):
                    nonlocal page
                    try:
                        if not reload:
                            if page is not None:
                                page.close()
                            page = context.new_page()
                            page.on("pageerror", lambda error: errors.append(str(error)))
                            page.on("requestfailed", lambda req: network.append({"url": req.url, "failure": req.failure}))
                            page.goto(host.origin + "/" + realm + "/index.html", wait_until="domcontentloaded", timeout=12000)
                        else:
                            page.reload(wait_until="domcontentloaded", timeout=12000)
                        page.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode==='title' && PRISM_DEMO.settings().loaded() && document.getElementById('status').hidden", timeout=12000)
                    except Exception:
                        capture_failure()
                        raise
                    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
                    state = page.evaluate("PRISM_DEMO.state()")
                    check(realm + (" reload" if reload else " boot") + " real HTTP identity + readiness",
                          page.context is context and page.evaluate("location.origin") == host.origin
                          and state["realmKey"] == realm and state["screen"] == ([256, 224] if realm == "portal" else [320, 224]))
                    # Completed resource body sizes, not transferSize (which includes headers).
                    network.append({"realm": realm, "resources": page.evaluate("performance.getEntriesByType('resource').filter(r=>new URL(r.name).origin===location.origin).map(r=>({path:new URL(r.name).pathname,encodedBodySize:r.encodedBodySize,decodedBodySize:r.decodedBodySize,duration:r.duration}))")})
                    return Bot(page, json.loads((packages[realm] / "data.json").read_text(encoding="utf-8")))

                for realm in packages:
                    bot = title(realm)
                    bot.press("a", 150)
                    page.wait_for_function("PRISM_DEMO.state().mode==='name'", timeout=3000)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(1100)
                    bot.clear()
                    check(realm + " new journey", bot.st()["mode"] == "field")
                    # Existing staging seam positions the player; the inn interaction saves normally.
                    page.evaluate("PRISM_DEMO.warp('Inn',3,6)")
                    page.wait_for_timeout(250)
                    bot.face("up")
                    bot.press("a", 250)
                    for _ in range(12):
                        if "REST" in (bot.st()["dialog"] or ""):
                            break
                        bot.press("a", 120)
                    check(realm + " actual inn prompt", "REST" in (bot.st()["dialog"] or ""))
                    bot.press("a", 1300)
                    key = realm + ".save.v1"
                    for _ in range(12):
                        raw = page.evaluate("key=>localStorage.getItem(key)", key)
                        if raw:
                            break
                        bot.press("a", 120)
                    check(realm + " real inn save", bool(raw) and json.loads(raw).get("realm_key") == realm)
                    saves[key] = raw
                    check(realm + " preserves both saved byte strings", all(page.evaluate("k=>localStorage.getItem(k)", k) == v for k, v in saves.items()))
                    bot = title(realm, reload=True)
                    bot.press("down", 120)
                    bot.press("a", 1100)
                    check(realm + " real HTTP reload + CONTINUE", bot.st()["mode"] == "field" and bot.st()["map"] == "interior"
                          and bot.st()["party"][0][0] == ("Arden" if realm == "portal" else "Corin"))
                bot = title("portal")
                bot.press("down", 120)
                bot.press("a", 1100)
                check("same-origin Portal return + both saves unchanged", bot.st()["mode"] == "field"
                      and bot.st()["party"][0][0] == "Arden" and all(page.evaluate("k=>localStorage.getItem(k)", k) == v for k, v in saves.items()))
                page.screenshot(path=str(evidence / "portal-http.png"))
                failures = [n for n in network if n.get("failure") and n["url"].startswith(host.origin + "/")]
                check("no local HTTP request failures or browser script errors", not failures and not errors, {"failures": failures, "errors": errors})
                context.close()
                browser.close()
                browser = None
            unchanged = all(sha((packages[realm] / name).read_bytes()) == digest
                            for realm, files in inputs.items() for name, digest in files.items())
            check("reused built files unchanged", unchanged)
    except Exception as error:
        if page is not None:
            try:
                page.screenshot(path=str(evidence / "http-failure.png"), timeout=3000)
            except Exception:
                pass
        errors.append(type(error).__name__ + ": " + str(error))
        raise
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        (evidence / "http-results.json").write_text(json.dumps({"transport": "actual loopback HTTP; no origin fulfillment",
            "origin": getattr(host, "origin", None), "checks": checks, "client_bodies": clients,
            "server_writes": host.receipts, "network": network, "errors": errors, "input_sha256": inputs}, indent=2) + "\n", encoding="utf-8")
    print("REAL HTTP %d/%d PASS" % (len(checks), len(checks)), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
