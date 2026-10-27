#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Discord-facing leaderboard feed for arcade best scores.

Pure data export. This module reads the host's ``best_scores.dgs`` text
(``DSB1``) and returns a ranked feed. It does not open a socket, call an HTTP
client, or post anywhere. A later Discord post needs a separate draft approval.

The text rules match ``DaedalusDesktopBestScores`` (one best score per game,
``DSB1`` header, ``id score`` rows, scores clamped to ``1e12`` on record,
files over ``1e12`` or otherwise malformed refused all-or-nothing, 64 canonical
games, ids ``[a-z0-9_]{1,32}``). Old ids merge through ``CanonicalGameId`` in
``DaedalusDesktopSaveSlots.h``. This file does not include that header and does
not depend on the best-scores source landing first.

Feed (machine): JSON ``daedalus.leaderboard.feed/v1``
  format, source, tie_break, rank_rule, entries[]
  entry: rank, game_id, name, score
  sort: score descending, then canonical game id ascending
  rank_rule ``ordinal``: the tie break assigns consecutive ranks

Feed (lines): ``DLB1`` then ``rank <escaped id> score <name>``.
Underscores in the line-feed id are written ``\\_`` so a paste cannot start
Discord italic. JSON ``game_id`` stays the canonical catalog id.

``name`` is display-safe: letters, digits and single spaces only, taken from
the catalog title when the game is listed. ``@everyone``, ``@here``, mentions
and markdown cannot survive in that field.

  python tools/minigames/leaderboard_feed.py --check
  python tools/minigames/leaderboard_feed.py best_scores.dgs
  python tools/minigames/leaderboard_feed.py --text best_scores.dgs
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "docs/minigames/catalog.json"
SLOTS_PATH = (
    ROOT / "engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DesktopGames/DaedalusDesktopSaveSlots.h"
)

MAX_SCORE = 1000000000000  # host clamp, 1e12 inclusive
MAX_GAMES = 64
MAX_TEXT = 4096
FEED_FORMAT = "daedalus.leaderboard.feed/v1"
TIE_BREAK = "score_desc_then_game_id_asc"
RANK_RULE = "ordinal"
SOURCE_HEADER = "DSB1"
LINE_HEADER = "DLB1"

# Published on the minigame catalog by minigame_catalog.py. The --check hook
# refuses a catalog whose leaderboard_feed block does not match this dict.
CATALOG_HOOK = {
    "source_format": SOURCE_HEADER,
    "source_file": "best_scores.dgs",
    "feed_format": FEED_FORMAT,
    "text_format": LINE_HEADER,
    "tool": "tools/minigames/leaderboard_feed.py",
    "hook": "python tools/minigames/leaderboard_feed.py --check",
    "network": "none",
    "tie_break": TIE_BREAK,
    "rank_rule": RANK_RULE,
}

_ID = re.compile(r"^[a-z0-9_]{1,32}$")
_SCORE = re.compile(r"[+-]?\d+")
_NAME = re.compile(r"^[A-Za-z0-9]+(?: [A-Za-z0-9]+)*$")
_ALIAS_BLOCK = re.compile(
    r"std::array<GameAlias,\s*(\d+)>\s*GameAliases\{\{(.*?)\}\};", re.S
)
_ALIAS_ROW = re.compile(r'\{"([a-z0-9_]+)","([a-z0-9_]+)","[a-z0-9_]+\.dgs"\}')
_MENTION = re.compile(r"@(everyone|here)\b", re.I)


