# SPDX-License-Identifier: MIT
"""Prismheart shops buy as well as sell (Playwright).

    python tools/rpg_demo/sell_test.py DEMO_DIR

Checks: the item shop opens on BUY as before (the bot's buying is unchanged); RIGHT switches to SELL, which lists
every bag item that has a price, fish included, each for half its price; selling takes one from the bag and pays the
gold; the last one leaves the list; the cursor stays inside a shrinking list; LEFT goes back to BUY with its stock;
the magic shop has no SELL tab; an empty bag says so; B leaves from either tab; no page errors.
"""
import functools, http.server, json, os, sys, threading
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bot import Bot  # noqa: E402

DEMO = sys.argv[1]
http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=DEMO))
threading.Thread(target=srv.serve_forever, daemon=True).start()
D = json.load(open(os.path.join(DEMO, "data.json"), encoding="utf-8"))
res = []
def check(n, ok, info=""):
    res.append(bool(ok)); print(("ok   " if ok else "FAIL ") + n + ("  " + str(info) if info != "" else ""), flush=True)

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:%d/index.html" % srv.server_port)
    pg.wait_for_function("window.PRISM_DEMO && PRISM_DEMO.state().mode === 'title'", timeout=10000)
    bot = Bot(pg, D); ev = bot.ev; W = pg.wait_for_timeout; st = bot.st
    ev("localStorage.clear()"); ev("PRISM_DEMO.seed(2)"); ev("PRISM_DEMO.speed(6)")
    for _ in range(30):
        s = st()
        if s["mode"] == "field" and not s["dialog"]: break
        bot.press("start" if s["mode"] == "name" else "a", 150)
    W(1200); bot.clear()
    sh = lambda: ev("PRISM_DEMO.shop()")
    def enter(kind):
        ev("PRISM_DEMO.warp('%s',5,5)" % kind); W(300); bot.face("up")
        for _ in range(12):
            if st()["mode"] == "shop": break
            bot.press("a", 250)
    ev("PRISM_DEMO.give('Pond Perch', 2)"); ev("PRISM_DEMO.give('Sunscale Carp', 1)")
    enter("Item")
    check("the item shop opens on BUY", sh() and sh()["tab"] == "buy", sh())
    bot.press("right", 150)
    s = sh()
    names = {k: (n, pr) for k, n, pr in s["sell"]}
    priced = {k: v for k, v in st()["bag"].items() if v > 0 and (D["gear"].get(k) or {}).get("price")}
    check("RIGHT switches to SELL, listing every priced bag item (fish too)", s["tab"] == "sell" and set(names) == set(priced) and "Sunscale Carp" in names, (sorted(names), sorted(priced)))
    check("...each for half its price", all(pr == D["gear"][k]["price"] // 2 for k, (n, pr) in names.items()), names)
    i = [k for k, _, _ in s["sell"]].index("Pond Perch")
    for _ in range(i): bot.press("down", 70)
    g0, n0 = st()["gold"], st()["bag"]["Pond Perch"]
    bot.press("a", 200)
    check("selling one Pond Perch pays half its price and takes it from the bag",
          st()["gold"] == g0 + D["gear"]["Pond Perch"]["price"] // 2 and st()["bag"]["Pond Perch"] == n0 - 1 and "SOLD" in sh()["msg"], (g0, st()["gold"], sh()["msg"]))
    bot.press("a", 200)
    check("selling the last one removes it from the list", "Pond Perch" not in [k for k, _, _ in sh()["sell"]] and st()["bag"].get("Pond Perch", 0) == 0, sh()["sell"])
    for _ in range(20): bot.press("down", 50)
    check("the cursor stays inside the list", 0 <= sh()["idx"] < len(sh()["sell"]), sh())
    pg.screenshot(path=os.path.join(DEMO, "..", "t_sell.png"))
    bot.press("left", 150)
    check("LEFT goes back to BUY", sh()["tab"] == "buy" and sh()["sell"] is None)
    bot.press("b", 300); bot.clear()
    check("B leaves the shop", st()["mode"] == "field")

    enter("Magic")
    bot.press("right", 150)
    check("the magic shop has no SELL tab", sh() and sh()["tab"] == "buy", sh())
    bot.press("b", 300); bot.clear()

    ev("(() => { const b = PRISM_DEMO.state().bag; for (const k in b) if (b[k] > 0) PRISM_DEMO.give(k, -b[k]); })()")
    enter("Item"); bot.press("right", 150)
    check("an empty bag: SELL says there is nothing to buy from you", sh()["sell"] == [] and "NOTHING" in sh()["msg"], sh())
    bot.press("a", 150)
    check("...and A there does nothing", sh() and sh()["tab"] == "sell" and st()["mode"] == "shop")
    bot.press("b", 300); bot.clear()
    check("B leaves from the SELL tab too", st()["mode"] == "field")
    check("no page errors", not errs, errs[:3])
    b.close()

k = sum(res)
print("SELL %d/%d %s" % (k, len(res), "PASS" if k == len(res) else "FAIL"))
sys.exit(0 if k == len(res) else 1)