class FeedRefused(Exception):
    """The DSB1 text was refused. No partial table and no feed."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def valid_id(raw: str) -> bool:
    return bool(_ID.fullmatch(raw))


def canonical_game_id(raw: str, aliases: dict[str, str]) -> str:
    return aliases.get(raw, raw)


def clamp_score(score: int) -> int | None:
    """Record-path clamp. ``None`` when the score is not a usable integer."""
    if isinstance(score, bool) or not isinstance(score, int) or score < 0:
        return None
    return MAX_SCORE if score > MAX_SCORE else score


def record(table: dict[str, int], raw_id: str, score: int, aliases: dict[str, str] | None = None) -> bool:
    """Keep the best score for one game. True only when this call sets a new best."""
    kept = clamp_score(score)
    if kept is None or not valid_id(raw_id):
        return False
    gid = canonical_game_id(raw_id, aliases or {})
    if not valid_id(gid):
        return False
    if gid not in table:
        if len(table) >= MAX_GAMES:
            return False
        table[gid] = kept
        return True
    if kept <= table[gid]:
        return False
    table[gid] = kept
    return True


def dumps_dsb1(table: dict[str, int]) -> str:
    """Host ``Save()`` shape: header, then ids in ascending order."""
    lines = [SOURCE_HEADER]
    for gid in sorted(table):
        lines.append(f"{gid} {int(table[gid])}")
    return "\n".join(lines) + "\n"


def _lines(text: str) -> list[str]:
    """``std::getline`` on the ``Save()`` string: split on ``\\n`` only."""
    if text == "":
        return []
    parts = text.split("\n")
    if text.endswith("\n"):
        parts.pop()
    return parts


def _parse_score(token: str) -> int:
    if not _SCORE.fullmatch(token):
        raise FeedRefused("score")
    digits = token[1:] if token[0] in "+-" else token
    if len(digits) > 19:
        raise FeedRefused("score")
    value = int(token)
    if value < 0 or value > MAX_SCORE:
        raise FeedRefused("score")
    return value


def parse_dsb1(text: str, aliases: dict[str, str] | None = None) -> dict[str, int]:
    """Parse one file. Raises ``FeedRefused`` and returns nothing on any fault."""
    if len(text.encode("utf-8")) > MAX_TEXT:
        raise FeedRefused("too_large")
    rows = _lines(text)
    if not rows or rows[0] != SOURCE_HEADER:
        raise FeedRefused("header")
    aliases = aliases or {}
    found: dict[str, int] = {}
    for line in rows[1:]:
        if line == "":
            continue
        parts = line.split()
        if len(parts) != 2:
            raise FeedRefused("row")
        raw_id, token = parts
        if not valid_id(raw_id):
            raise FeedRefused("id")
        score = _parse_score(token)
        gid = canonical_game_id(raw_id, aliases)
        if not valid_id(gid):
            raise FeedRefused("id")
        if gid not in found or score > found[gid]:
            found[gid] = score
        if len(found) > MAX_GAMES:
            raise FeedRefused("cap")
    return found


def restore(
    text: str, current: dict[str, int] | None = None, aliases: dict[str, str] | None = None
) -> tuple[bool, dict[str, int]]:
    """All-or-nothing. A bad file returns the previous table unchanged."""
    previous = dict(current or {})
    try:
        return True, parse_dsb1(text, aliases)
    except FeedRefused:
        return False, previous


def sanitize_name(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 ]+", " ", raw)
    cleaned = re.sub(r" +", " ", cleaned).strip()
    if len(cleaned) > 64:
        cleaned = cleaned[:64].rstrip()
    return cleaned


def display_name(game_id: str, titles: dict[str, str]) -> str:
    """Catalog title when it stays display-safe, otherwise a plain form of the id."""
    title = titles.get(game_id) or ""
    cleaned = sanitize_name(title) if title else ""
    if not _NAME.fullmatch(cleaned or ""):
        cleaned = sanitize_name(game_id.replace("_", " "))
    if not _NAME.fullmatch(cleaned or ""):
        cleaned = "Game"
    return cleaned


def _safe_entry(entry: dict) -> None:
    name = entry["name"]
    gid = entry["game_id"]
    if not valid_id(gid) or not _NAME.fullmatch(name):
        raise FeedRefused("unsafe")
    if _MENTION.search(name) or "<@" in name or "<#" in name or "@" in name:
        raise FeedRefused("unsafe")


def rank_entries(table: dict[str, int], titles: dict[str, str] | None = None) -> list[dict]:
    titles = titles or {}
    ordered = sorted(table.items(), key=lambda item: (-item[1], item[0]))
    entries = []
    for rank, (gid, score) in enumerate(ordered, start=1):
        entry = {
            "rank": rank,
            "game_id": gid,
            "name": display_name(gid, titles),
            "score": int(score),
        }
        _safe_entry(entry)
        entries.append(entry)
    return entries


def build_entries(text: str, titles: dict[str, str] | None = None, aliases: dict[str, str] | None = None) -> list[dict]:
    return rank_entries(parse_dsb1(text, aliases), titles)


def to_json(entries: list[dict]) -> str:
    for entry in entries:
        _safe_entry(entry)
    doc = {
        "format": FEED_FORMAT,
        "source": SOURCE_HEADER,
        "tie_break": TIE_BREAK,
        "rank_rule": RANK_RULE,
        "entries": entries,
    }
    blob = json.dumps(doc, indent=2, ensure_ascii=True) + "\n"
    _refuse_mentions(blob)
    return blob


def _line_id(game_id: str) -> str:
    """Backslash-escape underscores so a pasted line cannot toggle italic."""
    return game_id.replace("_", "\\_")


def to_text(entries: list[dict]) -> str:
    lines = [LINE_HEADER]
    for entry in entries:
        _safe_entry(entry)
        token = _line_id(entry["game_id"])
        if " " in token or "@" in token or token == "":
            raise FeedRefused("unsafe")
        lines.append(f"{entry['rank']} {token} {entry['score']} {entry['name']}")
    blob = "\n".join(lines) + "\n"
    _refuse_mentions(blob)
    return blob


def _refuse_mentions(blob: str) -> None:
    if _MENTION.search(blob) or "<@" in blob or "<#" in blob:
        raise FeedRefused("unsafe")


def load_aliases(header_text: str) -> dict[str, str]:
    found = _ALIAS_BLOCK.search(header_text)
    if not found:
        raise FeedRefused("aliases")
    declared = int(found.group(1))
    pairs = _ALIAS_ROW.findall(found.group(2))
    if len(pairs) != declared or len({old for old, _new in pairs}) != len(pairs):
        raise FeedRefused("aliases")
    return {old: new for old, new in pairs}


def load_titles(catalog: dict) -> dict[str, str]:
    titles = {}
    for game in catalog.get("games", []):
        gid = game.get("id")
        if isinstance(gid, str):
            titles[gid] = game.get("title") or ""
    return titles


def scoreboard_ids(catalog: dict) -> list[str]:
    ids = []
    for game in catalog.get("games", []):
        if "scoreboard" in game.get("capabilities", []) and isinstance(game.get("id"), str):
            ids.append(game["id"])
    return ids


def hook_errors(catalog: dict, header_text: str) -> list[str]:
    """Catalog/scoreboard hook: the feed block, aliases, names and a synthetic file."""
    errors: list[str] = []
    block = catalog.get("leaderboard_feed")
    if block != CATALOG_HOOK:
        errors.append("catalog leaderboard_feed hook does not match CATALOG_HOOK")
    try:
        aliases = load_aliases(header_text)
    except FeedRefused:
        return errors + ["GameAliases could not be read from DaedalusDesktopSaveSlots.h"]
    titles = load_titles(catalog)
    ids = scoreboard_ids(catalog)
    id_set = set(ids)
    if not ids:
        errors.append("no scoreboard games for the leaderboard hook")
    for old, new in aliases.items():
        if not valid_id(old) or not valid_id(new):
            errors.append(f"alias '{old}' -> '{new}' is not a game id")
        if new not in id_set:
            errors.append(f"alias '{old}' targets '{new}', which has no scoreboard entry")
        if old in id_set:
            errors.append(f"alias '{old}' is still a catalog id")
    for gid in ids:
        name = display_name(gid, titles)
        if not _NAME.fullmatch(name) or "@" in name or "_" in name:
            errors.append(f"'{gid}' has no display-safe leaderboard name")
    if errors:
        return errors
    lines = [SOURCE_HEADER]
    sample = next(((old, new) for old, new in aliases.items() if new in id_set), None)
    if aliases and sample is None:
        errors.append("no alias targets a scoreboard game")
        return errors
    if sample:
        lines.append(f"{sample[0]} 1")
    for index, gid in enumerate(ids):
        lines.append(f"{gid} {100 + len(ids) - index}")
    text = "\n".join(lines) + "\n"
    try:
        entries = build_entries(text, titles, aliases)
        blob = to_json(entries)
        lines_out = to_text(entries)
    except FeedRefused as exc:
        return [f"synthetic best-scores file was refused ({exc.reason})"]
    if [entry["game_id"] for entry in entries] != ids:
        errors.append("synthetic feed rank does not follow score then game id")
    if len(entries) != len(ids):
        errors.append("alias row changed the scoreboard game count")
    for entry in entries:
        if entry["name"] != display_name(entry["game_id"], titles):
            errors.append(f"feed name drifted for '{entry['game_id']}'")
    loaded = json.loads(blob)
    if "network" in loaded or loaded.get("format") != FEED_FORMAT or loaded.get("tie_break") != TIE_BREAK:
        errors.append("feed format drifted")
    if not lines_out.startswith(LINE_HEADER + "\n") or "@everyone" in blob or "@everyone" in lines_out:
        errors.append("feed text is not display-safe")
    if sample:
        old, new = sample
        for body, score in (
            (f"{SOURCE_HEADER}\n{old} 9\n{new} 4\n", 9),
            (f"{SOURCE_HEADER}\n{new} 9\n{old} 4\n", 9),
        ):
            merged = build_entries(body, titles, aliases)
            if len(merged) != 1 or merged[0]["game_id"] != new or merged[0]["score"] != score:
                errors.append(f"alias '{old}' did not merge into '{new}'")
    return errors


def _read_repo() -> tuple[dict, str]:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    header = SLOTS_PATH.read_text(encoding="utf-8")
    return catalog, header


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export a ranked leaderboard feed from a DSB1 best-scores file. No network."
    )
    parser.add_argument("file", nargs="?", help="path to a DSB1 best_scores.dgs file")
    parser.add_argument("--check", action="store_true", help="run the catalog/scoreboard hook")
    parser.add_argument("--text", action="store_true", help="write DLB1 lines instead of JSON")
    args = parser.parse_args(argv)
    if args.check:
        try:
            catalog, header = _read_repo()
        except (OSError, json.JSONDecodeError) as exc:
            print(f"leaderboard feed: {exc}", file=sys.stderr)
            return 2
        problems = hook_errors(catalog, header)
        for problem in problems:
            print("FAIL:", problem)
        print("leaderboard feed ok" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0
    if not args.file:
        parser.error("pass a DSB1 file, or --check")
    try:
        raw = pathlib.Path(args.file).read_bytes()
        text = raw.decode("utf-8")
        catalog, header = _read_repo()
        entries = build_entries(text, load_titles(catalog), load_aliases(header))
    except FeedRefused as exc:
        print(f"refused: {exc.reason}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"refused: {exc.__class__.__name__}", file=sys.stderr)
        return 1
    sys.stdout.write(to_text(entries) if args.text else to_json(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
